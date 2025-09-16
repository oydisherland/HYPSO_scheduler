import datetime

import data_postprocessing.algorithmData_api as AD_api
from data_preprocessing.get_target_passes import getGroundStationTimeWindows
from scheduling_model import OT, TTW, BT, GSTW, TW, DT
import time

from conflict_checks import downlinkTaskConflicting
import insertion
from input_parameters import getInputParams
from util import plotSchedule, getClosestGSTW, gstwToSortedTupleList


# TODO re-order transmission tasks such that split up transmission tasks are next to each other
# TODO make a cleaning sweep re-assigning transmission tasks to buffer tasks that are close to each other, same could be done for captures and their buffering
# TODO after/inter task/capture time are used quite randomly, it should be more clear where they are used (for example when checking for conflicts), they are not used uniformly and difficult to change
# TODO consider that data transmission cannot happen or is at least slower during a capture when in the transmission window
# TODO possibly add support for spreading transmission over more than 2 ground station passes



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
    directInsert = insertion.DirectInsertion(p)
    slideInsert = insertion.SlideInsertion(p)
    deleteInsert = insertion.DeleteInsertion(p)

    btList: list[BT] = []
    dtList: list[DT] = []

    otListMod = otList.copy() # This is the list of observation tasks that will be kept updated as tasks are deleted or shifted
    completeScheduleFound = True

    for otOriginal in otList:
        # First match the original OT to the most recently updated version that has been possibly shifted or deleted
        otToBuffer = None
        for ot in otListMod:
            if ot.GT == otOriginal.GT:
                otToBuffer = ot
                break

        # If we could not find the OT in the modified list, it has been deleted, and we can continue to the next OT
        if otToBuffer is None:
            continue

        # For each observation task to buffer, try to buffer it considering the downlink in one of the closest ground station time windows
        validBTFound = False
        closestGSTW = getClosestGSTW(otToBuffer, gstwList, p.maxGSTWAhead)
        closestGSTWSorted = gstwToSortedTupleList(closestGSTW)

        for i, entry in enumerate(closestGSTWSorted):
            gstw = GSTW(entry[0], [entry[1]])
            nextGSTW = GSTW(closestGSTWSorted[i + 1][0], [closestGSTWSorted[i + 1][1]]) \
                if i + 1 < len(closestGSTWSorted) else None

            candidateDTList = generateDownlinkTask(gstw, nextGSTW, p.downlinkDuration, dtList, otToBuffer)
            if candidateDTList is None: continue  # No valid downlink task could be scheduled in this ground station time window

            bt, _, _ = directInsert.generateBuffer(otToBuffer, gstw, otListMod, btList, gstwList)

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

                candidateDTList = generateDownlinkTask(gstw, nextGSTW, p.downlinkDuration, dtList, otToBuffer)
                if candidateDTList is None: continue  # No valid downlink task could be scheduled in this ground station time window

                # Now that we know the downlink task is scheduled, try to schedule the buffering task
                bt, otListMod, btList = slideInsert.generateBuffer(otToBuffer, gstw, otListMod, btList, gstwList,
                                                                      ttwList)

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

                candidateDTList = generateDownlinkTask(gstw, nextGSTW, p.downlinkDuration, dtList, otToBuffer)
                if candidateDTList is None: continue  # No valid downlink task could be scheduled in this ground station time window

                # Now that we know the downlink task is scheduled, try to schedule the buffering task
                otListPrioritySorted = otListMod.copy()  # The provided otList should already be priority sorted
                bt, otListMod, _  = deleteInsert.generateBuffer(otToBuffer, gstw, otListPrioritySorted, btList, gstwList)

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
            # Remove the currently considered observation task by checking if ground target matches
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
    remainingDownlinkTime = p.downlinkDuration - (candidateDT.end - candidateDT.start)
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
    if gstw.TWs[0].end - gstw.TWs[0].start < p.minGSWindowTime:
        return None, True

    # First try to insert the downlink task at the start of the ground station time window
    dtStart = gstw.TWs[0].start + p.transmissionStartTime
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
        dtStart = otherDT.end + p.interDownlinkTime
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


parametersFilePath = "../data_input/input_parameters.csv"
p = getInputParams(parametersFilePath)

groundStationFilePath = "data_input/HYPSO_data/ground_stations.csv"

otList = AD_api.getScheduleFromFile("BS_test12-run1.json")  # observation task
otListPrioSorted = sorted(otList, key=lambda x: x.GT.priority, reverse=True)

# Create TTW list by adding some time before and after each observation task
ttwList: list[TTW] = []
for ot in otList:
    ttwStart = max(0, ot.start - 50)
    ttwEnd = min(p.ohDuration, ot.end + 50)
    ttwList.append(TTW(ot.GT, [TW(ttwStart, ttwEnd)]))

startTimeOH = datetime.datetime(2025, 8, 27, 15, 29, 0)
startTimeOH = startTimeOH.replace(tzinfo=datetime.timezone.utc)
endTimeOH = startTimeOH + datetime.timedelta(seconds=p.ohDuration)

gstwList = getGroundStationTimeWindows(startTimeOH, endTimeOH, p.minGSWindowTime, groundStationFilePath, p.hypsoNr)

start_time = time.perf_counter()
valid, btList, dtList, otListModified = scheduleTransmissions(otListPrioSorted, ttwList, gstwList)
end_time = time.perf_counter()

print(f"{(end_time - start_time) * 1000:.4f} milliseconds")

plotSchedule(otListModified, otListPrioSorted, btList, dtList, gstwList, ttwList, p)
