from scheduling_model import OT, TTW, BT, GSTW

buffering_time = 15  # seconds
max_buffer_offset = 12 * 3600  # Maximum offset between a capture and its buffering in seconds


def scheduleTransmissions(otList: list[OT], ttwList: list[TTW]):
    """
    Try to schedule the transmission of each observed target in otList.
    Transmission consists of transmitting to Ground Station and buffering the capture before actually transmitting.

    Args:
        otList (list[OT]): List of observation tasks to schedule transmissions for.
        ttwList (list[TTW]): List of target time windows (not used in current implementation).

    Returns:
        tuple[bool, list[BT], list[OT]]: A tuple containing:
            - A boolean indicating if a valid schedule was found for all buffering tasks.
            - A list of scheduled buffering tasks (BT).
            - A possibly changed List of observation tasks (OT) to fit the observation tasks.
    """
    btList: list[BT] = []
    validScheduleFound = True
    for otToBuffer in otList:
        bt = generateBufferTaskDirectInsert(otToBuffer, otList, btList, [])
        if bt is not None:
            btList.append(bt)
        else:
            print(
                f"Could not schedule buffering task for observation of target {otToBuffer.GT.id} at {otToBuffer.start}")
            validScheduleFound = False

    return validScheduleFound, btList, otList


def bufferTaskValid(bt: BT, btList: list[BT], otList: list[OT], gstwList: list[GSTW]):
    """
    Check if the buffering task overlaps with any other scheduled tasks.
    """
    # TODO sort the lists chronologically beforehand to be able to break off search early or do binary search
    for ot in otList:
        if ot.end < bt.start or ot.start > bt.end:
            continue
        else:
            return False
    for otherBT in btList:
        if otherBT.GT == bt.GT:
            # The task we are comparing is the same buffering task
            continue
        if otherBT.end < bt.start or otherBT.start > bt.end:
            continue
        else:
            return False
    for gstw in gstwList:
        for tw in gstw.TWs:
            if tw.end <= bt.start or tw.start >= bt.end:
                continue
            else:
                return False

    return True


def generateBufferTaskDirectInsert(otToBuffer: OT, otList: list[OT], btList: list[BT], gstwList: list[GSTW]):
    """
    Try to insert the buffering of an observed target directly into the schedule.
    Insertion is tried at the end of other tasks, so all tasks neatly follow each other.
    If no valid insertion is found, return None.
    """

    # First guess is to immediately start buffering after observation
    candidateBufferTask = BT(otToBuffer.GT, otToBuffer.end, otToBuffer.end + buffering_time)
    if bufferTaskValid(candidateBufferTask, btList, otList, []):
        return candidateBufferTask

    # Now try to insert the buffer task at the end of other observation tasks
    for ot in otList:
        if ot.end - otToBuffer.end > max_buffer_offset or ot.end < otToBuffer.end:
            # Skip if the observation task ends too long after the target observation
            # or if the candidate buffer task would be scheduled before its target observation
            continue

        candidateBufferTask.start = ot.end
        candidateBufferTask.end = ot.end + buffering_time
        if bufferTaskValid(candidateBufferTask, btList, otList, []):
            return candidateBufferTask

    # Now try to insert the buffer task at the end of other buffer tasks
    for bt in btList:
        if bt.end - otToBuffer.end > max_buffer_offset or bt.end < otToBuffer.end:
            continue

        candidateBufferTask.start = bt.end
        candidateBufferTask.end = bt.end + buffering_time
        if bufferTaskValid(candidateBufferTask, btList, otList, []):
            return candidateBufferTask

    # Last attempt is to insert after a ground station time window
    for gstw in gstwList:
        for tw in gstw.TWs:
            if tw.end - otToBuffer.end > max_buffer_offset or tw.end < otToBuffer.end:
                continue

            candidateBufferTask.start = tw.end
            candidateBufferTask.end = tw.end + buffering_time
            if bufferTaskValid(candidateBufferTask, btList, otList, []):
                return candidateBufferTask

    # No valid insertions have been found, return None
    return None
