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
    # Find the observation tasks of the ground targets that could not be scheduled
    otListUnscheduled = [ot for ot in otListLastInsertionAttempt if not any(ot.GT == otScheduled.GT for otScheduled in scheduledOTList)]

    if not fullReinsert:
        # We only want to find TTWs for targets that failed to be scheduled by the transmission scheduler
        # However, the ttwList might contain time windows for targets that were not in the imaging schedule
        # that was passed to the transmission scheduler in the first place.
        ttwListUnscheduled = [TTW(ttw.GT, ttw.TWs.copy()) for ttw in ttwListToUpdate if any(ot.GT == ttw.GT for ot in otListUnscheduled)]
    else:
        ttwListUnscheduled = copy.deepcopy(ttwListToUpdate)
        for otScheduled in scheduledOTList:
            for ttw in ttwListToUpdate:
                if ttw.GT == otScheduled.GT:
                    ttwListUnscheduled.remove(ttw)
                    break

    # Remove the time windows that we have already tried to schedule
    for ttw in ttwListUnscheduled:
        for otUnscheduled in otListUnscheduled:
            if ttw.GT == otUnscheduled.GT:
                for tw in ttw.TWs:
                    if otUnscheduled.start >= tw.start and otUnscheduled.end <= tw.end:
                        ttw.TWs.remove(tw)
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
    seenTaskIDs = set()
    for dt in dtListSorted:
        if dt.OTTaskID not in seenTaskIDs:
            dtListUnique.append(dt)
            seenTaskIDs.add(dt.OTTaskID)

    latencyList = []
    for ot in otList:
        for dt in dtListUnique:
            if ot.taskID == dt.OTTaskID:
                latency = dt.start - ot.end
                latencyList.append(latency)
                break
    if latencyList:
        print(f"Maximum latency: {max(latencyList) / 3600:.2f} hours")
        print(f"Average latency: {sum(latencyList) / (len(latencyList) * 3600):.2f} hours")


def getFreeGSGaps(btList: list[BT], gstwListSorted: list[tuple[GS, TW]]) -> list[tuple[TW, TW]]:
    """
    Find the gaps between ground station passes where no buffering is scheduled.

    Args:
        btList (list[BT]): List of all scheduled buffering tasks.
        gstwListSorted (list[tuple[GS, TW]): List of all ground station time windows.

    Returns:
        list[tuple[TW, TW]]: List with the time windows from the ground station pass before and after the gaps
    """
    freeGapList = []  # List with the end time of the free gaps
    btListToCheck = btList.copy()
    for i in range(len(gstwListSorted) - 1):
        gstw = gstwListSorted[i]
        nextGstw = gstwListSorted[i + 1]
        gapStart = gstw[1].start
        gapEnd = nextGstw[1].end
        freeGapFound = True
        for bt in btListToCheck:
            if not (bt.end <= gapStart or bt.start >= gapEnd):
                # There is a buffering task in this gap
                freeGapFound = False
                # Remove the buffer task from the list to check, because it is not relevant for other gaps
                btListToCheck.remove(bt)
                break
        if freeGapFound:
            freeGapList.append((gstw[1], nextGstw[1]))

    return freeGapList

def getBufferClearedTimestamps(otList: list[OT], btList: list[BT], dtList: list[DT],
                               gstwSortedTupleList: list[tuple[GS,TW]], p: TransmissionParams) -> list[float]:
    """
    Find the timestamps when the buffer is cleared.
    This happens when there are one or two buffer files left which get two full ground station passes to downlink.
    """
    freeGSGapList = getFreeGSGaps(btList, gstwSortedTupleList)
    # Store the last part of all the downlink tasks
    dtDictUnique: dict = {}
    for dt in dtList:
        existing = dtDictUnique.get(dt.OTTaskID)
        if existing is None or dt.start > existing.start:
            dtDictUnique[dt.OTTaskID] = dt

    # Now that we have found the GS passes with no buffering tasks in between them,
    # verify that the buffer is empty enough before the first of these two passes
    bufferClearedTimestamps = []  # List of timestamps when the buffer is cleared
    for freeGSGap in freeGSGapList:
        preGapFileCount = 0
        for dt in dtDictUnique.values():
            if dt.end < freeGSGap[0].start:
                preGapFileCount -= 1
        for bt in btList:
            if bt.start < freeGSGap[0].start:
                preGapFileCount += 1

        if preGapFileCount == 0:
            bufferClearedTimestamps.append(freeGSGap[0].start)
            continue

        if preGapFileCount <= 2:
            # Check if there is enough available time in the GS passes right before and after the gap to clear the buffer
            availableTime = getAvailableDownlinkTime(freeGSGap[0], [], otList, p) + \
                                getAvailableDownlinkTime(freeGSGap[1], [], otList, p)
            if availableTime > preGapFileCount * 1.5 * p.downlinkDuration:
                bufferClearedTimestamps.append(freeGSGap[1].end)

    bufferClearedTimestamps.insert(0, 0)

    return bufferClearedTimestamps

def getAvailableDownlinkTime(tw: TW, dtList: list[DT], otList: list[OT], p: TransmissionParams) -> float:
    """
    Get the available time during the provided ground station pass (represented as a time window) for downlinking captures.
    This takes into account that there is less time available then the full pass
    due to downlinking telemetry and when observation tasks are scheduled during the pass.

    Args:
        tw (TW): Time window of the ground station pass to check.
        dtList (list[DT]): List of all already scheduled downlink tasks.
        otList (list[OT]): List of all scheduled observation tasks.
        p (TransmissionParams): Input parameters containing timing configurations.

    Returns:
        float: The available time in seconds during the ground station pass for downlinking captures.
            Can be negative if there is a scheduling conflict.
    """

    otDuringGS = [ot for ot in otList if not (ot.end <= tw.start or ot.start >= tw.end)]
    dtDuringGS = [dt for dt in dtList if not (dt.end <= tw.start or dt.start >= tw.end)]
    availableTime = tw.end - tw.start
    # Subtract time for telemetry downlinking
    availableTime -= p.transmissionStartTime
    # Subtract time for observation tasks during the GS pass
    availableTime -= p.overLappingWithCaptureSetback * len(otDuringGS)

    # Subtract time for already scheduled downlink tasks
    for dt in dtDuringGS:
        availableTime -= dt.end - dt.start

    return availableTime

def plotSchedule(otList: list[OT], btList: list[BT], dtList: list[DT], gstwList: list[GSTW],
                 ttwList: list[TTW], p: TransmissionParams, savePlotPath=None):
    otListPrio = sorted(otList, key=lambda x: x.GT.priority, reverse=True)
    taskIDPrio = [ot.taskID for ot in otListPrio]
    taskIDPrio.insert(0, -1)  # So that taskID 0 is at index 1

    # Also some printing of metrics
    print(" ")
    print(f"Number of scheduled observation tasks: {len(otListPrio)}")
    latencyCounter(otListPrio, dtList)

    fig, ax = plt.subplots(figsize=(30, 5))

    # Observation Tasks (blue)
    for i, ot in enumerate(otListPrio, start=1):
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
            s= str(taskIDPrio.index(ot.taskID)),
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
            y= 0.62 - (i % 5) * 0.02,  # below y=0.5 row
            s=str(taskIDPrio.index(bt.OTTaskID)),
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
    for i, dt in enumerate(dtList, start=1):
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
            s=str(taskIDPrio.index(dt.OTTaskID)),
            ha="center",
            va="top",
            fontsize=10,
            color="black"
        )

    # Formatting
    plt.xlim(0, p.ohDuration)
    plt.legend()
    plt.tight_layout()
    if savePlotPath is not None:
        plt.savefig(f"{savePlotPath}.png")
        plt.close()  # Close the figure to free memory
    else:
        plt.show()


def plotCompareSchedule(otListCp: list[OT], otList: list[OT], btList: list[BT], dtList: list[DT], gstwList: list[GSTW],
                 ttwList: list[TTW], p: TransmissionParams, savePlotPath=None):

    otListPrio = sorted(otList, key=lambda x: x.GT.priority, reverse=True)
    otListCPPrio = sorted(otListCp, key=lambda x: x.GT.priority, reverse=True)
    taskIDPrio = [ot.taskID for ot in otListPrio]
    taskIDPrio.insert(0, -1)  # So that taskID 0 is at index 1

    # Also some printing of metrics
    print(" ")
    print(f"Number of scheduled observation tasks: {len(otListPrio)}")
    latencyCounter(otListPrio, dtList)

    fig, ax = plt.subplots(figsize=(30, 5))

    # Observation Tasks (blue)
    for i, ot in enumerate(otListPrio, start=1):
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
            s=str(taskIDPrio.index(ot.taskID)),
            ha="center",
            va="top",
            fontsize=10,
            color="black"
        )

    # Observation Tasks Campaign Planner (orange)
    for i, ot in enumerate(otListCPPrio, start=1):
        ax.barh(
            y=-0.8,
            width=ot.end - ot.start,
            left=ot.start,
            height=0.3,
            color="magenta",
            alpha=1,
            label="OT campaign planner" if i == 1 else ""
        )
        # Label under the box
        ax.text(
            x=ot.start + (ot.end - ot.start) / 2,
            y=-0.8 - (i % 3) * 0.04,  # below y=0 row
            s=str(i),
            ha="center",
            va="top",
            fontsize=10,
            color="grey"
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
            y= 0.62 - (i % 5) * 0.02,  # below y=0.5 row
            s=str(taskIDPrio.index(bt.OTTaskID)),
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
    for i, dt in enumerate(dtList, start=1):
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
            s=str(taskIDPrio.index(dt.OTTaskID)),
            ha="center",
            va="top",
            fontsize=10,
            color="black"
        )

    # Formatting
    plt.xlim(0, p.ohDuration)
    plt.legend()
    plt.tight_layout()
    if savePlotPath is not None:
        plt.savefig(f"{savePlotPath}.png")
        plt.close()  # Close the figure to free memory
    else:
        plt.show()
