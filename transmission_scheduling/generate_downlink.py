from scheduling_model import GSTW, DT, OT
from transmission_scheduling.conflict_checks import downlinkTaskConflicting
from transmission_scheduling.input_parameters import TransmissionParams


def generateDownlinkTask(gstw: GSTW, nextGSTW: GSTW, downlinkTime: float, dtList: list[DT], otToDownlink: OT,
                         p: TransmissionParams):
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
        p (TransmissionParams): The transmission scheduling parameters.

    Returns:
        list[DT]: A list of scheduled downlink tasks, or None if no valid scheduling was found.
    """
    candidateDT, isPartialSchedule = generatePartialDownlinkTask(gstw, downlinkTime, dtList, otToDownlink, p)
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
    candidateDT2, isPartialSchedule = generatePartialDownlinkTask(nextGSTW, remainingDownlinkTime, dtList, otToDownlink,
                                                                  p)

    if isPartialSchedule or candidateDT2 is None:
        return None
    else:
        # We can schedule the remaining part of the downlink task in the next GSTW
        # Merge the two downlink tasks into one
        candidateList.append(candidateDT2)
        return candidateList


def generatePartialDownlinkTask(gstw: GSTW, downlinkTime: float, dtList: list[DT], otToDownlink: OT,
                                p: TransmissionParams):
    """
    Try to schedule downlink tasks in the given ground station time window for the given observation task.
    If the downlink task cannot fit in the schedule, try to schedule a partial downlink task.

    Args:
        gstw (GSTW): The ground station time window to schedule the downlink task in.
        downlinkTime (float): The length in seconds of the downlink task to schedule.
        dtList (list[DT]): List of all already scheduled downlink tasks.
        otToDownlink (OT): The observation task to schedule the downlink for.
        p (TransmissionParams): The transmission scheduling parameters.

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