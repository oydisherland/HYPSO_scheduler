from scheduling_model import GSTW, DT, TW, GS, GT, OT
from transmission_scheduling.conflict_checks import downlinkTaskConflicting
from transmission_scheduling.input_parameters import TransmissionParams
from transmission_scheduling.util import getAvailableDownlinkTime


def generateDownlinkTask(otList: list[OT], gstw: GSTW, nextGSTWList: list[tuple[GS,TW]],
                         dtList: list[DT], gtToDownlink: GT, p: TransmissionParams) -> list[DT] | None:
    """
    Tries to schedule an entire downlink of an observation task in two given ground station time windows.
    Returns a list of downlink task with either one entry if the task fit within the first window
    or two if it needs to be spread over two windows.

    Args:
        otList (list[OT]): The already scheduled observation tasks
        gstw (GSTW): The ground station time window to schedule the downlink task in.
        nextGSTWList (list[tuple[GS,TW]]): The list of all future ground station passes that are considered for this OT.
        dtList (list[DT]): List of all already scheduled downlink tasks.
        gtToDownlink (GT): The ground target of which the capture needs to be downlinked.
        p (TransmissionParams): The transmission scheduling parameters.

    Returns:
        list[DT]: A list of scheduled downlink tasks, or None if no valid scheduling was found.
    """
    candidateDT, isPartialSchedule = generatePartialDownlinkTask(otList, gstw, p.downlinkDuration, dtList,
                                                                 gtToDownlink, p)
    candidateList = [candidateDT]

    if candidateDT is None:
        # No valid downlink task could be scheduled in this ground station time window
        return None

    if not isPartialSchedule:
        # The full downlink was scheduled in the first GSTW
        return candidateList

    if not nextGSTWList:
        # No next GSTW were provided, so we cannot schedule the remaining part of the downlink task
        return None

    remainingDownlinkTime = p.downlinkDuration
    previousCandidateSuccess = True
    for entry in nextGSTWList:
        nextGSTW = GSTW(entry[0], [entry[1]])
        # Now we know the first part of the downlink task was scheduled, try to schedule the remaining part in the next GSTW
        if previousCandidateSuccess:
            remainingDownlinkTime -= (candidateList[-1].end - candidateList[-1].start)
        newCandidateDT, isPartialSchedule = generatePartialDownlinkTask(otList, nextGSTW,
                                                                        remainingDownlinkTime, dtList, gtToDownlink, p)
        previousCandidateSuccess = newCandidateDT is not None
        if previousCandidateSuccess:
            candidateList.append(newCandidateDT)

        if not isPartialSchedule:
            # The full remaining downlink was scheduled in this GSTW
            break

    if not isPartialSchedule:
        return candidateList
    else:
        # Even after trying to schedule in all provided next GSTWs, we could not schedule the full downlink task
        return None


def generatePartialDownlinkTask(otList: list[OT], gstw: GSTW, desiredDownlinkTime: float,
                                dtList: list[DT], gtToDownlink: GT, p: TransmissionParams):
    """
    Try to schedule downlink tasks in the given ground station time window for the given observation task.
    If the downlink task cannot fit in the schedule, try to schedule a partial downlink task.

    Args:
        otList (list[OT]): The already scheduled observation tasks
        gstw (GSTW): The ground station time window to schedule the downlink task in.
        desiredDownlinkTime (float): The length in seconds of the downlink task to schedule.
        dtList (list[DT]): List of all already scheduled downlink tasks.
        gtToDownlink (GT): The ground target of which the capture needs to be downlinked.
        p (TransmissionParams): The transmission scheduling parameters.

    Returns:
        tuple[DT, bool]: A tuple containing:

            - DT: The scheduled downlink tasks, or None if no valid scheduling was found.
            - bool: True if only a partial downlink task was scheduled, False if the full downlink task was scheduled.
    """
    # First check if the ground station pass is long enough for downlinking at least some of the data
    if gstw.TWs[0].end - gstw.TWs[0].start < p.minGSWindowTime:
        return None, True

    # Check the available downlink time during this ground station pass
    availableTime = getAvailableDownlinkTime(gstw.TWs[0], dtList, otList, p)
    epsilon = 0.1 #seconds
    if availableTime < epsilon:
        return None, True

    partial = availableTime <= desiredDownlinkTime
    downlinkTime = min(availableTime, desiredDownlinkTime)

    # First try to insert the downlink task at the start of the ground station time window
    dtStart = gstw.TWs[0].start + p.transmissionStartTime
    dtEnd = dtStart + downlinkTime
    candidateDT = DT(gtToDownlink, gstw.GS, dtStart, dtEnd)
    if dtEnd <= gstw.TWs[0].end:
        if not downlinkTaskConflicting(candidateDT, dtList):
            return candidateDT, partial

    # Now try to start the downlink task at the end of other downlink tasks
    otherDTList = [dt for dt in dtList if dt.start > gstw.TWs[0].start and dt.end < gstw.TWs[0].end]
    for otherDT in otherDTList:
        dtStart = otherDT.end
        dtEnd = dtStart + downlinkTime
        candidateDT = DT(gtToDownlink, gstw.GS, dtStart, dtEnd)

        if dtEnd <= gstw.TWs[0].end:
            if not downlinkTaskConflicting(candidateDT, dtList):
                return candidateDT, partial

    return None, True