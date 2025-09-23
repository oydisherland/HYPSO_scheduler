from scheduling_model import OT, GSTW, BT, TTW, TW, DT
from transmission_scheduling.conflict_checks import bufferTaskConflicting, observationTaskConflicting
from transmission_scheduling.insertion.insertion_interface import InsertionInterface
from transmission_scheduling.insertion.direct_insertion import DirectInsertion
from transmission_scheduling.util import gstwToSortedTupleList
from transmission_scheduling.input_parameters import TransmissionParams


class SlideInsertion(InsertionInterface):

    def __init__(self, parameters: TransmissionParams):
        """
        Initialize the DirectInsertion class with the given parameters.
        """
        self.p = parameters
        self.direct_insert = DirectInsertion(parameters)

    def generateBuffer(self, otToBuffer: OT, gstwToDownlink: GSTW, otList: list[OT], btList: list[BT],
                       dtList: list[DT], gstwList: list[GSTW], ttwList: list[TTW] = None) -> tuple[BT | None, list[OT], list[BT]]:
        """
        Try to insert the buffering of an observed target into the schedule by shifting other observation tasks if necessary.

        Args:
            otToBuffer (OT): The observation task to schedule buffering for.
            gstwToDownlink (GSTW): The ground station time window to use for downlinking the buffered data.
            otList (list[OT]): List of all observation tasks
            btList (list[BT]): List of all already scheduled buffering tasks.
            dtList (list[DT]): List of all already scheduled downlinking tasks plus the candidate downlink tasks.
            gstwList (list[GSTW]): List of all ground station time windows.
            ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.

        Returns:
            tuple[BT, list[OT], list[BT]]: A tuple containing:

                - BT: The scheduled buffering task, or None if no valid scheduling was found.
                - list[OT]: Modified list of observation tasks, with any shifted tasks updated.
                - list[BT]: Modified list of buffering tasks, with any shifted tasks updated.
        """
        p = self.p

        if ttwList is None:
            raise ValueError("TTW list must be provided for sliding insertion.")

        otListOriginal = otList.copy()
        otListModified = otList.copy()
        btListOriginal = btList.copy()
        btListModified = btList.copy()
        otToBufferShifted = otToBuffer

        shiftBackwardPossible = True
        shiftForwardPossible = True

        shiftWindow = TW(otToBuffer.end, gstwToDownlink.TWs[0].start)  # Time window in which we can shift

        # Find the largest gap that exists in this window, this is where we will try to make room to fit the buffer
        gapLength, gapTW = self.getLargestTimeGap(shiftWindow, otListOriginal, btListOriginal, gstwList)

        # Get the closest observation task before the gap window
        closestOTBeforeGap = None
        for ot in sorted(otListOriginal, key=lambda x: x.start, reverse=True):
            if ot.end <= gapTW.start:
                closestOTBeforeGap = ot
                break

        if closestOTBeforeGap is None:
            shiftBackwardPossible = False

        # Get the closest observation task after the gap window
        closestOTAfterGap = None
        for ot in sorted(otListOriginal, key=lambda x: x.start):
            if ot.start >= gapTW.end:
                closestOTAfterGap = ot
                break

        if closestOTAfterGap is None:
            shiftForwardPossible = False

        # Get the closest GSTW before the gap window
        closestGSTWBeforeGap = None
        for gstw in sorted(gstwToSortedTupleList(gstwList), key=lambda x: x[1].start, reverse=True):
            if gstw[1].end <= gapTW.start:
                closestGSTWBeforeGap = GSTW(gstw[0], [gstw[1]])
                break

        # A ground station time window cannot be shifted,
        # so if that is the first non-buffer task after the gap, we cannot shift in that direction
        if closestGSTWBeforeGap is not None and shiftBackwardPossible:
            if closestGSTWBeforeGap.TWs[0].end > closestOTBeforeGap.end:
                shiftBackwardPossible = False

        # Get the closest GSTW after the gap window
        closestGSTWAfterGap = None
        for gstw in sorted(gstwToSortedTupleList(gstwList), key=lambda x: x[1].start):
            if gstw[1].start >= gapTW.end:
                closestGSTWAfterGap = GSTW(gstw[0], [gstw[1]])
                break

        if closestGSTWAfterGap is not None and shiftForwardPossible:
            if closestGSTWAfterGap.TWs[0].start < closestOTAfterGap.start:
                shiftForwardPossible = False

        if not shiftForwardPossible and not shiftBackwardPossible:
            return None, otListOriginal, btListOriginal

        maxShift = 0
        if shiftBackwardPossible:
            maxShift += getMaxShift(closestOTBeforeGap, ttwList, False)
        if shiftForwardPossible:
            maxShift += getMaxShift(closestOTAfterGap, ttwList, True)

        # Make an estimate of the shift that is needed
        # The processing time after other tasks are included in the gap length, but not the processing time of the buffering itself
        shiftNeeded = p.bufferingTime + p.interTaskTime - gapLength

        # Check if increasing the gap width by shifting will make the buffer fit
        if shiftNeeded > maxShift:
            return None, otListOriginal, btListOriginal

        # First try to shift the lowest priority task in the corresponding direction, then the highest priority task
        # while taking into account if the shift is possible
        if shiftBackwardPossible and shiftForwardPossible:
            backwardShiftFirst = closestOTBeforeGap.GT.priority < closestOTAfterGap.GT.priority
        else:
            backwardShiftFirst = shiftBackwardPossible

        operations = [("backward", shiftBackwardPossible), ("forward", shiftForwardPossible)] if backwardShiftFirst \
            else [("forward", shiftForwardPossible), ("backward", shiftBackwardPossible)]

        for op, enabled in operations:
            if not enabled:
                continue
            if op == "backward":
                otToBufferShifted, otListModified, btListModified, backwardShift = self.backwardScheduleShift(
                    closestOTBeforeGap, otToBuffer, gapTW, otListModified, btListModified, dtList, gstwList, ttwList,
                    shiftNeeded, p.slidingInsertIterations
                )
                shiftNeeded -= backwardShift
            else:
                otListModified, btListModified, forwardShift = self.forwardScheduleShift(
                    closestOTAfterGap, otListModified, btListModified, dtList, gstwList, ttwList, shiftNeeded,
                    p.slidingInsertIterations
                )
                shiftNeeded -= forwardShift

        # If we still need to shift, then the shifting was not successful
        if shiftNeeded > 0:
            return None, otListOriginal, btListOriginal

        # After the shifting has been successful, try to insert the buffering task directly
        bt, _, _ = self.direct_insert.generateBuffer(otToBufferShifted, gstwToDownlink, otListModified, btListModified,
                                                     dtList, gstwList)
        if bt is not None:
            taskID = otListOriginal.index(otToBuffer) + 1
            print(f"Successfully inserted task {taskID} by shifting observation tasks")
            return bt, otListModified, btListModified
        else:
            return None, otListOriginal, btListOriginal

    def backwardScheduleShift(self, otToShift: OT, otToBuffer: OT, gapTW: TW, otList: list[OT], btList: list[BT],
                              dtList: list[DT], gstwList: list[GSTW], ttwList: list[TTW], shiftAmount: float = float('Infinity'),
                              iterations: int = 1):
        """
        Try to shift an observation task and the bufferings right after it to an earlier time.
        The observation task that we are trying to shift should happen before the gap in the schedule occurs,
        that's why we try to shift it to an earlier time.

        Args:
            otToShift (OT): The observation task to shift.
            otToBuffer (OT): The observation task for which the buffering is being scheduled.
            gapTW (TW): The time window representing the gap in the schedule to create space for the buffering.
            otList (list[OT]): List of all observation tasks
            btList (list[BT]): List of all already scheduled buffering tasks.
            dtList (list[DT]): List of all already scheduled downlinking tasks plus the candidate downlink tasks.
            gstwList (list[GSTW]): List of all ground station time windows.
            ttwList (list[TTW]): List of target time windows.
            shiftAmount (float, optional): The absolute amount of time in seconds to shift the task. The task will never be shifted outside its target time window.
            iterations (int, optional): The number of iteration for trying to shift, the shift in each iteration is the total shift divided by the number of iterations.

        Returns:
            tuple[OT, list[OT], list[BT], float]: A tuple containing:

                - OT: The (possibly) shifted observation task for which the buffering should be scheduled.
                    This task is shifted if the otToShift and otToBuffer happen to be the same task.
                - list[OT]: Modified list of observation tasks, with any shifted tasks updated.
                - list[BT]: Modified list of buffering tasks, with any shifted tasks updated.
                - float: The amount of seconds the task was shifted
        """
        # Start by trying to shift the full amount, if that fails, try smaller shifts
        otToBufferShifted = otToBuffer
        otListModified = otList.copy()
        btListModified = btList.copy()
        backwardShift = 0

        n = max(iterations, 1)
        for i in range(n):
            factor = 1 - i / n  # Fraction of the shift to try
            otToBufferShifted, otListModified, btListModified, backwardShift = self.backwardScheduleShiftPartial(
                otToShift, otToBuffer, gapTW, otList, btList, dtList, gstwList, ttwList, shiftAmount * factor
            )
            if backwardShift > 0:
                break

        return otToBufferShifted, otListModified, btListModified, backwardShift

    def backwardScheduleShiftPartial(self, otToShift: OT, otToBuffer: OT, gapTW: TW, otList: list[OT], btList: list[BT],
                                     dtList: list[DT], gstwList: list[GSTW], ttwList: list[TTW], shiftAmount: float = float('Infinity')):
        p = self.p

        # Shift the closest observation task before the gap backward to increase the gap width
        shiftedOTBeforeGap, backwardShift = shiftOT(otToShift, ttwList, False, shiftAmount)
        otListCandidate = otList.copy()
        otIndex = otListCandidate.index(otToShift)
        otListCandidate[otIndex] = shiftedOTBeforeGap

        # Shift all buffers before the gap backward
        btListCandidate = btList.copy()
        for i, bt in enumerate(btList):
            if otToShift.start <= bt.start <= gapTW.start:
                btListCandidate[i] = BT(bt.GT, bt.start - backwardShift, bt.end - backwardShift)

        # Check all buffers for conflict
        conflictingBuffer = False
        for bt in btListCandidate:
            if bufferTaskConflicting(bt, btListCandidate, otListCandidate, dtList, gstwList, p, False):
                conflictingBuffer = True
                break

        if not conflictingBuffer and not observationTaskConflicting(shiftedOTBeforeGap, btListCandidate,
                                                                    otListCandidate, gstwList, p):
            # The backward shift did not result in conflicts, so we can save the results
            otListModified = otListCandidate.copy()
            btListModified = btListCandidate.copy()
            otToBufferShifted = shiftedOTBeforeGap if shiftedOTBeforeGap.GT == otToBuffer.GT else otToBuffer

            return otToBufferShifted, otListModified, btListModified, backwardShift
        else:
            return otToBuffer, otList, btList, 0

    def forwardScheduleShift(self, otToShift: OT, otList: list[OT], btList: list[BT], dtList: list[DT],
                             gstwList: list[GSTW], ttwList: list[TTW], shiftAmount: float = float('Infinity'), iterations: int = 1):
        """
        Try to shift an observation task and the bufferings right after it to a later time.
        The observation task that we are trying to shift should happen after the gap in the schedule occurs,
        that's why we try to shift it to a later time.

        Args:
            otToShift (OT): The observation task to shift.
            otList (list[OT]): List of all observation tasks
            btList (list[BT]): List of all already scheduled buffering tasks.
            dtList (list[DT]): List of all already scheduled downlinking tasks plus the candidate downlink tasks.
            gstwList (list[GSTW]): List of all ground station time windows.
            ttwList (list[TTW]): List of target time windows.
            shiftAmount (float, optional): The absolute amount of time in seconds to shift the task. The task will never be shifted outside its target time window.
            iterations (int, optional): The number of iteration for trying to shift, the shift in each iteration is the total shift divided by the number of iterations.

        Returns:
            tuple[list[OT], list[BT]]: A tuple containing:

                - list[OT]: Modified list of observation tasks, with any shifted tasks updated.
                - list[BT]: Modified list of buffering tasks, with any shifted tasks updated.
                - float: The amount of seconds the task was shifted
        """
        otListModified = otList.copy()
        btListModified = btList.copy()
        forwardShift = 0

        # Start by trying to shift the full amount, if that fails, try smaller shifts
        n = max(iterations, 1)
        for i in range(n):
            factor = 1 - i / n  # Fraction of the shift to try
            otListModified, btListModified, forwardShift = self.forwardScheduleShiftPartial(
                otToShift, otList, btList, dtList, gstwList, ttwList, shiftAmount * factor
            )
            if forwardShift > 0:
                break

        return otListModified, btListModified, forwardShift

    def forwardScheduleShiftPartial(self, otToShift: OT, otList: list[OT], btList: list[BT], dtList: list[DT],
                                    gstwList: list[GSTW], ttwList: list[TTW], shiftAmount: float = float('Infinity')):
        p = self.p

        shiftedOTAfterGap, forwardShift = shiftOT(otToShift, ttwList, True, shiftAmount)
        otListCandidate = otList.copy()
        otIndex = otListCandidate.index(otToShift)
        otListCandidate[otIndex] = shiftedOTAfterGap

        # Now shift all the buffer tasks after the gap forward
        btListTimeSorted = sorted(btList, key=lambda x: x.start)
        btListCandidate = btList.copy()
        previousBT = btListTimeSorted[0] if len(btListTimeSorted) > 0 else None
        for i, bt in enumerate(btListTimeSorted):
            if bt.start > otToShift.end:
                if bt.start - otToShift.end == p.afterCaptureTime:
                    # This is the first buffer after the gap window
                    btListIndex = btListCandidate.index(bt)
                    btListCandidate[btListIndex] = BT(bt.GT, bt.start + forwardShift, bt.end + forwardShift)
                elif bt.start - previousBT.end == p.interTaskTime:
                    # This is one of the buffers in the stack of buffers after the gap
                    btListIndex = btListCandidate.index(bt)
                    btListCandidate[btListIndex] = BT(bt.GT, bt.start + forwardShift, bt.end + forwardShift)
                else:
                    # This is the first buffer after the gap that is not part of the chain of buffers after the capture, so we stop here
                    break

            previousBT = btListTimeSorted[i]

        # Check all buffers for conflict
        conflictingBuffer = False
        for bt in btListCandidate:
            if bufferTaskConflicting(bt, btListCandidate, otListCandidate, dtList, gstwList, p, False):
                conflictingBuffer = True
                break

        if not conflictingBuffer and not observationTaskConflicting(shiftedOTAfterGap, btListCandidate, otListCandidate,
                                                                    gstwList, p):
            # Forward shift has been successful, so we can save the results
            return otListCandidate, btListCandidate, forwardShift
        else:
            return otList, btList, 0


    def getLargestTimeGap(self, searchWindow: TW, otList: list[OT], btList: list[BT], gstwList: list[GSTW]):
        """
        Get the largest time gap between scheduled tasks.
        This will take into account the processing or waiting time that is needed after each specific task.
        The processing time of the task that needs to be inserted into the gap is not considered here.

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
        p = self.p

        twList = self.mergeToTimeWindowList(otList, btList, gstwList)

        if not twList:
            return 0

        # Add a dummy time window at the start and end of the observation horizon
        twList.insert(0, TW(0, 0))
        twList.append(TW(p.ohDuration, p.ohDuration))

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

    def mergeToTimeWindowList(self, otList: list[OT], btList: list[BT], gstwList: list[GSTW]):
        """
        Merge the observation tasks, buffering tasks and ground station time windows into a single list of time windows.
        The time windows in the list will include the processing and waiting times after each task.

        Args:
            otList (list[OT]): List of observation tasks.
            btList (list[BT]): List of buffering tasks.
            gstwList (list[GSTW]): List of ground station time windows.

        Returns:
            list[TW]: List of time windows
        """
        p = self.p

        twList: list[TW] = []
        for ot in otList:
            twList.append(TW(ot.start, ot.end + p.afterCaptureTime))
        for bt in btList:
            twList.append(TW(bt.start, bt.end + p.interTaskTime))
        for gstw in gstwList:
            for tw in gstw.TWs:
                twList.append(TW(tw.start, tw.end + p.interTaskTime))

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
        tuple[OT, float]: Tuple containing:

            - OT: The shifted observation task. If no valid shifting was possible, the original task will be returned.
            - float: The actual amount of time in seconds the task was shifted.
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

    if shiftForward:
        maxShift = otTW.end - ot.end
        actualShift = min(abs(shiftAmount), maxShift)
        newOT = OT(ot.GT, ot.start + actualShift, ot.end + actualShift)
    else:
        maxShift = ot.start - otTW.start
        actualShift = min(abs(shiftAmount), maxShift)
        newOT = OT(ot.GT, ot.start - actualShift, ot.end - actualShift)

    return newOT, actualShift


def getMaxShift(ot: OT, ttwList: list[TTW], shiftForward: bool = True):
    """
    Get the maximum amount of time an observation task can be shifted forward or backward in time.

    Args:
        ot (OT): The observation task to check.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.
        shiftForward (bool, optional): If True, the task will be shifted forward in time. If False, it will be shifted backward. Defaults to True.

    Returns:
        float: The maximum amount of time in seconds the task can be shifted.
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
        return 0

    if shiftForward:
        return otTW.end - ot.end
    else:
        return ot.start - otTW.start