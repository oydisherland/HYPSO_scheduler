import copy

from scheduling_model import OT, TTW, GSTW, BT, DT
from transmission_scheduling import insertion
from transmission_scheduling.conflict_checks import observationTaskConflicting, downlinkTaskConflicting
from transmission_scheduling.generate_downlink import generateDownlinkTask
from transmission_scheduling.input_parameters import TransmissionParams
from transmission_scheduling.util import getClosestGSTW, gstwToSortedTupleList, findPossibleTTW, generateNewOTList, \
    latencyCounter


def twoStageTransmissionScheduling(otList: list[OT], ttwList: list[TTW], gstwList: list[GSTW],
                                   parameters: TransmissionParams) -> tuple[bool, list[BT], list[DT], list[OT]]:
    """
    Try to schedule the transmission of each observed target in otList.
    Transmission consists of transmitting to Ground Station and buffering the capture before actually transmitting.
    The observation tasks will be considered in the order that they are provided, so sorting by priority is recommended.

    The first phase will try to insert the buffer and transmission tasks with several strategies.
    The second phase will try to re-insert the observation tasks that could not be scheduled in the first phase.
    This re-insertion is attempted at other target time windows (other passes of the satellite over the target)

    Args:
        otList (list[OT]): List of observation tasks to schedule transmissions for.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.
        gstwList (list[GSTW]): List of ground station time windows with time windows corresponding to each GS.
        parameters (TransmissionParams): Parameters for the transmission scheduling.

    Returns:
        tuple[bool, list[BT], list[DT], list[OT]]: A tuple containing:

            - A boolean indicating if a transmission schedule has been found for all observation tasks.
              If false, there can still be a useful output containing a schedule for the tasks that were able to fit.
            - A list of scheduled buffering tasks (BT).
            - A list of scheduled downlink tasks (DT).
            - A list of observation tasks, possibly changed to fit the buffering and downlinking tasks.
    """

    """
    Phase 1: Regular insertion phase using several strategies (e.g. direct, sliding, deleting)
    """
    p = parameters
    fullScheduleFound, btList, dtList, otListScheduled = scheduleTransmissions(otList, ttwList, gstwList, p)

    if fullScheduleFound:
        btList, dtList = cleanUpSchedule(otListScheduled, btList, dtList, gstwList)
        return fullScheduleFound, btList, dtList, otListScheduled

    """
    Phase 2: Re-insertion phase for the observation tasks that could not be scheduled in the first phase
    """
    possibleTTW = copy.deepcopy(ttwList)
    otListReInsert = otList.copy()
    for i in range(p.reInsertIterations):
        possibleTTW = findPossibleTTW(possibleTTW, otListReInsert, otListScheduled)
        otListReInsert = generateNewOTList(possibleTTW, otListScheduled, btList, gstwList, p)

        print("======= Starting re-insertion phase for unscheduled observation tasks =======")
        n_before = len(otListScheduled)
        fullScheduleFound, btList, dtList, otListScheduled = scheduleTransmissions(otListReInsert, ttwList, gstwList, p,
                                                                                   otListScheduled, btList, dtList)
        n_after = len(otListScheduled)
        print(f"Successfully re-inserted {n_after - n_before} observation tasks out of {len(otListReInsert)}")

    latencyCounter(otListScheduled, dtList)
    btList, dtList = cleanUpSchedule(otListScheduled, btList, dtList, gstwList)
    latencyCounter(otListScheduled, dtList)

    return fullScheduleFound, btList, dtList, otListScheduled


def scheduleTransmissions(otList: list[OT], ttwList: list[TTW], gstwList: list[GSTW], parameters: TransmissionParams,
                          existingOTList: list[OT] = None, existingBTList: list[BT] = None,
                          existingDTList: list[DT] = None) -> tuple[bool, list[BT], list[DT], list[OT]]:
    """
    Try to schedule the transmission of each observed target in otList.
    Transmission consists of transmitting to Ground Station and buffering the capture before actually transmitting.
    The observation tasks will be considered in the order that they are provided, so sorting by priority is recommended.

    Args:
        otList (list[OT]): List of observation tasks to schedule transmissions for.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.
        gstwList (list[GSTW]): List of ground station time windows with time windows corresponding to each GS.
        parameters (TransmissionParams): Parameters for the transmission scheduling.
        existingOTList (list[OT], optional): List of already scheduled observation tasks.
        existingBTList (list[BT], optional): List of already scheduled buffering tasks.
        existingDTList (list[DT], optional): List of already scheduled downlink tasks.

    Returns:
        tuple[bool, list[BT], list[DT], list[OT]]: A tuple containing:

            - A boolean indicating if a transmission schedule has been found for all observation tasks.
              If false, there can still be a useful output containing a schedule for the tasks that were able to fit.
            - A list of scheduled buffering tasks (BT).
            - A list of scheduled downlink tasks (DT).
            - A list of observation tasks, possibly changed to fit the buffering and downlinking tasks.
    """
    p = parameters

    directInsert = insertion.DirectInsertion(p)
    slideInsert = insertion.SlideInsertion(p)
    deleteInsert = insertion.DeleteInsertion(p)
    insertList: list[insertion.InsertionInterface] = [directInsert, slideInsert, deleteInsert]

    btList: list[BT] = existingBTList.copy() if existingBTList is not None else []
    dtList: list[DT] = existingDTList.copy() if existingDTList is not None else []

    otListMod = otList.copy()  # This is the list of observation tasks that will be kept updated as tasks are deleted or shifted

    if existingOTList is not None:
        # Check if there are any tasks in the existing OT list that are also in the list to be scheduled
        for existingOT in existingOTList:
            for ot in otListMod:
                if ot.GT == existingOT.GT:
                    raise ValueError("The existing OT list contains a task that is also in the list to be scheduled.")

        # We will add the existing OT list as highest priority to the list,
        # making it less likely for them to be modified or deleted
        otListMod = existingOTList.copy() + otListMod

    for otOriginal in otList:
        # First check if the observation task already has a corresponding buffering task
        alreadyBuffered = False
        for bt in btList:
            if bt.GT == otOriginal.GT:
                alreadyBuffered = True
                break

        if alreadyBuffered: continue

        # Match the original OT to the most recently updated version that has been possibly shifted or deleted
        otToBuffer = None
        for ot in otListMod:
            if ot.GT == otOriginal.GT:
                otToBuffer = ot
                break

        # If we could not find the OT in the modified list, it has been deleted, and we can continue to the next OT
        if otToBuffer is None: continue

        if observationTaskConflicting(otToBuffer, btList, otListMod, gstwList, p):
            # The observation task is conflicting with already scheduled tasks, so we cannot buffer it
            otListMod.remove(otToBuffer)
            continue

        validBTFound = False
        closestGSTW = getClosestGSTW(otToBuffer, gstwList, p.maxLatency)
        closestGSTWSorted = gstwToSortedTupleList(closestGSTW)

        # Iterate over the closest ground station passes and try to buffer it before the pass
        for i, entry in enumerate(closestGSTWSorted):
            if validBTFound:
                # If a valid buffer task has been found we don't need to look further
                break
            for insertMethod in insertList:
                gstw = GSTW(entry[0], [entry[1]])
                nextGSTW = GSTW(closestGSTWSorted[i + 1][0], [closestGSTWSorted[i + 1][1]]) \
                    if i + 1 < len(closestGSTWSorted) else None

                candidateDTList = generateDownlinkTask(gstw, nextGSTW, p.downlinkDuration, dtList, otToBuffer, p)
                if candidateDTList is None: continue  # No valid downlink task could be scheduled in this ground station time window

                bt, otListMod, btList = insertMethod.generateBuffer(otToBuffer, gstw, otListMod, btList, gstwList,
                                                                    ttwList)

                if bt is not None:
                    btList.append(bt)
                    for candidate in candidateDTList:
                        dtList.append(candidate)
                    validBTFound = True
                    # We found a buffer task and corresponding GSTW to downlink, so we don't need to consider other GSTW
                    break

        if not validBTFound:
            # No valid GSTW has been found to downlink the buffered data
            print(f"Transmission scheduling failed for {otToBuffer.GT.id} at {otToBuffer.start}")
            # Remove the currently considered observation task by checking if ground target matches
            otListMod.remove(otToBuffer)

    completeScheduleFound = len(otListMod) == len(otList)
    return completeScheduleFound, btList, dtList, otListMod


def cleanUpSchedule(otList: list[OT], btList: list[BT], dtList: list[DT], gstwList: list[GSTW]) -> tuple[
    list[BT], list[DT]]:
    """
    Clean up the schedule by re-assigning buffer and transmission tasks to other ground targets if possible.
    Each OT will be assigned to the closest BT in chronological order.
    And so will each BT to the closest DT.
    No time windows will be adjusted, the tasks will simply be assigned to another ground target.

    Args:
        otList (list[OT]): List of observation tasks.
        btList (list[BT]): List of buffering tasks.
        dtList (list[DT]): List of downlink tasks.
        gstwList (list[GSTW]): List of ground station time windows.

        Returns:
            tuple[list[BT], list[DT]]: The cleaned up lists of buffering tasks and downlink tasks.
    """
    btListCleaned = []
    dtListCleaned = []

    otListTimeSorted = sorted(otList, key=lambda x: x.start)
    btListTimeSorted = sorted(btList, key=lambda x: x.start)
    dtListTimeSorted = sorted(dtList, key=lambda x: x.start)

    # First re-assign the buffer tasks to have the same ground target as the closest observation task
    if len(otListTimeSorted) != len(btListTimeSorted):
        print("Cannot clean up schedule, number of observation tasks and buffer tasks do not match")
        return btList, dtList

    for i, bt in enumerate(btListTimeSorted):
        newBT = BT(otListTimeSorted[i].GT, bt.start, bt.end)
        btListCleaned.append(newBT)

    # Now re-assign the downlink tasks to have the same ground target as the closest buffer task
    dtListTimeSortedDirty = dtListTimeSorted.copy()  # List from which we will remove DT as they are re-assigned
    btListTimeSortedClean = sorted(btListCleaned, key=lambda x: x.start)
    for i, bt in enumerate(btListTimeSortedClean):
        # Find the closest DT that is after the BT
        closestDT = dtListTimeSortedDirty[0]
        oldGT = closestDT.GT
        # There might be several DT with the same GT, so change the GT of all of them
        for dt in dtListTimeSorted:
            if dt.GT == oldGT:
                dtListCleaned.append(DT(bt.GT, dt.GS, dt.start, dt.end))
                dtListTimeSortedDirty.remove(dt)

    # Do an extra cleaning pass over the downlink schedule to make sure split up tasks happen in the right order
    dtListCleaned = cleanUpDownlinkSchedule(dtListCleaned, gstwList)

    return btListCleaned, dtListCleaned


def cleanUpDownlinkSchedule(dtList: list[DT], gstwList: list[GSTW]):
    """
    Clean up downlink schedule by making sure that downlinks split over two ground station passes are scheduled in the correct order.

    Args:
        dtList (list[DT]): List of downlink tasks.
        gstwList (list[GSTW]): List of ground station time windows.

    Returns:
        list[DT]: Cleaned up list of downlink tasks.
    """

    gstwSorted = gstwToSortedTupleList(gstwList)
    dtListClean: list[DT] = []
    for i, entry in enumerate(gstwSorted):
        gs = entry[0]
        tw = entry[1]

        # Save the downlink tasks that happen in this ground station pass
        dtListForGS = [dt for dt in dtList if dt.GS == gs and dt.start >= tw.start and dt.end <= tw.end]
        dtListInGSSorted = sorted(dtListForGS, key=lambda x: x.start)
        if len(dtListInGSSorted) <= 1:
            # No need to clean up if there is only one or zero downlink tasks in this GS pass
            dtListClean = dtListClean + dtListInGSSorted
            continue

        # Determine the time between two downlink tasks in this GS pass
        interTaskTime = dtListInGSSorted[1].start - dtListInGSSorted[0].end

        # Find the possible downlink tasks that are also scheduled in the previous ground station pass
        if i > 0:
            prevEntry = gstwSorted[i - 1]
            prevGS = prevEntry[0]
            prevTW = prevEntry[1]

            # Find the list of downlink tasks that are scheduled in the previous GS pass
            dtListInPrevGS = [dt for dt in dtList if
                              dt.GS == prevGS and dt.start >= prevTW.start and dt.end <= prevTW.end]

            # See if one of the downlink tasks in the previous GS pass covers the same ground target
            # as one of the downlink tasks in the current GS pass
            dtSplitPrevious = None
            for dt in dtListInGSSorted:
                for dtPrev in dtListInPrevGS:
                    if dt.GT == dtPrev.GT:
                        dtSplitPrevious = dt
                        break

            if dtSplitPrevious and dtListInGSSorted.index(dtSplitPrevious) != 0:
                # We have found a downlink task that is split over the current and previous GS pass
                # Additionally, this downlink task is not the first task in the current GS pass, we need to fix that
                dtStart = dtListInGSSorted[0].start
                dtSplitDuration = dtSplitPrevious.end - dtSplitPrevious.start
                dtListInGSSorted.insert(0,
                                        DT(dtSplitPrevious.GT, dtSplitPrevious.GS, dtStart, dtStart + dtSplitDuration))
                dtListInGSSorted.remove(dtSplitPrevious)

                # Now that the split task is first in the list, all other tasks need to be shifted to prevent conflicts
                for j in range(1, len(dtListInGSSorted)):
                    dtCheck = dtListInGSSorted[j]
                    if downlinkTaskConflicting(dtCheck, dtListInGSSorted):
                        # Shift it to the right
                        dtNewStart = dtListInGSSorted[j - 1].end + interTaskTime
                        dtNewEnd = dtNewStart + (dtCheck.end - dtCheck.start)
                        dtListInGSSorted[j] = DT(dtCheck.GT, dtCheck.GS, dtNewStart, dtNewEnd)

        # After fixing possible split tasks, add the downlink tasks in this GS pass to the cleaned list
        dtListClean = dtListClean + dtListInGSSorted

    return dtListClean
