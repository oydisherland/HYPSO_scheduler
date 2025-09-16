from scheduling_model import OT, BT, GSTW, TW, DT
from transmission_scheduling.input_parameters import TransmissionParams


def getConflictingTasks(tw: TW, btList: list[BT], otList: list[OT], gstwList: list[GSTW], p: TransmissionParams, cancelEarly: bool = False):
    """
    Get the list of tasks that conflict with the given time window.

    Args:
        tw (TW): The time window to check for conflicts.
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


def bufferTaskConflicting(bt: BT, btList: list[BT], otList: list[OT], gstwList: list[GSTW], p: TransmissionParams):
    """
    Check if the buffering task overlaps with any other scheduled tasks.

    Args:
        bt (BT): The buffering task to validate.
        btList (list[BT]): List of all already scheduled buffering tasks.
        otList (list[OT]): List of all observation tasks.
        gstwList (list[GSTW]): List of all ground station time windows.
        p (TransmissionParams): Input parameters containing timing configurations.

    Returns:
        bool: True if the buffering task conflicts with any other task, False otherwise.
    """
    bufferTimeWindow = TW(bt.start, bt.end + p.interTaskTime)
    # Remove the buffer task from the list to prevent self conflict
    btListOther = [otherBT for otherBT in btList if otherBT != bt]
    conflictOTs, conflictBTs, conflictGSTWs = getConflictingTasks(bufferTimeWindow, btListOther, otList, gstwList, p, True)
    return bool(conflictOTs or conflictBTs or conflictGSTWs)


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
