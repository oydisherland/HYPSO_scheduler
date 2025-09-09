import datetime

from data_postprocessing.fromFile_toObject import getScheduleFromFile
from data_preprocessing.get_target_passes import getGroundStationTimeWindows
from scheduling_model import OT, TTW, BT, GSTW
import matplotlib.pyplot as plt
import time


buffering_time = 900  # seconds
max_buffer_offset = 12 * 3600  # Maximum offset between a capture and its buffering in seconds
interTaskTime = 100  # seconds between two tasks to account for transition time
groundStationFilePath = "data_input/HYPSO_data/ground_stations.csv"
ohDuration = 48*3600  # Duration of the observation horizon in seconds

def scheduleTransmissions(otList: list[OT], ttwList: list[TTW], gstwListSorted: list[GSTW]):
    """
    Try to schedule the transmission of each observed target in otList.
    Transmission consists of transmitting to Ground Station and buffering the capture before actually transmitting.

    Args:
        otList (list[OT]): List of observation tasks to schedule transmissions for.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.
        gstwListSorted (list[GSTW]): List of ground station time windows with time windows sorted by time.

    Returns:
        tuple[bool, list[BT], list[OT]]: A tuple containing:
            - A boolean indicating if a valid transmission schedule was found.
            - A list of scheduled buffering tasks (BT).
            - A list of observation tasks, possibly changed to fit the observation tasks.
    """
    btList: list[BT] = []
    otListSorted = sorted(otList, key=lambda x: x.start)
    validScheduleFound = True
    for otToBuffer in otList:
        bt = generateBufferTaskDirectInsert(otToBuffer, otListSorted, btList, gstwListSorted)
        if bt is not None:
            btList.append(bt)
        else:
            print(
                f"Could not schedule buffering task for observation of target {otToBuffer.GT.id} at {otToBuffer.start}")
            validScheduleFound = False

    return validScheduleFound, btList, otList


def generateBufferTaskDirectInsert(otToBuffer: OT, otListSorted: list[OT], btList: list[BT], gstwListSorted: list[GSTW]):
    """
    Try to insert the buffering of an observed target directly into the schedule.
    Insertion is tried at the end of other tasks, so all tasks neatly follow each other.
    If no valid insertion is found, return None.

    Args:
        otToBuffer (OT): The observation task to schedule buffering for.
        otListSorted (list[OT]): List of all observation tasks, sorted by start time
        btList (list[BT]): List of all already scheduled buffering tasks.
        gstwListSorted (list[GSTW]): List of all ground station time windows, sorted by start time.
    """

    candidateBT = BT(otToBuffer.GT, otToBuffer.end + interTaskTime, otToBuffer.end + buffering_time + interTaskTime)

    # First guess is to immediately start buffering after observation
    if not bufferTaskConflicting(candidateBT, btList, otListSorted, gstwListSorted):
        return candidateBT

    # From now on, we will save all the possible candidates and later pick the earliest option
    candidateBTList : list[BT] = []

    # Now try to insert the buffer task at the end of other observation tasks
    for ot in otListSorted:
        if ot.end - otToBuffer.end > max_buffer_offset:
            # Inserting the buffer tasks after this point would be too far from the observation task
            # Observation tasks are sorted by time, so looking further is not necessary
            break
        if ot.end < otToBuffer.end:
            # Skip if the candidate buffer task would be scheduled before its target observation
            continue

        candidateBT = BT(otToBuffer.GT, ot.end + interTaskTime, ot.end + buffering_time + interTaskTime)
        if not bufferTaskConflicting(candidateBT, btList, otListSorted, gstwListSorted):
            candidateBTList.append(candidateBT)
            # Observation tasks are sorted by time, so looking further is not necessary
            break

    # Now try to insert the buffer task at the end of other buffer tasks
    for bt in btList:
        if bt.end - otToBuffer.end > max_buffer_offset or bt.end < otToBuffer.end:
            continue

        candidateBT = BT(otToBuffer.GT, bt.end + interTaskTime, bt.end + buffering_time + interTaskTime)
        if not bufferTaskConflicting(candidateBT, btList, otListSorted, gstwListSorted):
            candidateBTList.append(candidateBT)


    # Last attempt is to insert after a ground station time window
    for gstw in gstwListSorted:
        for tw in gstw.TWs:
            if tw.end - otToBuffer.end > max_buffer_offset:
                # Inserting the buffer tasks after this point would be too far from the observation task
                # Time windows are sorted by time, so looking further is not necessary
                break
            if tw.end < otToBuffer.end:
                continue

            candidateBT = BT(otToBuffer.GT, tw.end + interTaskTime, tw.end + buffering_time + interTaskTime)
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

def plotSchedule(otList: list[OT], btList: list[BT], gstwList: list[GSTW]):
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
            y=-0.1  - (i%3) * 0.04,  # below y=0 row
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

    # Formatting
    plt.xlim(0, ohDuration)
    plt.xlabel("Time [s]")
    plt.legend()
    plt.tight_layout()
    plt.show()



otList = getScheduleFromFile("C:/Users/20212052/git/TU/HYPSO_scheduler/BS_test12-run1.json")

startTimeOH = datetime.datetime.now(datetime.timezone.utc)
endTimeOH = startTimeOH + datetime.timedelta(seconds= ohDuration)
gstwList = getGroundStationTimeWindows(startTimeOH, endTimeOH, groundStationFilePath, 1)

start_time = time.perf_counter()
valid, btList, otListModified = scheduleTransmissions(otList, [], gstwList)
end_time = time.perf_counter()

print(f"{(end_time - start_time)*1000:.4f} milliseconds")

plotSchedule(otListModified, btList, gstwList)