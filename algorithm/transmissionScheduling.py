import copy
import datetime

import data_postprocessing.algorithmData_api as AD_api
from data_preprocessing.get_target_passes import getGroundStationTimeWindows
from scheduling_model import OT, TTW, BT, GSTW, TW, GS, DT
import time

bufferingTime = 1500  # seconds
maxBufferOffset = 12 * 3600  # Maximum offset between a capture and its buffering in seconds
interTaskTime = 100  # seconds between two tasks to account for transition time
downlinkDuration = 100  # seconds to downlink a capture
groundStationFilePath = "data_input/HYPSO_data/ground_stations.csv"
ohDuration = 48 * 3600  # Duration of the observation horizon in seconds
maxGSTWAhead = 4  # Maximum number of ground station time windows ahead of the capture to consider when scheduling a buffering task
hypsoNr = 2  # HYPSO satellite number


def scheduleTransmissions(otList: list[OT], ttwList: list[TTW], gstwListSorted: list[GSTW]):
    """
    Try to schedule the transmission of each observed target in otList.
    Transmission consists of transmitting to Ground Station and buffering the capture before actually transmitting.

    Args:
        otList (list[OT]): List of observation tasks to schedule transmissions for.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.
        gstwListSorted (list[GSTW]): List of ground station time windows with time windows corresponding to each GS sorted by time.

    Returns:
        tuple[bool, list[BT], list[DT], list[OT]]: A tuple containing:

            - A boolean indicating if a transmission schedule has been found for all observation tasks.
                If false, there can still be a useful output containing a schedule for the tasks that were able to fit.
            - A list of scheduled buffering tasks (BT).
            - A list of scheduled downlink tasks (DT).
            - A list of observation tasks, possibly changed to fit the buffering and downlinking tasks.
    """
    btList: list[BT] = []
    dtList: list[DT] = []

    otListMod = copy.copy(otList)
    otListSorted = sorted(otList, key=lambda x: x.start)
    completeScheduleFound = True

    for otToBuffer in otList:
        # For each observation task to buffer, try to buffer it considering the downlink in one of the closest ground station time windows
        validBTFound = False
        closestGSTW = getClosestGSTW(otToBuffer, gstwListSorted, maxGSTWAhead)
        closestGSTWSorted = gstwToSortedTupleList(closestGSTW)

        for entry in closestGSTWSorted:
            gstw = GSTW(entry[0], [entry[1]])
            candidateDT = generateDownlinkTask(gstw, dtList, otToBuffer)

            if candidateDT is None:
                # No valid downlink task could be scheduled in this ground station time window
                continue

            bt = generateBufferTaskDirectInsert(otToBuffer, gstw, otListSorted, btList, gstwListSorted)
            if bt is not None:
                btList.append(bt)
                dtList.append(candidateDT)
                validBTFound = True
                # We found a buffer task and corresponding GSTW to downlink, so we don't need to consider other GSTW
                break

        if not validBTFound:
            # No valid GSTW has been found to downlink the buffered data
            completeScheduleFound = False
            print(
                f"Could not schedule buffering task for capture of {otToBuffer.GT.id} at {otToBuffer.start}")
            otListMod.remove(otToBuffer)

    return completeScheduleFound, btList, dtList, otListMod


def generateDownlinkTask(gstw: GSTW, dtList: list[DT], otToDownlink: OT):
    """
    Try to schedule a downlink task in the given ground station time window for the given observation task.

    Args:
        gstw (GSTW): The ground station time window to schedule the downlink task in.
        dtList (list[DT]): List of all already scheduled downlink tasks.
        otToDownlink (OT): The observation task to schedule the downlink for.

    Returns:
        DT: The scheduled downlink task, or None if no valid scheduling was found.
    """

    # First try to insert the downlink task at the start of the ground station time window
    dtStart = gstw.TWs[0].start
    dtEnd = dtStart + downlinkDuration
    candidateDT = DT(otToDownlink.GT, gstw.GS, dtStart, dtEnd)
    if dtEnd <= gstw.TWs[0].end:
        if not downlinkTaskConflicting(candidateDT, dtList):
            return candidateDT

    # Now try to start the downlink task at the end of other downlink tasks
    for otherDT in dtList:
        dtStart = otherDT.end + interTaskTime
        dtEnd = dtStart + downlinkDuration
        candidateDT = DT(otToDownlink.GT, gstw.GS, dtStart, dtEnd)
        if dtStart >= gstw.TWs[0].start and dtEnd <= gstw.TWs[0].end:
            if not downlinkTaskConflicting(candidateDT, dtList):
                return candidateDT

    return None


def generateBufferTaskDirectInsert(otToBuffer: OT, gstwToDownlink: GSTW, otListSorted: list[OT], btList: list[BT],
                                   gstwListSorted: list[GSTW]):
    """
    Try to insert the buffering of an observed target directly into the schedule.
    Insertion is tried at the end of other tasks, so all tasks neatly follow each other.
    If no valid insertion is found, return None.

    Args:
        otToBuffer (OT): The observation task to schedule buffering for.
        gstwToDownlink (GSTW): The ground station time window to use for downlinking the buffered data.
        otListSorted (list[OT]): List of all observation tasks, sorted by start time
        btList (list[BT]): List of all already scheduled buffering tasks.
        dtList (list[DT]): List of all already scheduled downlink tasks.
        gstwListSorted (list[GSTW]): List of all ground station time windows, sorted by start time.
    """

    # Candidate buffer task start and end
    btStart = otToBuffer.end + interTaskTime
    btEnd = btStart + bufferingTime
    candidateBT = BT(otToBuffer.GT, btStart, btEnd)

    # First guess is to immediately start buffering after observation
    if not bufferTaskConflicting(candidateBT, btList, otListSorted, gstwListSorted) \
            and btEnd < gstwToDownlink.TWs[0].start:
        return candidateBT

    # From now on, we will save all the possible candidates and later pick the earliest option
    candidateBTList: list[BT] = []

    # Now try to insert the buffer task at the end of other observation tasks
    for ot in otListSorted:
        # Candidate buffer task start and end
        btStart = ot.end + interTaskTime
        btEnd = btStart + bufferingTime

        if btStart - otToBuffer.end > maxBufferOffset or btEnd > gstwToDownlink.TWs[0].start:
            # Inserting the buffer tasks after this point would be too far from the observation task
            # or be after the intended downlink window has started.
            # Observation tasks are sorted by time, so looking further is not necessary
            break
        if ot.end < otToBuffer.end:
            # Skip if the candidate buffer task would be scheduled before its target observation
            continue

        candidateBT = BT(otToBuffer.GT, btStart, btEnd)
        if not bufferTaskConflicting(candidateBT, btList, otListSorted, gstwListSorted):
            candidateBTList.append(candidateBT)
            # Observation tasks are sorted by time, so looking further is not necessary
            break

    # Now try to insert the buffer task at the end of other buffer tasks
    for bt in btList:
        # Candidate buffer task start and end
        btStart = bt.end + interTaskTime
        btEnd = btStart + bufferingTime
        if btStart - otToBuffer.end > maxBufferOffset or btStart < otToBuffer.end \
                or btEnd > gstwToDownlink.TWs[0].start:
            continue

        candidateBT = BT(otToBuffer.GT, btStart, btEnd)
        if not bufferTaskConflicting(candidateBT, btList, otListSorted, gstwListSorted):
            candidateBTList.append(candidateBT)

    # Last attempt is to insert after a ground station time window
    for gstw in gstwListSorted:
        for tw in gstw.TWs:
            # Candidate buffer task start and end
            btStart = tw.end + interTaskTime
            btEnd = btStart + bufferingTime
            if btStart - otToBuffer.end > maxBufferOffset or btEnd > gstwToDownlink.TWs[0].start:
                # Inserting the buffer tasks after this point would be too far from the observation task
                # or be after the intended downlink window has started.
                # Observation tasks are sorted by time, so looking further is not necessary
                break
            if btStart < otToBuffer.end:
                continue

            candidateBT = BT(otToBuffer.GT, btStart, btEnd)
            if not bufferTaskConflicting(candidateBT, btList, otListSorted, gstwListSorted):
                candidateBTList.append(candidateBT)
                # Time windows are sorted by time, so looking further is not necessary
                break

    # Search the earliest candidate in the list
    if candidateBTList:
        earliestBT = min(candidateBTList, key=lambda x: x.start)
        return earliestBT

    # No valid insertions have been found, return None
    return None


def bufferTaskConflicting(bt: BT, btList: list[BT], otListSorted: list[OT], gstwListSorted: list[GSTW]):
    """
    Check if the buffering task overlaps with any other scheduled tasks.

    Args:
        bt (BT): The buffering task to validate.
        btList (list[BT]): List of all already scheduled buffering tasks.
        otListSorted (list[OT]): List of all observation tasks, sorted by start time.
        gstwListSorted (list[GSTW]): List of all ground station time windows, sorted by start time.
    """
    for ot in otListSorted:
        if ot.start > bt.end:
            # All following observation tasks will also start after the buffering task has already ended
            break
        if ot.end < bt.start:
            continue
        else:
            return True
    for otherBT in btList:
        if otherBT.GT == bt.GT:
            # The task we are comparing is the same buffering task
            continue
        if otherBT.end < bt.start or otherBT.start > bt.end:
            continue
        else:
            return True
    for gstw in gstwListSorted:
        for tw in gstw.TWs:
            if tw.start > bt.end:
                # All following time windows will also start after the buffering task has already ended
                break
            if tw.end < bt.start:
                continue
            else:
                return True

    return False


def downlinkTaskConflicting(dt: DT, dtList: list[DT]):
    """
    Check if the downlink task overlaps with any other scheduled downlink tasks.

    Args:
        dt (DT): The downlink task to validate.
        dtList (list[DT]): List of all already scheduled downlink tasks.
    """
    for otherDT in dtList:
        if otherDT.GT == dt.GT and otherDT.GS == dt.GS:
            # The task we are comparing is the same downlink task
            continue
        if otherDT.end < dt.start or otherDT.start > dt.end:
            continue
        else:
            return True

    return False


def getClosestGSTW(ot: OT, gstwListSorted: list[GSTW], numberOfClosest=1):
    """
    Get the closest ground station time windows to the observation task.

    Args:
        ot (OT): The observation task to find the closest ground station time windows for.
        gstwListSorted (list[GSTW]): List of all ground station time windows, sorted by start time.
        numberOfClosest (int, optional): Number of closest ground station time windows to return. Defaults to 1.
                If there are less than this number of time windows available, all available time windows will be returned.

    Return:
        list[GSTW]: List of the closest ground station time windows.
    """
    # First put the gstwList into a single list of time windows with reference to their ground station
    # This is not the right output structure, but it is easier to sort and select from

    allGSTWsSorted = gstwToSortedTupleList(gstwListSorted)

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


def plotSchedule(otList: list[OT], btList: list[BT], dtList: list[DT], gstwList: list[GSTW]):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(30, 5))

    # Observation Tasks (blue)
    for i, ot in enumerate(otList, start=1):
        ax.barh(
            y=0,
            width=ot.end - ot.start,
            left=ot.start,
            height=0.5,
            color="royalblue",
            alpha=1,
            label="OT" if i == 1 else ""
        )
        # Label under the box
        ax.text(
            x=ot.start + (ot.end - ot.start) / 2,
            y=-0.1 - (i % 3) * 0.04,  # below y=0 row
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
            y=1.75 - (i % 10) * 0.05,  # below y=1.5 row
            s=str(i),
            ha="center",
            va="top",
            fontsize=10,
            color="black"
        )

    # Formatting
    plt.xlim(0, ohDuration)
    plt.xlabel("Time [s]")
    plt.legend()
    plt.tight_layout()
    plt.show()


otList = AD_api.getScheduleFromFile("BS_test12-run1.json")

startTimeOH = datetime.datetime(2025, 8, 27, 15, 29, 0)
startTimeOH = startTimeOH.replace(tzinfo=datetime.timezone.utc)
endTimeOH = startTimeOH + datetime.timedelta(seconds=ohDuration)

gstwList = getGroundStationTimeWindows(startTimeOH, endTimeOH, groundStationFilePath, hypsoNr)

start_time = time.perf_counter()
valid, btList, dtList, otListModified = scheduleTransmissions(otList, [], gstwList)
end_time = time.perf_counter()

print(f"{(end_time - start_time) * 1000:.4f} milliseconds")

plotSchedule(otListModified, btList, dtList, gstwList)
