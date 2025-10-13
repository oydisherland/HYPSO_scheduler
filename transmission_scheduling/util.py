import copy

from scheduling_model import OT, GSTW, GS, TW, TTW, BT, DT
from transmission_scheduling.input_parameters import TransmissionParams
import matplotlib.pyplot as plt


def findPossibleTTW(ttwListToUpdate: list[TTW], otListLastInsertionAttempt: list[OT], scheduledOTList: list[OT],
                    fullReinsert: bool = False) -> list[TTW]:
    """
    Find a list of target time windows that could still be used to schedule the unscheduled observation tasks

    Args:
        ttwListToUpdate (list[TTW]): List of target time windows to select the possible TTWs from.
        otListLastInsertionAttempt (list[OT]): List of observation tasks that where lastly attempted to be scheduled.
        scheduledOTList (list[OT]): List of observation tasks that have been successfully scheduled.
        fullReinsert (bool): Whether to try to reinsert observation tasks which were not included in last insertion attempt.

    Returns:
        list[TTW]: List of target time windows that could still be used to schedule the unscheduled observation tasks.
    """
    # Find the observation tasks that could not be scheduled
    otListUnscheduled = otListLastInsertionAttempt.copy()
    ttwListUnscheduled = copy.deepcopy(ttwListToUpdate)
    for otScheduled in scheduledOTList:
        for ttw in ttwListToUpdate:
            if ttw.GT == otScheduled.GT:
                ttwListUnscheduled.remove(ttw)
                break
        for ot in otListLastInsertionAttempt:
            if ot.GT == otScheduled.GT:
                otListUnscheduled.remove(ot)
                break

    if not fullReinsert:
        # We only want to find TTWs for targets that failed to be scheduled by the transmission scheduler
        # However, the ttwList might contain time windows for targets that were not in the imaging schedule
        # that was passed to the transmission scheduler in the first place.
        ttwListUnscheduled = [ttw for ttw in ttwListUnscheduled if any(ot.GT == ttw.GT for ot in otListUnscheduled)]

    # Remove the time windows that we have already tried to schedule
    for ttw in ttwListUnscheduled:
        for otUnscheduled in otListUnscheduled:
            if ttw.GT == otUnscheduled.GT:
                for tw in ttw.TWs:
                    if otUnscheduled.start >= tw.start and otUnscheduled.end <= tw.end:
                        ttw.TWs.remove(tw)
                        break
                break

    return ttwListUnscheduled


def getClosestGSTW(taskEndTime: float, gstwList: list[GSTW], maxLatency=float("Infinity")) -> list[GSTW]:
    """
    Get the closest ground station time windows to the observation task.

    Args:
        taskEndTime (float): End time of the observation task in seconds.
        gstwList (list[GSTW]): List of all ground station time windows.
        maxLatency (float): Maximum duration between the capture and its downlink in seconds

    Return:
        list[GSTW]: List of the closest ground station time windows.
    """
    # First put the gstwList into a single list of time windows with reference to their ground station
    # This is not the right output structure, but it is easier to sort and select from

    allGSTWsSorted = gstwToSortedTupleList(gstwList)

    # Remove entries before the observation tasks ended
    allGSTWsSorted = [entry for entry in allGSTWsSorted if taskEndTime <= entry[1].start <= taskEndTime + maxLatency]

    if not allGSTWsSorted:
        return []

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


def gstwToSortedTupleList(gstwList: list[GSTW]) -> list[tuple[GS, TW]]:
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


def latencyCounter(otList: list[OT], dtList: list[DT]):
    """
    Check the latency between each capture and their downlink
    """
    dtListSorted = sorted(dtList, key=lambda x: x.start, reverse=True)
    dtListUnique: list[DT] = []
    seenGTs = set()
    for dt in dtListSorted:
        if dt.GT not in seenGTs:
            dtListUnique.append(dt)
            seenGTs.add(dt.GT)

    latencyList = []
    for ot in otList:
        for dt in dtListUnique:
            if ot.GT == dt.GT:
                latency = dt.start - ot.end
                latencyList.append(latency)
                break
    if latencyList:
        print(f"Maximum latency: {max(latencyList) / 3600:.2f} hours")
        print(f"Average latency: {sum(latencyList) / (len(latencyList) * 3600):.2f} hours")


def getFreeGSGaps(btList: list[BT], gstwListSorted: list[tuple[GS, TW]]) -> list[TW]:
    """
    Find the gaps between ground station passes where no buffering is scheduled.

    Args:
        btList (list[BT]): List of all buffering tasks.
        gstwListSorted (list[tuple[GS, TW]): List of all ground station time windows.

    Returns:
        list[TW]: List with the time windows of the gap (from start of first GS pass to end of next GS pass).
    """
    freeGapList = []  # List with the end time of the free gaps
    for i in range(len(gstwListSorted) - 1):
        gstw = gstwListSorted[i]
        nextGstw = gstwListSorted[i + 1]
        gapStart = gstw[1].start
        gapEnd = nextGstw[1].end
        freeGapFound = True
        for bt in btList:
            if not (bt.end <= gapStart or bt.start >= gapEnd):
                # There is a buffering task in this gap
                freeGapFound = False
                break
        if freeGapFound:
            freeGapList.append(TW(gapStart, gapEnd))

    return freeGapList

def getBufferClearedTimestamps(btList: list[BT], dtList: list[DT], gstwSortedTupleList: list[tuple[GS,TW]]) \
        -> list[float]:
    """
    Find the timestamps when the buffer is cleared.
    This happens when there are one or two buffer files left which get two full ground station passes to downlink.
    """
    freeGSGapList = getFreeGSGaps(btList, gstwSortedTupleList)
    # Store the last part of all the downlink tasks
    dtDictUnique: dict = {}
    for dt in dtList:
        existing = dtDictUnique.get(dt.GT)
        if existing is None or dt.start > existing.start:
            dtDictUnique[dt.GT] = dt

    # Now that we have found the GS passes with no buffering tasks in between them,
    # verify that the buffer is empty enough before the first of these two passes
    bufferClearedTimestamps = []  # List of timestamps when the buffer is cleared
    for freeGSGap in freeGSGapList:
        preGapFileCount = 0
        for dt in dtDictUnique.values():
            if dt.end < freeGSGap.start:
                preGapFileCount -= 1
        for bt in btList:
            if bt.end < freeGSGap.start:
                preGapFileCount += 1

        if preGapFileCount <= 2:
            bufferClearedTimestamps.append(freeGSGap.end)

    bufferClearedTimestamps.insert(0, 0)

    return bufferClearedTimestamps

def plotSchedule(otListMod: list[OT], otList: list[OT], btList: list[BT], dtList: list[DT], gstwList: list[GSTW],
                 ttwList: list[TTW], p: TransmissionParams):
    otListPrio = sorted(otList, key=lambda x: x.GT.priority, reverse=True)
    otListModPrio = sorted(otListMod, key=lambda x: x.GT.priority, reverse=True)
    btListPrio = sorted(btList, key=lambda x: x.GT.priority, reverse=True)
    dtListPrio = sorted(dtList, key=lambda x: x.GT.priority, reverse=True)

    # Also some printing of metrics
    print(" ")
    print(f"Number of scheduled observation tasks: {len(otListModPrio)}")
    latencyCounter(otListModPrio, dtListPrio)

    fig, ax = plt.subplots(figsize=(30, 5))

    # Observation Tasks (blue)
    for i, ot in enumerate(otListModPrio, start=1):
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

    for i, ot in enumerate(otListPrio, start=1):
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
    for i, bt in enumerate(btListPrio, start=1):
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
            y= 0.62 - (i % 5) * 0.02,  # below y=0.5 row
            s=str(i),
            ha="center",
            va="top",
            fontsize=10,
            color="black"
        )
        ax.text(
            x=bt.start + (bt.end - bt.start) / 2,
            y=0.25,  # below y=0.5 row
            s=bt.fileID,
            ha="center",
            va="top",
            fontsize=10,
            color="grey"
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
    for i, dt in enumerate(dtListPrio, start=1):
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
    plt.xlim(0, p.ohDuration)
    plt.legend()
    plt.tight_layout()
    plt.show()
