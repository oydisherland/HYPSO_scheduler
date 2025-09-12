import copy
import datetime

import data_postprocessing.algorithmData_api as AD_api
from data_preprocessing.get_target_passes import getGroundStationTimeWindows
from scheduling_model import OT, TTW, BT, GSTW, TW, GS, DT
import time

bufferingTime = 1800  # seconds (Hypso-2: 1500)
afterCaptureTime = 140  # seconds for processing capture onboard (Hypso-2: 1100)
interTaskTime = 100  # general time between two tasks
interDownlinkTime = 5  # seconds between two downlink tasks
downlinkDuration = 2  # seconds to downlink a capture (Hypso-2: 217)
transmissionStartTime = 6  # seconds into the transmission window when the transmission can start (Hypso-2: 260)
maxGSTWAhead = 8  # Maximum number of ground station time windows ahead of the capture to consider when scheduling a buffering task
maxBufferOffset = 12 * 3600  # Maximum offset between a capture and its buffering in seconds
minGSWindowTime = transmissionStartTime + 0.1 * downlinkDuration # Minimum length of a ground station time window to consider it for downlinking

hypsoNr = 2  # HYPSO satellite number
groundStationFilePath = "data_input/HYPSO_data/ground_stations.csv"
ohDuration = 48 * 3600  # Duration of the observation horizon in seconds

# TODO possibly add support for spreading transmission over more than 2 ground station passes
# TODO re-order transmission tasks such that split up transmission tasks are next to each other
# TODO make a cleaning sweep re-assigning transmission tasks to buffer tasks that are close to each other, same could be done for captures and their buffering
# TODO consider that data transmission cannot happen or is at least slower during a capture when in the transmission window
# TODO after/inter task/capture time are used quite randomly, it should be more clear where they are used (for example when checking for conflicts), they are not used uniformly and difficult to change

def scheduleTransmissions(otList: list[OT], ttwList: list[TTW], gstwList: list[GSTW]):
    """
    Try to schedule the transmission of each observed target in otList.
    Transmission consists of transmitting to Ground Station and buffering the capture before actually transmitting.
    The observation tasks will be considered in the order that they are provided, so sorting by priority is recommended.

    Args:
        otList (list[OT]): List of observation tasks to schedule transmissions for.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.
        gstwList (list[GSTW]): List of ground station time windows with time windows corresponding to each GS.

    Returns:
        tuple[bool, list[BT], list[DT], list[OT]]: A tuple containing:

            - A boolean indicating if a transmission schedule has been found for all observation tasks.
                If false, there can still be a useful output containing a schedule for the tasks that were able to fit.
            - A list of scheduled buffering tasks (BT).
            - A list of scheduled downlink tasks (DT).
            - A list of observation tasks, possibly changed to fit the buffering and downlinking tasks.
    """
    btList: list[BT] = []
    dtList: list[DT] = []

    otListMod = copy.copy(otList) # This is the list of observation tasks that will be kept updated as tasks are deleted or shifted
    completeScheduleFound = True

    for otToBuffer in otList:
        # Check if this observation task has not been deleted
        if otToBuffer not in otListMod:
            continue
        # For each observation task to buffer, try to buffer it considering the downlink in one of the closest ground station time windows
        validBTFound = False
        closestGSTW = getClosestGSTW(otToBuffer, gstwList, maxGSTWAhead)
        closestGSTWSorted = gstwToSortedTupleList(closestGSTW)

        for i, entry in enumerate(closestGSTWSorted):
            gstw = GSTW(entry[0], [entry[1]])
            nextGSTW = GSTW(closestGSTWSorted[i + 1][0], [closestGSTWSorted[i + 1][1]]) \
                if i + 1 < len(closestGSTWSorted) else None

            candidateDTList = generateDownlinkTask(gstw, nextGSTW, downlinkDuration, dtList, otToBuffer)
            if candidateDTList is None: continue  # No valid downlink task could be scheduled in this ground station time window

            bt = generateBufferTaskDirectInsert(otToBuffer, gstw, otListMod, btList, gstwList)
            bt = None

            if bt is not None:
                btList.append(bt)
                for candidate in candidateDTList:
                    dtList.append(candidate)
                validBTFound = True
                # We found a buffer task and corresponding GSTW to downlink, so we don't need to consider other GSTW
                break

        if not validBTFound:
            # If no valid BT was found using direct insert, try deletion insert
            for i, entry in enumerate(closestGSTWSorted):
                gstw = GSTW(entry[0], [entry[1]])
                nextGSTW = GSTW(closestGSTWSorted[i + 1][0], [closestGSTWSorted[i + 1][1]]) \
                    if i + 1 < len(closestGSTWSorted) else None

                candidateDTList = generateDownlinkTask(gstw, nextGSTW, downlinkDuration, dtList, otToBuffer)
                if candidateDTList is None: continue  # No valid downlink task could be scheduled in this ground station time window

                # Now that we know the downlink task is scheduled, try to schedule the buffering task
                # otListPrioritySorted = otListMod.copy()  # The priority order considered in this function is the order of otList
                # bt, otListMod = generateBufferTaskDeletionInsert(otToBuffer, gstw, otListPrioritySorted, btList, gstwList)
                # bt = generateBufferTaskDirectInsert(otToBuffer, gstw, otList, btList, gstwList)

                bt = generateBufferTaskDirectInsert(otToBuffer, gstw, otListMod, btList, gstwList)
                if bt is None:
                    bt, otListMod, btListMod = generateBufferTaskSlideInsert(otToBuffer, gstw, otListMod, btList, gstwList, ttwList)
                    btList = btListMod

                if bt is not None:
                    btList.append(bt)
                    for candidate in candidateDTList:
                        dtList.append(candidate)
                    validBTFound = True
                    # We found a buffer task and corresponding GSTW to downlink, so we don't need to consider other GSTW
                    break

        if not validBTFound:
            # No valid GSTW has been found to downlink the buffered data
            completeScheduleFound = False
            print(
                f"Transmission scheduling failed for {otToBuffer.GT.id} at {otToBuffer.start}")
            otListMod.remove(otToBuffer)

    return completeScheduleFound, btList, dtList, otListMod


def generateDownlinkTask(gstw: GSTW, nextGSTW: GSTW, downlinkTime: float, dtList: list[DT], otToDownlink: OT):
    """
    Tries to schedule an entire downlink of an observation task in two given ground station time windows.
    Returns a list of downlink task with either one entry if the task fit within the first window
    or two if it needs to be spread over two windows.

    Args:
        gstw (GSTW): The ground station time window to schedule the downlink task in.
        nextGSTW (GSTW): The next ground station time window to schedule the remaining downlink task in, if necessary.
        downlinkTime (float): The length in seconds of the downlink task to schedule.
        dtList (list[DT]): List of all already scheduled downlink tasks.
        otToDownlink (OT): The observation task to schedule the downlink for.

    Returns:
        list[DT]: A list of scheduled downlink tasks, or None if no valid scheduling was found.
    """
    candidateDT, isPartialSchedule = generatePartialDownlinkTask(gstw, downlinkTime, dtList, otToDownlink)
    candidateList = [candidateDT]

    if candidateDT is None:
        # No valid downlink task could be scheduled in this ground station time window
        return None

    if not isPartialSchedule:
        # The full downlink was scheduled in the first GSTW
        return candidateList

    if nextGSTW is None:
        # No next GSTW was provided, so we cannot schedule the remaining part of the downlink task
        return None

    # Now we know the first part of the downlink task was scheduled, try to schedule the remaining part in the next GSTW
    remainingDownlinkTime = downlinkDuration - (candidateDT.end - candidateDT.start)
    candidateDT2, isPartialSchedule = generatePartialDownlinkTask(nextGSTW, remainingDownlinkTime, dtList, otToDownlink)

    if isPartialSchedule or candidateDT2 is None:
        return None
    else:
        # We can schedule the remaining part of the downlink task in the next GSTW
        # Merge the two downlink tasks into one
        candidateList.append(candidateDT2)
        return candidateList


def generatePartialDownlinkTask(gstw: GSTW, downlinkTime: float, dtList: list[DT], otToDownlink: OT):
    """
    Try to schedule downlink tasks in the given ground station time window for the given observation task.
    If the downlink task cannot fit in the schedule, try to schedule a partial downlink task.

    Args:
        gstw (GSTW): The ground station time window to schedule the downlink task in.
        downlinkTime (float): The length in seconds of the downlink task to schedule.
        dtList (list[DT]): List of all already scheduled downlink tasks.
        otToDownlink (OT): The observation task to schedule the downlink for.

    Returns:
        tuple[DT, bool]: A tuple containing:

            - DT: The scheduled downlink tasks, or None if no valid scheduling was found.
            - bool: True if only a partial downlink task was scheduled, False if the full downlink task was scheduled.
    """
    # First check if the ground station pass is long enough for downlinking at least some of the data
    if gstw.TWs[0].end - gstw.TWs[0].start < minGSWindowTime:
        return None, True

    # First try to insert the downlink task at the start of the ground station time window
    dtStart = gstw.TWs[0].start + transmissionStartTime
    dtEnd = dtStart + downlinkTime
    candidateDT = DT(otToDownlink.GT, gstw.GS, dtStart, dtEnd)
    if dtEnd <= gstw.TWs[0].end:
        if not downlinkTaskConflicting(candidateDT, dtList):
            return candidateDT, False
    else:
        # Try to schedule a partial downlink task
        dtEnd = gstw.TWs[0].end
        candidateDT = DT(otToDownlink.GT, gstw.GS, dtStart, dtEnd)
        if not downlinkTaskConflicting(candidateDT, dtList):
            return candidateDT, True

    # Now try to start the downlink task at the end of other downlink tasks
    for otherDT in dtList:
        dtStart = otherDT.end + interDownlinkTime
        dtEnd = dtStart + downlinkTime
        candidateDT = DT(otToDownlink.GT, gstw.GS, dtStart, dtEnd)

        if dtStart >= gstw.TWs[0].start and dtEnd <= gstw.TWs[0].end:
            if not downlinkTaskConflicting(candidateDT, dtList):
                return candidateDT, False
        elif gstw.TWs[0].start <= dtStart <= gstw.TWs[0].end < dtEnd:
            # Try to schedule a partial downlink task
            dtEnd = gstw.TWs[0].end
            candidateDT = DT(otToDownlink.GT, gstw.GS, dtStart, dtEnd)
            if not downlinkTaskConflicting(candidateDT, dtList):
                return candidateDT, True

    return None, True


def generateBufferTaskDirectInsert(otToBuffer: OT, gstwToDownlink: GSTW, otList: list[OT], btList: list[BT],
                                   gstwList: list[GSTW]):
    """
    Try to insert the buffering of an observed target directly into the schedule.
    Insertion is tried at the end of other tasks, so all tasks neatly follow each other.
    If no valid insertion is found, return None.

    Args:
        otToBuffer (OT): The observation task to schedule buffering for.
        gstwToDownlink (GSTW): The ground station time window to use for downlinking the buffered data.
        otList (list[OT]): List of all observation tasks
        btList (list[BT]): List of all already scheduled buffering tasks.
        dtList (list[DT]): List of all already scheduled downlink tasks.
        gstwList (list[GSTW]): List of all ground station time windows.

    Returns:
        BT: The scheduled buffering task, or None if no valid scheduling was found.
    """

    # First guess is to immediately start buffering after observation
    # Candidate buffer task start and end
    btStart = otToBuffer.end + afterCaptureTime
    btEnd = btStart + bufferingTime
    candidateBT = BT(otToBuffer.GT, btStart, btEnd)
    if not bufferTaskConflicting(candidateBT, btList, otList, gstwList) \
            and btEnd < gstwToDownlink.TWs[0].start:
        return candidateBT

    # From now on, we will save all the possible candidates and later pick the earliest option
    candidateBTList: list[BT] = []

    # Now try to insert the buffer task at the end of other observation tasks
    for ot in otList:
        # Candidate buffer task start and end
        btStart = ot.end + afterCaptureTime
        btEnd = btStart + bufferingTime

        if btStart - otToBuffer.end > maxBufferOffset or btEnd > gstwToDownlink.TWs[0].start:
            # Inserting the buffer tasks after this point would be too far from the observation task
            # or be after the intended downlink window has started.
            continue
        if ot.end < otToBuffer.end:
            # Skip if the candidate buffer task would be scheduled before its target observation
            continue

        candidateBT = BT(otToBuffer.GT, btStart, btEnd)
        if not bufferTaskConflicting(candidateBT, btList, otList, gstwList):
            candidateBTList.append(candidateBT)
            continue

    # Now try to insert the buffer task at the end of other buffer tasks
    for bt in btList:
        # Candidate buffer task start and end
        btStart = bt.end + interTaskTime
        btEnd = btStart + bufferingTime
        if btStart - otToBuffer.end > maxBufferOffset or btStart < otToBuffer.end \
                or btEnd > gstwToDownlink.TWs[0].start:
            continue

        candidateBT = BT(otToBuffer.GT, btStart, btEnd)
        if not bufferTaskConflicting(candidateBT, btList, otList, gstwList):
            candidateBTList.append(candidateBT)

    # Last attempt is to insert after a ground station time window
    for gstw in gstwList:
        for tw in gstw.TWs:
            # Candidate buffer task start and end
            btStart = tw.end + interTaskTime
            btEnd = btStart + bufferingTime
            if btStart - otToBuffer.end > maxBufferOffset or btEnd > gstwToDownlink.TWs[0].start:
                # Inserting the buffer tasks after this point would be too far from the observation task
                # or be after the intended downlink window has started.
                continue
            if btStart < otToBuffer.end:
                continue

            candidateBT = BT(otToBuffer.GT, btStart, btEnd)
            if not bufferTaskConflicting(candidateBT, btList, otList, gstwList):
                candidateBTList.append(candidateBT)
                continue

    # Search the earliest candidate in the list
    if candidateBTList:
        earliestBT = min(candidateBTList, key=lambda x: x.start)
        return earliestBT

    # No valid insertions have been found, return None
    return None


def generateBufferTaskSlideInsert(otToBuffer: OT, gstwToDownlink: GSTW, otList: list[OT], btList: list[BT],
                                  gstwList: list[GSTW], ttwList: list[TTW]):
    """
    Try to insert the buffering of an observed target into the schedule by shifting other observation tasks if necessary.

    Args:
        otToBuffer (OT): The observation task to schedule buffering for.
        gstwToDownlink (GSTW): The ground station time window to use for downlinking the buffered data.
        otList (list[OT]): List of all observation tasks
        btList (list[BT]): List of all already scheduled buffering tasks.
        gstwList (list[GSTW]): List of all ground station time windows.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.

    Returns:
        tuple[BT, list[OT], list[BT]]: A tuple containing:

            - BT: The scheduled buffering task, or None if no valid scheduling was found.
            - list[OT]: Modified list of observation tasks, with any shifted tasks updated.
            - list[BT]: Modified list of buffering tasks, with any shifted tasks updated.
    """
    otListOriginal = otList.copy()
    otListModified = otList.copy()
    btListOriginal = btList.copy()
    btListModified = btList.copy()

    shiftWindow = TW(otToBuffer.end, gstwToDownlink.TWs[0].start) # Time window in which we can shift

    # Find the largest gap that exists in this window, this is where we will try to make room to fit the buffer
    gapLength, gapTW = getLargestTimeGap(shiftWindow, otListOriginal, btListOriginal, gstwList)

    # Get the closest observation task before the gapwindow
    closestOTBeforeGap = None
    for ot in sorted(otListOriginal, key=lambda x: x.start, reverse=True):
        if ot.end <= gapTW.start:
            closestOTBeforeGap = ot
            break

    # Get the closest observation task after the gapwindow
    closestOTAfterGap = None
    for ot in sorted(otListOriginal, key=lambda x: x.start):
        if ot.start >= gapTW.end:
            closestOTAfterGap = ot
            break

    if closestOTBeforeGap is None or closestOTAfterGap is None:
        print("Error: During sliding insertion, no observation tasks before or after the gap found")
        return None, otListOriginal, btListOriginal

    # Get the closest GSTW before the gap window
    closestGSTWBeforeGap = None
    for gstw in sorted(gstwToSortedTupleList(gstwList), key=lambda x: x[1].start, reverse=True):
        if gstw[1].end <= gapTW.start:
            closestGSTWBeforeGap = GSTW(gstw[0], [gstw[1]])
            break

    shiftBackwardPossible = True
    if closestGSTWBeforeGap is not None:
        if closestGSTWBeforeGap.TWs[0].end > closestOTBeforeGap.end:
            print("GSTW is closer than OT at the beginning of the gap, so we cannot shift here")
            shiftBackwardPossible = False

    # Get the closest GSTW after the gap window
    closestGSTWAfterGap = None
    for gstw in sorted(gstwToSortedTupleList(gstwList), key=lambda x: x[1].start):
        if gstw[1].start >= gapTW.end:
            closestGSTWAfterGap = GSTW(gstw[0], [gstw[1]])
            break

    shiftForwardPossible = True
    if closestGSTWAfterGap is not None:
        if closestGSTWAfterGap.TWs[0].start < closestOTAfterGap.start:
            print("GSTW is closer than OT at the end of the gap, so we cannot shift here")
            shiftForwardPossible = False

    if shiftBackwardPossible:
        # Shift the closest observation task before the gap backward to increase the gap width
        shiftedOTBeforeGap, backwardShift = shiftOT(closestOTBeforeGap, ttwList, False)

        # Shift all buffers before the gap backward
        btListCandidate = btList.copy()
        for i, bt in enumerate(btListOriginal):
            if closestOTBeforeGap.start <= bt.start <= gapTW.start:
                btListCandidate[i] = BT(bt.GT, bt.start - backwardShift, bt.end - backwardShift)

        if not observationTaskConflicting(shiftedOTBeforeGap, btListCandidate, otListModified, gstwList):
            # The backward shift did not result in conflicts, so we can save the results
            otIndex = otListModified.index(closestOTBeforeGap)
            otListModified[otIndex] = shiftedOTBeforeGap
            btListModified = btListCandidate

    if shiftForwardPossible:
        shiftedOTAfterGap, forwardShift = shiftOT(closestOTAfterGap, ttwList, True)

        # Now shift all the buffer tasks after the gap forward
        btListTimeSorted = sorted(btListModified, key=lambda x: x.start)
        btListCandidate = btListModified.copy()
        previousBT = btListTimeSorted[0]
        successfulShift = False
        for i, bt in enumerate(btListTimeSorted):
            if bt.start > closestOTAfterGap.end:
                if bt.start - closestOTAfterGap.end == afterCaptureTime:
                    # This is the first buffer after the gap window
                    btListIndex = btListCandidate.index(bt)
                    btListCandidate[btListIndex] = BT(bt.GT, bt.start + forwardShift, bt.end + forwardShift)
                elif bt.start - previousBT.end == interTaskTime:
                    # This is one of the buffers in the stack of buffers after the gap
                    btListIndex = btListCandidate.index(bt)
                    btListCandidate[btListIndex] = BT(bt.GT, bt.start + forwardShift, bt.end + forwardShift)
                else:
                    # This is the first buffer after the gap that is not part of the chain of buffers after the capture, so we stop here
                    # We do have to do a check on the last buffer that is shifted to prevent conflicts
                    previousBTShifted = BT(previousBT.GT, previousBT.start + forwardShift, previousBT.end + forwardShift)
                    successfulShift = not bufferTaskConflicting(previousBTShifted, btListCandidate, otListModified, gstwList)
                    break

            previousBT = btListTimeSorted[i]

        if successfulShift:
            # Forward shift has been successful, so we can save the results
            otIndex = otListModified.index(closestOTAfterGap)
            otListModified[otIndex] = shiftedOTAfterGap
            btListModified = btListCandidate

    # After the shifting has been successful, try to insert the buffering task directly
    # TODO, actually display if the gap has been made big enough to fit a buffer task
    bt = generateBufferTaskDirectInsert(otToBuffer, gstwToDownlink, otListModified, btListModified, gstwList)
    if bt is not None:
        print("Successfully inserted buffering task by shifting observation tasks")
        return bt, otListModified, btListModified
    else:
        return None, otListOriginal, btListOriginal




def generateBufferTaskDeletionInsert(otToBuffer: OT, gstwToDownlink: GSTW, otListPrioritySorted: list[OT],
                                     btList: list[BT], gstwList: list[GSTW]):
    """
    Try to insert the buffering of an observed target into the schedule by deleting other observation tasks if necessary.

    Args:
        otToBuffer (OT): The observation task to schedule buffering for.
        gstwToDownlink (GSTW): The ground station time window to use for downlinking the buffered data.
        otListPrioritySorted (list[OT]): List of all observation tasks, sorted by priority (highest priority first)
        btList (list[BT]): List of all already scheduled buffering tasks.
        gstwList (list[GSTW]): List of all ground station time windows.

    Returns:
        tuple[BT, list[OT]]: A tuple containing:

            - BT: The scheduled buffering task, or None if no valid scheduling was found.
            - list[OT]: Modified list of observation tasks, with any deleted tasks removed.
    """
    # Remove lower priority observation tasks until a valid insertion is found
    otListPrioSorted = otListPrioritySorted.copy()
    otIndex = otListPrioSorted.index(otToBuffer)
    otListLength = len(otListPrioSorted)
    nRemove = otListLength - otIndex  # The number of observation tasks we can remove
    found = False
    for i in range(0, nRemove):
        otListMod = otListPrioSorted[:otListLength - i]
        bt = generateBufferTaskDirectInsert(otToBuffer, gstwToDownlink, otListMod, btList, gstwList)
        if bt is not None:
            found = True
            break

    if not found:
        return None, otListPrioSorted

    # Only remove the observation tasks that are needed to fit the buffering task
    conflictOTs, conflictBTs, conflictGSTWs = getConflictingTasks(bt, btList, otListPrioSorted, gstwList)
    if conflictBTs or conflictGSTWs:
        # We can only remove observation tasks, if there are conflicts with other tasks, return None
        return None, otListPrioSorted

    # Remove the observation tasks that conflict with the buffering task
    for conflictOT in conflictOTs:
        # print which task has been removed
        print(
            f"Removed observation task {conflictOT.GT.id} at {conflictOT.start} to fit buffering task for {otToBuffer.GT.id} at {otToBuffer.start}")
        otListPrioSorted.remove(conflictOT)

    return bt, otListPrioSorted


def getConflictingTasks(bt: BT, btList: list[BT], otList: list[OT], gstwList: list[GSTW], cancelEarly: bool = False):
    """
    Get the list of tasks that conflict with the given buffering task.

    Args:
        bt (BT): The buffering task to check for conflicts.
        btList (list[BT]): List of all already scheduled buffering tasks.
        otList (list[OT]): List of all observation tasks.
        gstwList (list[GSTW]): List of all ground station time windows.
        cancelEarly (bool, optional): If True, the function will return as soon as a single conflict is found.

    Returns:
        tuple(list[OT], list[BT], list[GSTW]): A tuple containing:

            - list[OT]: List of conflicting observation tasks.
            - list[BT]: List of conflicting buffering tasks.
            - list[GSTW]: List of conflicting ground station time windows.
    """
    conflictingOTs: list[OT] = []
    conflictingBTs: list[BT] = []
    conflictingGSTWs: list[GSTW] = []

    for ot in otList:
        if ot.start >= bt.end + interTaskTime or ot.end + afterCaptureTime <= bt.start:
            continue
        else:
            conflictingOTs.append(ot)
            if cancelEarly: return conflictingOTs, conflictingBTs, conflictingGSTWs

    for otherBT in btList:
        if otherBT.GT == bt.GT:
            # The task we are comparing is the same buffering task
            continue
        if otherBT.start >= bt.end + interTaskTime or otherBT.end + interTaskTime <= bt.start:
            continue
        else:
            conflictingBTs.append(otherBT)
            if cancelEarly: return conflictingOTs, conflictingBTs, conflictingGSTWs

    for gstw in gstwList:
        for tw in gstw.TWs:
            if tw.start >= bt.end + interTaskTime or tw.end + interTaskTime <= bt.start:
                continue
            else:
                conflictingGSTWs.append(gstw)
                if cancelEarly: return conflictingOTs, conflictingBTs, conflictingGSTWs

    return conflictingOTs, conflictingBTs, conflictingGSTWs


def bufferTaskConflicting(bt: BT, btList: list[BT], otList: list[OT], gstwList: list[GSTW]):
    """
    Check if the buffering task overlaps with any other scheduled tasks.

    Args:
        bt (BT): The buffering task to validate.
        btList (list[BT]): List of all already scheduled buffering tasks.
        otList (list[OT]): List of all observation tasks.
        gstwList (list[GSTW]): List of all ground station time windows.

    Returns:
        bool: True if the buffering task conflicts with any other task, False otherwise.
    """
    conflictOTs, conflictBTs, conflictGSTWs = getConflictingTasks(bt, btList, otList, gstwList, True)
    return conflictOTs or conflictBTs or conflictGSTWs

def observationTaskConflicting(ot: OT, btList: list[BT], otList: list[OT], gstwList: list[GSTW]):
    """
    Check if the observation task overlaps with any other scheduled tasks.

    Args:
        ot (OT): The observation task to validate.
        btList (list[BT]): List of all already scheduled buffering tasks.
        otList (list[OT]): List of all observation tasks.
        gstwList (list[GSTW]): List of all ground station time windows.

    Returns:
        bool: True if the observation task conflicts with any other task, False otherwise.
    """
    # Trick to use the existing function is to convert observation task to buffer task
    otAsBT = BT(ot.GT, ot.start, ot.end)
    conflictOTs, conflictBTs, conflictGSTWs = getConflictingTasks(otAsBT, btList, otList, gstwList, True)
    return conflictOTs or conflictBTs or conflictGSTWs


def downlinkTaskConflicting(dt: DT, dtList: list[DT]):
    """
    Check if the downlink task overlaps with any other scheduled downlink tasks.

    Args:
        dt (DT): The downlink task to validate.
        dtList (list[DT]): List of all already scheduled downlink tasks.
    """
    for otherDT in dtList:
        if otherDT.end < dt.start or otherDT.start > dt.end:
            continue
        else:
            return True

    return False


def getClosestGSTW(ot: OT, gstwList: list[GSTW], numberOfClosest=1):
    """
    Get the closest ground station time windows to the observation task.

    Args:
        ot (OT): The observation task to find the closest ground station time windows for.
        gstwList (list[GSTW]): List of all ground station time windows.
        numberOfClosest (int, optional): Number of closest ground station time windows to return. Defaults to 1.
                If there are less than this number of time windows available, all available time windows will be returned.

    Return:
        list[GSTW]: List of the closest ground station time windows.
    """
    # First put the gstwList into a single list of time windows with reference to their ground station
    # This is not the right output structure, but it is easier to sort and select from

    allGSTWsSorted = gstwToSortedTupleList(gstwList)

    # Remove entries before the observation tasks ended
    allGSTWsSorted = [entry for entry in allGSTWsSorted if entry[1].start >= ot.end]

    if not allGSTWsSorted:
        return []
    if len(allGSTWsSorted) < numberOfClosest:
        numberOfClosest = len(allGSTWsSorted)

    allGSTWsSorted = allGSTWsSorted[:numberOfClosest]

    # Put list in GSTW format by grouping by GS
    groupedList: list[GSTW] = []
    for entry in allGSTWsSorted:
        # Try to add the time window to a GSTW with the same GS
        added = False
        for gstw in groupedList:
            if gstw.GS == entry[0]:
                gstw.TWs.append(entry[1])
                added = True
                break
        if not added:
            groupedList.append(GSTW(entry[0], [entry[1]]))

    return groupedList


def gstwToSortedTupleList(gstwList: list[GSTW]):
    """
    Convert a list of GSTW (GS, [TWs]) to a list of tuples (GS, TW) sorted by TW start time.

    Args:
        gstwList (list[GSTW]): List of GSTW to convert.

    Returns:
        list[tuple[GS, TW]]: List of tuples (GS, TW) sorted
    """
    allGSTWs: list[tuple[GS, TW]] = []
    for gstw in gstwList:
        for tw in gstw.TWs:
            allGSTWs.append((gstw.GS, tw))

    return sorted(allGSTWs, key=lambda x: x[1].start)

def getLargestTimeGap(searchWindow: TW, otList: list[OT], btList: list[BT], gstwList: list[GSTW]):
    """
    Get the largest time gap between scheduled tasks.
    This will take into account the processing or waiting time that is needed after each specific task.

    Args:
        searchWindow (TW): The time window to search for the largest time gap in.
        otList (list[OT]): List of observation tasks.
        btList (list[BT]): List of buffering tasks.
        gstwList (list[GSTW]): List of ground station time windows.

    Returns:
        tuple[float, TW]: A tuple containing:

            - float: The duration of the largest time gap in seconds.
            - TW: The time window representing the largest time gap.
    """
    twList = mergeToTimeWindowList(otList, btList, gstwList)

    if not twList:
        return 0

    # Add a dummy time window at the start and end of the observation horizon
    twList.insert(0, TW(0, 0))
    twList.append(TW(ohDuration, ohDuration))

    largestGap = 0
    begin = 0
    end = 0
    for i in range(len(twList) - 1):
        if twList[i].end < searchWindow.start or twList[i + 1].start > searchWindow.end:
            continue
        gap = twList[i + 1].start - twList[i].end
        if gap > largestGap:
            largestGap = gap
            begin = twList[i].end
            end = twList[i + 1].start

    return largestGap, TW(begin, end)

def mergeToTimeWindowList(otList: list[OT], btList: list[BT], gstwList: list[GSTW]):
    """
    Merge the observation tasks, buffering tasks and ground station time windows into a single list of time windows.
    The time windows in the list will include the processing and waiting times for each task

    Args:
        otList (list[OT]): List of observation tasks.
        btList (list[BT]): List of buffering tasks.
        gstwList (list[GSTW]): List of ground station time windows.

    Returns:
        list[TW]: List of time windows
    """
    twList: list[TW] = []
    for ot in otList:
        twList.append(TW(ot.start, ot.end + afterCaptureTime))
    for bt in btList:
        twList.append(TW(bt.start, bt.end + interTaskTime))
    for gstw in gstwList:
        for tw in gstw.TWs:
            twList.append(TW(tw.start, tw.end + interTaskTime))

    return sorted(twList, key=lambda x: x.start)

def shiftOT(ot: OT, ttwList: list[TTW], shiftForward: bool = True, shiftAmount: float = float('Infinity')):
    """
    Shift an observation task forward or backward in time.

    Args:
        ot (OT): The observation task to shift.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.
        shiftForward (bool, optional): If True, the task will be shifted forward in time. If False, it will be shifted backward. Defaults to True.
        shiftAmount (float, optional): The absolute amount of time in seconds to shift the task. The task will never be shifted outside its target time window.

    Returns:
        A tuple(OT, float) containing:

            OT: The shifted observation task. If no valid shifting was possible, the original task will be returned.
            float: The actual amount of time in seconds the task was shifted.
    """
    # First find the corresponding time window from the list
    otTW = None
    for ttw in ttwList:
        if ttw.GT == ot.GT:
            for tw in ttw.TWs:
                if tw.start <= ot.start and tw.end >= ot.end:
                    otTW = tw
                    break

    if otTW is None:
        print(f"Observation task {ot.GT.id} at {ot.start} is not included in the target time windows list")
        return ot, 0

    actualShift = 0
    if shiftForward:
        maxShift = otTW.end - ot.end
        actualShift = min(abs(shiftAmount), maxShift)
        newOT = OT(ot.GT, ot.start + actualShift, ot.end + actualShift)
    else:
        maxShift = ot.start - otTW.start
        actualShift = min(abs(shiftAmount), maxShift)
        newOT = OT(ot.GT, ot.start - actualShift, ot.end - actualShift)

    return newOT, actualShift

def plotSchedule(otListMod: list[OT], otList: list[OT], btList: list[BT], dtList: list[DT], gstwList: list[GSTW], ttwList: list[TTW]):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(30, 5))

    # Observation Tasks (blue)
    for i, ot in enumerate(otListMod, start=1):
        ax.barh(
            y=0,
            width=ot.end - ot.start,
            left=ot.start,
            height=0.5,
            color="royalblue",
            alpha=1,
            label="OT modified" if i == 1 else ""
        )
        # Label under the box
        ax.text(
            x=ot.start + (ot.end - ot.start) / 2,
            y=0 - (i % 3) * 0.04,  # below y=0 row
            s=str(i),
            ha="center",
            va="top",
            fontsize=10,
            color="black"
        )

    for i, ot in enumerate(otList, start=1):
        ax.barh(
            y=-0.5,
            width=ot.end - ot.start,
            left=ot.start,
            height=0.3,
            color="darkgrey",
            alpha=1,
            label="OT original" if i == 1 else ""
        )
        # Label under the box
        ax.text(
            x=ot.start + (ot.end - ot.start) / 2,
            y=-0.5 - (i % 3) * 0.04,  # below y=0 row
            s=str(i),
            ha="center",
            va="top",
            fontsize=10,
            color="black"
        )

    # Buffering Tasks (orange)
    for i, bt in enumerate(btList, start=1):
        ax.barh(
            y=0.5,
            width=bt.end - bt.start,
            left=bt.start,
            height=0.5,
            color="darkorange",
            alpha=0.7,
            label="BT" if i == 1 else ""
        )
        ax.text(
            x=bt.start + (bt.end - bt.start) / 2,
            y=0.25,  # below y=0.5 row
            s=str(i),
            ha="center",
            va="top",
            fontsize=10,
            color="black"
        )

    # GSTWs (green)
    counter = 1
    for gstw in gstwList:
        for tw in gstw.TWs:
            ax.barh(
                y=1,
                width=tw.end - tw.start,
                left=tw.start,
                height=0.5,
                color="green",
                alpha=0.3,
                label=gstw.GS.id if counter == 1 else ""
            )
            ax.text(
                x=tw.start + (tw.end - tw.start) / 2,
                y=0.75,  # below y=1 row
                s=str(counter),
                ha="center",
                va="top",
                fontsize=10,
                color="black"
            )
            counter += 1

    for gt in ttwList:
        for tw in gt.TWs:
            ax.barh(
                y=-0.3,
                width=tw.end - tw.start,
                left=tw.start,
                height=0.2,
                color="lightblue",
                alpha=0.7,
            )

    # Add DTlist plotting
    previousGT = None
    gtId = 0
    for i, dt in enumerate(dtList, start=1):
        if dt.GT != previousGT:
            previousGT = dt.GT
            gtId += 1
        ax.barh(
            y=1.5,
            width=dt.end - dt.start,
            left=dt.start,
            height=0.5,
            color="red",
            alpha=0.4,
            label="DT" if i == 1 else ""
        )
        ax.text(
            x=dt.start + (dt.end - dt.start) / 2,
            y=1.75 - (i % 11) * 0.05,  # below y=1.5 row
            s=str(gtId),
            ha="center",
            va="top",
            fontsize=10,
            color="black"
        )

    # Formatting
    plt.xlim(0, ohDuration)
    plt.xlabel("Time [s]")
    plt.legend()
    plt.tight_layout()
    plt.show()


otList = AD_api.getScheduleFromFile("BS_test12-run1.json")  # observation task
otListPrioSorted = sorted(otList, key=lambda x: x.GT.priority, reverse=True)

# Create TTW list by adding 150 seconds before and after each observation task
ttwList: list[TTW] = []
for ot in otList:
    ttwStart = max(0, ot.start - 300)
    ttwEnd = min(ohDuration, ot.end + 500)
    ttwList.append(TTW(ot.GT, [TW(ttwStart, ttwEnd)]))

startTimeOH = datetime.datetime(2025, 8, 27, 15, 29, 0)
startTimeOH = startTimeOH.replace(tzinfo=datetime.timezone.utc)
endTimeOH = startTimeOH + datetime.timedelta(seconds=ohDuration)

gstwList = getGroundStationTimeWindows(startTimeOH, endTimeOH, minGSWindowTime, groundStationFilePath, hypsoNr)

start_time = time.perf_counter()
valid, btList, dtList, otListModified = scheduleTransmissions(otListPrioSorted, ttwList, gstwList)
end_time = time.perf_counter()

print(f"{(end_time - start_time) * 1000:.4f} milliseconds")

plotSchedule(otListModified, otListPrioSorted, btList, dtList, gstwList, ttwList)

# Sort the otList by time and display the times between each capture
otListTimeSorted = sorted(otList, key=lambda x: x.start)
timeDiffList = []
for i in range(1, len(otListTimeSorted)):
    timeDiff = otListTimeSorted[i].start - otListTimeSorted[i - 1].end
    if 1650 < timeDiff < 1960:
        timeDiffList.append(timeDiff)
        print(f"Time between capture {i} and {i+1}: {timeDiff} seconds")
