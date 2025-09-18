import copy

from scheduling_model import OT, GSTW, GS, TW, TTW, BT, DT
from transmission_scheduling.conflict_checks import observationTaskConflicting
from transmission_scheduling.input_parameters import TransmissionParams


def generateNewOTList(possibleTTW: list[TTW], otListScheduled: list[OT], btListScheduled: list[BT],
                      gstwList: list[GSTW], p: TransmissionParams) -> list[OT]:
    """
    Based on a list of possible target time windows, generate a list of observation tasks that could be scheduled.

    Args:
        possibleTTW (list[TTW]): List of target time windows that could still be used to schedule the unscheduled observation tasks.
        otListScheduled (list[OT]): List of observation tasks that have been successfully scheduled.
        btListScheduled (list[BT]): List of buffering tasks that have been successfully scheduled.
        gstwList (list[GSTW]): List of ground station time windows.
        p (TransmissionParams): Parameters for the transmission scheduling.

    Returns:
        list[OT]: List of observation tasks that could be scheduled during re-insertion in the provided target time windows.
    """
    newOTList: list[OT] = []
    for ttw in possibleTTW:
        for tw in ttw.TWs:
            halfTime = (tw.start + tw.end) / 2
            # The new observation task will be centered, the insertion algorithms could always shift it if needed
            otCandidate = OT(ttw.GT, halfTime - p.captureDuration / 2, halfTime + p.captureDuration / 2)
            # Check for a conflic of this OT with the already scheduled tasks and the new ones
            fullOTList = otListScheduled + newOTList
            if not observationTaskConflicting(otCandidate, btListScheduled, fullOTList, gstwList, p):
                newOTList.append(otCandidate)
                break

    return newOTList


def findPossibleTTW(ttwListToUpdate: list[TTW], otListLastInsertionAttempt: list[OT], scheduledOTList: list[OT]) \
        -> list[TTW]:
    """
    Find a list of target time windows that could still be used to schedule the unscheduled observation tasks

    Args:
        ttwListToUpdate (list[TTW]): List of target time windows to select the possible TTWs from.
        otListLastInsertionAttempt (list[OT]): List of observation tasks that where lastly attempted to be scheduled.
        scheduledOTList (list[OT]): List of observation tasks that have been successfully scheduled.

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


def getClosestGSTW(ot: OT, gstwList: list[GSTW], maxLatency=36000):
    """
    Get the closest ground station time windows to the observation task.

    Args:
        ot (OT): The observation task to find the closest ground station time windows for.
        gstwList (list[GSTW]): List of all ground station time windows.
        maxLatency (float): Maximum duration between the capture and its downlink in seconds

    Return:
        list[GSTW]: List of the closest ground station time windows.
    """
    # First put the gstwList into a single list of time windows with reference to their ground station
    # This is not the right output structure, but it is easier to sort and select from

    allGSTWsSorted = gstwToSortedTupleList(gstwList)

    # Remove entries before the observation tasks ended
    allGSTWsSorted = [entry for entry in allGSTWsSorted if ot.end <= entry[1].start <= ot.end + maxLatency]

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

def bufferFileCounter(btList: list[BT], dtList: list[DT]):
    """
    Count the number of captures that is present in the buffer of the satellite at any given time.
    Hypso-2 has a maximum of 7 captures that can be stored in the buffer at any given time.
    """
    # First sort the dtList by time and remove duplicate GT, but only keep the latest entry
    # The latest entry of a ground target in the dtList is the one where the data has been fully transmitted
    dtListSorted = sorted(dtList, key=lambda x: x.start, reverse=True)
    dtListUnique: list[DT] = []
    seenGTs = set()
    for dt in dtListSorted:
        if dt.GT not in seenGTs:
            dtListUnique.append(dt)
            seenGTs.add(dt.GT)
    events = []
    for dt in dtListUnique:
        events.append((dt.start, -1))
    for bt in btList:
        events.append((bt.start, 1))

    events = sorted(events, key=lambda x: x[0])
    fileCount = 0
    fileCountList = []
    for event in events:
        fileCount += event[1]
        fileCountList.append(fileCount)

    print(f"Maximum number of files in buffer: {max(fileCountList)}")

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

    print(f"Maximum latency: {max(latencyList):.2f} seconds")
    print(f"Average latency: {sum(latencyList)/len(latencyList):.2f} seconds")

def plotSchedule(otListMod: list[OT], otList: list[OT], btList: list[BT], dtList: list[DT], gstwList: list[GSTW],
                 ttwList: list[TTW], p: TransmissionParams):
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
    plt.xlim(0, p.ohDuration)
    plt.legend()
    plt.tight_layout()
    plt.show()
