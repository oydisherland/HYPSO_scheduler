from scheduling_model import OT, BT, GSTW, TW, DT
from transmission_scheduling.input_parameters import TransmissionParams
from transmission_scheduling.util import getFreeGSGaps, bufferFileCounter, gstwToSortedTupleList


def getConflictingTasks(tw: TW, btList: list[BT], otList: list[OT], gstwList: list[GSTW], p: TransmissionParams, cancelEarly: bool = False):
    """
    Get the list of tasks that conflict with the given time window.

    Args:
        tw (TW): The time window to check for conflicts, this window should include any processing time after the task.
        btList (list[BT]): List of all already scheduled buffering tasks.
        otList (list[OT]): List of all observation tasks.
        gstwList (list[GSTW]): List of all ground station time windows.
        p (TransmissionParams): Input parameters containing timing configurations.
        cancelEarly (bool, optional): If True, the function will return as soon as a single conflict is found.

    Returns:
        tuple[list[OT], list[BT], list[GSTW]]: A tuple containing:

            - list[OT]: List of conflicting observation tasks.
            - list[BT]: List of conflicting buffering tasks.
            - list[GSTW]: List of conflicting ground station time windows.
    """
    conflictingOTs: list[OT] = []
    conflictingBTs: list[BT] = []
    conflictingGSTWs: list[GSTW] = []

    for ot in otList:
        if ot.start >= tw.end or ot.end + p.afterCaptureTime <= tw.start:
            continue
        else:
            conflictingOTs.append(ot)
            if cancelEarly: return conflictingOTs, conflictingBTs, conflictingGSTWs

    for otherBT in btList:
        if otherBT.start >= tw.end or otherBT.end + p.interTaskTime <= tw.start:
            continue
        else:
            conflictingBTs.append(otherBT)
            if cancelEarly: return conflictingOTs, conflictingBTs, conflictingGSTWs

    for gstw in gstwList:
        for gstw_tw in gstw.TWs:
            if gstw_tw.start >= tw.end or gstw_tw.end + p.interTaskTime <= tw.start:
                continue
            else:
                conflictingGSTWs.append(gstw)
                if cancelEarly: return conflictingOTs, conflictingBTs, conflictingGSTWs

    return conflictingOTs, conflictingBTs, conflictingGSTWs


def bufferTaskConflicting(bt: BT, btList: list[BT], otList: list[OT], dtList: list[DT], gstwList: list[GSTW],
                          p: TransmissionParams, checkHypso2BufferLimit: bool = True):
    """
    Check if the buffering task overlaps with any other scheduled tasks.

    Args:
        bt (BT): The buffering task to validate.
        btList (list[BT]): List of all already scheduled buffering tasks.
        otList (list[OT]): List of all observation tasks.
        dtList (list[DT]): List of all already scheduled downlink tasks plus the candidate downlink tasks.
        gstwList (list[GSTW]): List of all ground station time windows.
        p (TransmissionParams): Input parameters containing timing configurations.
        checkHypso2BufferLimit (bool, optional): If True, also check for conflicts with the HYPSO-2 buffer size limit.

    Returns:
        bool: True if the buffering task conflicts with any other task, False otherwise.
    """
    bufferTimeWindow = TW(bt.start, bt.end + p.interTaskTime)
    # Remove the buffer task from the list to prevent self conflict
    btListOther = [otherBT for otherBT in btList if otherBT != bt]
    conflictOTs, conflictBTs, conflictGSTWs = getConflictingTasks(bufferTimeWindow, btListOther, otList, gstwList, p, True)
    conflict =  bool(conflictOTs or conflictBTs or conflictGSTWs)
    if conflict:
        return True

    if not checkHypso2BufferLimit:
        return False

    # Also check for the buffer file limit
    newBTList = btList.copy()
    newBTList.append(bt)
    return hypso2BufferLimitConflicting(newBTList, dtList, gstwList, p)

def observationTaskConflicting(ot: OT, btList: list[BT], otList: list[OT], gstwList: list[GSTW], p: TransmissionParams):
    """
    Check if the observation task overlaps with any other scheduled tasks.

    Args:
        ot (OT): The observation task to validate.
        btList (list[BT]): List of all already scheduled buffering tasks.
        otList (list[OT]): List of all observation tasks.
        gstwList (list[GSTW]): List of all ground station time windows.
        p (TransmissionParams): Input parameters containing timing configurations.

    Returns:
        bool: True if the observation task conflicts with any other task, False otherwise.
    """

    observationTimeWindow = TW(ot.start, ot.end + p.afterCaptureTime)
    # Remove instances of the observation task itself from the list
    otListOther = [otherOT for otherOT in otList if otherOT != ot]
    conflictOTs, conflictBTs, conflictGSTWs = getConflictingTasks(observationTimeWindow, btList, otListOther, gstwList,
                                                                  p, True)
    return bool(conflictOTs or conflictBTs or conflictGSTWs)


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


def hypso2BufferLimitConflicting(btList: list[BT], dtList: list[DT], gstwList: list[GSTW], p: TransmissionParams,
                                 printResults:bool = False) -> bool:
    """
    Check whether the buffer tasks scheduled would result in a conflict with the buffer size limit.

    The HYPSO satellites have a limit of the number of files that can be in the buffer.
    The buffer is ordered by priority, and each GS pass the highest priority files will be downlinked first.
    So if something is in the lowest priority slot, it will stay there until all files from the buffer are downlinked.
    This means that we must ensure that the buffer is fully cleaned before the max latency is reached.
    In the case of HYPSO-2, I have chosen to do this by ensuring that at some point, 1 or 2 buffer tasks
    get two full GS passes of time to downlink, this is likely enough to fully clean the buffer.
    Finding such a point where the buffer is fully cleaned is done by finding two adjacent ground station passes
    where there are no buffering tasks scheduled in between them.
    If buffer is only filled with one or two files before these two passes, then the buffer will be fully cleaned.
    """
    gstwSortedTupleList = gstwToSortedTupleList(gstwList)
    freeGSGapList = getFreeGSGaps(btList, gstwSortedTupleList)
    # Now that we have found the GS passes with no buffering tasks in between them,
    # verify that the buffer is empty enough before the first of these two passes
    bufferClearedTimestamps = [] # List of timestamps when the buffer is cleared
    for freeGSGap in freeGSGapList:
        preGapFileCount = bufferFileCounter(btList, dtList, freeGSGap.start)
        if preGapFileCount <= 2:
            bufferClearedTimestamps.append(freeGSGap.end)

    # Additionally, the buffer should also be cleared at the end of the schedule
    lastGSTW = gstwSortedTupleList[-1]
    if not bufferClearedTimestamps[-1] >= lastGSTW[1].start:
        return True

    bufferClearedTimestamps.insert(0, 0)

    if printResults:
        print(bufferClearedTimestamps)

    # Check if the buffer is cleared often enough
    for i in range(len(bufferClearedTimestamps) - 1):
        bufferClearedStart = bufferClearedTimestamps[i]
        bufferClearedEnd = bufferClearedTimestamps[i+1]
        buffers = [bt for bt in btList if not (bt.end < bufferClearedStart or bt.start > bufferClearedEnd)]
        # Check if the duration between buffer clearing is too lang with too many buffers planned in between
        if bufferClearedEnd - bufferClearedStart > p.maxLatency and len(buffers) > 6:
            return True

    return False
