from scheduling_model import OT, GSTW, GS, TW, TTW, BT, DT
from transmission_scheduling.input_parameters import TransmissionParams


def getClosestGSTW(ot: OT, gstwList: list[GSTW], numberOfClosest=1):
    """
    Get the closest ground station time windows to the observation task.

    Args:
        ot (OT): The observation task to find the closest ground station time windows for.
        gstwList (list[GSTW]): List of all ground station time windows.
        numberOfClosest (int, optional): Number of closest ground station time windows to return. Defaults to 1.
                If there are less than this number of time windows available, all available time windows will be returned.

    Return:
        list[GSTW]: List of the closest ground station time windows.
    """
    # First put the gstwList into a single list of time windows with reference to their ground station
    # This is not the right output structure, but it is easier to sort and select from

    allGSTWsSorted = gstwToSortedTupleList(gstwList)

    # Remove entries before the observation tasks ended
    allGSTWsSorted = [entry for entry in allGSTWsSorted if entry[1].start >= ot.end]

    if not allGSTWsSorted:
        return []
    if len(allGSTWsSorted) < numberOfClosest:
        numberOfClosest = len(allGSTWsSorted)

    allGSTWsSorted = allGSTWsSorted[:numberOfClosest]

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
