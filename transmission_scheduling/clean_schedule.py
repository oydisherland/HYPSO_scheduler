from scheduling_model import BT, OT, DT, GSTW, GS, TW
from transmission_scheduling.generate_downlink import generateDownlinkTask
from transmission_scheduling.input_parameters import TransmissionParams
from transmission_scheduling.util import gstwToSortedTupleList, getBufferClearedTimestamps, getClosestGSTW

from enum import Enum

class OrderType(Enum):
    FIFO = 1
    PRIORITY = 2


def cleanUpSchedule(otList: list[OT], btList: list[BT], dtList: list[DT], gstwList: list[GSTW],
                    parameters: TransmissionParams, bufferOrder: OrderType, downlinkOrder: OrderType) \
        -> tuple[list[BT], list[DT]]:
    """
    Clean up the schedule by re-assigning buffer and transmission tasks to other ground targets if possible.
    The time windows for the downlink tasks will also be adjusted to reflect the real downlink strategy better.

    Args:
        otList (list[OT]): List of observation tasks.
        btList (list[BT]): List of buffering tasks.
        dtList (list[DT]): List of downlink tasks.
        gstwList (list[GSTW]): List of ground station time windows.
        parameters (TransmissionParams): Input parameters containing timing configurations.
        bufferOrder (OrderType): The order in which to re-assign buffer tasks to observation tasks (FIFO or PRIORITY).
        downlinkOrder (OrderType): The order in which to re-assign downlink tasks to observation tasks (FIFO or PRIORITY).

        Returns:
            tuple[list[BT], list[DT]]: The cleaned up lists of buffering tasks and downlink tasks.
    """
    p = parameters

    # The buffers are already scheduled in priority order, so we only rearrange for FIFO
    btListCleaned = arrangeBufferScheduleFIFO(btList, otList) if bufferOrder == OrderType.FIFO else btList.copy()

    btListCleaned = assignBufferIDs(btListCleaned, dtList, gstwList, p, downlinkOrder)

    dtListCleaned = regenerateDownlinkSchedule(btListCleaned, gstwList, p)


    return btListCleaned, dtListCleaned

def arrangeBufferScheduleFIFO(btList: list[BT], otList: list[OT]):
    btListCleaned = []

    otListTimeSorted = sorted(otList, key=lambda x: x.start)
    btListTimeSorted = sorted(btList, key=lambda x: x.start)

    # Re-assign the buffer tasks to have the same ground target as the closest observation task
    if len(otListTimeSorted) != len(btListTimeSorted):
        print("Cannot clean up buffer schedule, number of observation tasks and buffer tasks do not match")
        return btList

    for i, bt in enumerate(btListTimeSorted):
        newBT = BT(otListTimeSorted[i].GT, -1, bt.start, bt.end)
        btListCleaned.append(newBT)

    return btListCleaned

def assignBufferIDs(btList: list[BT], dtList: list[DT], gstwList: list[GSTW], p: TransmissionParams,
                    downlinkOrder: OrderType) -> list[BT]:
    """
    Assign file IDs to each buffer task.
    """
    btListSorted = btList.copy()
    if downlinkOrder == OrderType.PRIORITY:
        btListSorted = sorted(btList, key=lambda x: x.GT.priority, reverse=True)
    elif downlinkOrder == OrderType.FIFO:
        btListSorted = sorted(btList, key=lambda x: x.start)

    gstwSortedTupleList = gstwToSortedTupleList(gstwList)
    bufferClearedTimestamps = getBufferClearedTimestamps(btList, dtList, gstwSortedTupleList)

    btListFileID: list[BT] = []
    for bt in btListSorted:
        highestIDFree = getHighestFreeBufferID(bt, btListFileID, bufferClearedTimestamps, p)
        newBT = BT(bt.GT, highestIDFree, bt.start, bt.end)
        btListFileID.append(newBT)

    return btListFileID


def regenerateDownlinkSchedule(btList: list[BT], gstwList: list[GSTW], p: TransmissionParams) -> list[DT]:
    """
    Regenerate the downlink schedule based on the cleaned buffer schedule.
    HYPSO automatically downlinks the highest priority file form the buffer first, and this function simulates that.
    """
    dtListCleaned: list[DT] = []
    # Sort the buffer tasks by file ID, then by start time
    btListSorted = sorted(btList, key=lambda x: (x.fileID, x.start))
    for bt in btListSorted:
        closestGSTW = getClosestGSTW(bt.end, gstwList)
        closestGSTWSorted = gstwToSortedTupleList(closestGSTW)

        for i, entry in enumerate(closestGSTWSorted):
            gstw = GSTW(entry[0], [entry[1]])
            # Find the list of future GSTW that could be used to downlink the remaining data if needed
            nextGSTWList: list[tuple[GS, TW]]  # Storing the GS passes in this form is more convenient
            nextGSTWList = closestGSTWSorted[i + 1:] if i + 1 < len(closestGSTWSorted) else []
            newDT = generateDownlinkTask(gstw, nextGSTWList, dtListCleaned, bt.GT, p)
            if newDT is not None:
                # Valid downlink task(s) were generated
                dtListCleaned = dtListCleaned + newDT
                break

    return dtListCleaned

def getHighestFreeBufferID(btToCheck: BT, btList: list[BT], bufferClearedTimestamps: list[float],
                           p: TransmissionParams) -> int:
    """
    Get the buffer ID with the highest priority that is free at the given timestamp.

    Args:
        btToCheck (BT): The buffering task for which to find a free buffer ID.
        btList (list[BT]): List of buffering tasks after the latest buffer clearing
        bufferClearedTimestamps (list[float]): List of timestamps at which the buffer is cleared
        p (TransmissionParams): Input parameters containing timing configurations.
    """
    freeIDs = list(range(p.bufferStartID, p.bufferStartID + p.maxBufferFiles))
    thisDownlinkEndTime = getDownlinkEndTime(btToCheck, bufferClearedTimestamps)
    for bt in btList:
        if bt.start > thisDownlinkEndTime:
            continue

        downlinkEndTime = getDownlinkEndTime(bt, bufferClearedTimestamps)
        if downlinkEndTime > btToCheck.start:
            # This buffer task is still in the buffer at the given timestamp
            if bt.fileID in freeIDs:
                freeIDs.remove(bt.fileID)

    if not freeIDs:
        raise ValueError("No free buffer IDs available during cleanup of schedule")

    return freeIDs[0]


def getDownlinkEndTime(bt: BT, bufferClearedTimestamps: list[float]) -> float:
    """
    Find the time at which the buffer task is guaranteed to be fully downlinked
    For now, the assumption is made that this is at a time when the buffer can be fully cleared
    """
    # Find the first timestamp that is later than the bt end time
    for ts in bufferClearedTimestamps:
        if ts > bt.end:
            return ts
    return float("inf")