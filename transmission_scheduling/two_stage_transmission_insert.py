from scheduling_model import OT, TTW, GSTW, BT, DT, GS, TW
from transmission_scheduling import insertion
from transmission_scheduling.conflict_checks import observationTaskConflicting
from transmission_scheduling.generate_downlink import generateDownlinkTask
from transmission_scheduling.input_parameters import TransmissionParams
from transmission_scheduling.util import getClosestGSTW, gstwToSortedTupleList, findPossibleTTW


def twoStageTransmissionScheduling(otList: list[OT], ttwList: list[TTW], gstwList: list[GSTW],
                                   parameters: TransmissionParams, sortOtList: bool = True,
                                   fullReinsert: bool = False) -> tuple[list[BT], list[DT], list[OT]]:
    """
    Try to schedule the transmission of each observed target in otList.
    Transmission consists of transmitting to Ground Station and buffering the capture before actually transmitting.
    The observation tasks will be considered in the order that they are provided, so sorting by priority is recommended.

    The first phase will try to insert the buffer and transmission tasks with several strategies.
    The second phase will try to re-insert the observation tasks that could not be scheduled in the first phase.
    This re-insertion is attempted at other target time windows (other passes of the satellite over the target)

    Args:
        otList (list[OT]): List of observation tasks to schedule transmissions for.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.
        gstwList (list[GSTW]): List of ground station time windows with time windows corresponding to each GS.
        parameters (TransmissionParams): Parameters for the transmission scheduling.
        sortOtList (bool, optional): Whether the observation tasks should be sorted by priority by this function.
        fullReinsert (bool): Whether to try to re-insert observation tasks which were not included in otList.

    Returns:
        tuple[list[BT], list[DT], list[OT]]: A tuple containing:

            - A list of scheduled buffering tasks (BT).
            - A list of scheduled downlink tasks (DT).
            - A list of observation tasks, possibly changed to fit the buffering and downlinking tasks.
    """
    otListCopy = sorted(otList, key=lambda x: x.GT.priority, reverse=True) if sortOtList else otList.copy()

    """
    Phase 1: Regular insertion phase using several strategies (e.g. direct, sliding, deleting)
    """
    p = parameters
    fullScheduleFound, btList, dtList, otListScheduled = scheduleTransmissions(otListCopy, ttwList, gstwList, p)

    if fullScheduleFound:
        return btList, dtList, otListScheduled

    """
    Phase 2: Re-insertion phase for the observation tasks that could not be scheduled in the first phase
    """
    possibleTTW = findPossibleTTW(ttwList, otListCopy, otListScheduled, fullReinsert)
    otListReInsert = generateNewOTList(possibleTTW, otListScheduled, btList, dtList, gstwList, p)

    for i in range(p.reInsertIterations):

        _, btList, dtList, otListScheduled = scheduleTransmissions(otListReInsert, ttwList, gstwList, p,
                                                                                   otListScheduled, btList, dtList)

        if i == p.reInsertIterations - 1:
            break  # No need to update for another iteration

        # Update the possible TTW list and the OT list to re-insert for the next cycle
        possibleTTW = findPossibleTTW(possibleTTW, otListReInsert, otListScheduled, fullReinsert)
        otListReInsert = generateNewOTList(possibleTTW, otListScheduled, btList, dtList, gstwList, p)

    return btList, dtList, otListScheduled


def scheduleTransmissions(otList: list[OT], ttwList: list[TTW], gstwList: list[GSTW], parameters: TransmissionParams,
                          existingOTList: list[OT] = None, existingBTList: list[BT] = None,
                          existingDTList: list[DT] = None) -> tuple[bool, list[BT], list[DT], list[OT]]:
    """
    Try to schedule the transmission of each observed target in otList.
    Transmission consists of transmitting to Ground Station and buffering the capture before actually transmitting.
    The observation tasks will be considered in the order that they are provided, so sorting by priority is recommended.

    Args:
        otList (list[OT]): List of observation tasks to schedule transmissions for.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.
        gstwList (list[GSTW]): List of ground station time windows with time windows corresponding to each GS.
        parameters (TransmissionParams): Parameters for the transmission scheduling.
        existingOTList (list[OT], optional): List of already scheduled observation tasks.
        existingBTList (list[BT], optional): List of already scheduled buffering tasks.
        existingDTList (list[DT], optional): List of already scheduled downlink tasks.

    Returns:
        tuple[bool, list[BT], list[DT], list[OT]]: A tuple containing:

            - A boolean indicating if a transmission schedule has been found for all observation tasks.
              If false, there can still be a useful output containing a schedule for the tasks that were able to fit.
            - A list of scheduled buffering tasks (BT).
            - A list of scheduled downlink tasks (DT).
            - A list of observation tasks, possibly changed to fit the buffering and downlinking tasks.
    """
    p = parameters

    directInsert = insertion.DirectInsertion(p)
    slideInsert = insertion.SlideInsertion(p)
    deleteInsert = insertion.DeleteInsertion(p)
    insertList: list[insertion.InsertionInterface] = [directInsert, slideInsert, deleteInsert]

    btList: list[BT] = existingBTList.copy() if existingBTList is not None else []
    dtList: list[DT] = existingDTList.copy() if existingDTList is not None else []

    otListMod = otList.copy()  # This is the list of observation tasks that will be kept updated as tasks are deleted or shifted

    if existingOTList is not None:
        # Check if there are any tasks in the existing OT list that are also in the list to be scheduled
        for existingOT in existingOTList:
            for ot in otListMod:
                if ot.GT == existingOT.GT:
                    raise ValueError("The existing OT list contains a task that is also in the list to be scheduled.")

        # We will add the existing OT list as highest priority to the list,
        # making it less likely for them to be modified or deleted
        otListMod = existingOTList.copy() + otListMod

    for otOriginal in otList:
        # First check if the observation task already has a corresponding buffering task
        alreadyBuffered = False
        for bt in btList:
            if bt.GT == otOriginal.GT:
                alreadyBuffered = True
                break

        if alreadyBuffered: continue

        # Match the original OT to the most recently updated version that has been possibly shifted or deleted
        otToBuffer = None
        for ot in otListMod:
            if ot.GT == otOriginal.GT:
                otToBuffer = ot
                break

        # If we could not find the OT in the modified list, it has been deleted, and we can continue to the next OT
        if otToBuffer is None: continue

        if observationTaskConflicting(otToBuffer, btList, dtList, otListMod, gstwList, p):
            # The observation task is conflicting with already scheduled tasks, so we cannot buffer it
            otListMod.remove(otToBuffer)
            continue

        validBTFound = False
        closestGSTW = getClosestGSTW(otToBuffer.end, gstwList, p.maxLatency)
        closestGSTWSorted = gstwToSortedTupleList(closestGSTW)
        # TODO check if this \/ is somehow meta, or order the GS passes in different priority than just chronological order
        # closestGSTWSorted = sorted(closestGSTWSorted, key=lambda x: x[1].start, reverse=True)

        # Iterate over the closest ground station passes and try to buffer it before the pass
        for i, entry in enumerate(closestGSTWSorted):
            if validBTFound:
                # If a valid buffer task has been found we don't need to look further
                break
            for insertMethod in insertList:
                gstw = GSTW(entry[0], [entry[1]])
                # Find the list of future GSTW that could be used to downlink the remaining data if needed
                nextGSTWList: list[tuple[GS, TW]]  # Storing the GS passes in this form is more convenient
                nextGSTWList = closestGSTWSorted[i + 1:] if i + 1 < len(closestGSTWSorted) else []
                candidateOTList = otListMod.copy()
                candidateOTList.append(otToBuffer)
                candidateDTList = generateDownlinkTask(candidateOTList, gstw, nextGSTWList, dtList, otToBuffer.GT, p)
                if candidateDTList is None: continue  # No valid downlink task could be scheduled in this ground station time window
                dtListPlusCandidates = dtList + candidateDTList
                bt, otListMod, btList = insertMethod.generateBuffer(otToBuffer, gstw, otListMod, btList,
                                                                    dtListPlusCandidates, gstwList, ttwList)

                if bt is not None:
                    btList.append(bt)
                    for candidate in candidateDTList:
                        dtList.append(candidate)
                    validBTFound = True
                    # We found a buffer task and corresponding GSTW to downlink, so we don't need to consider other GSTW
                    break

        if not validBTFound:
            # No valid GSTW has been found to downlink the buffered data
            # print(f"Transmission scheduling failed for {otToBuffer.GT.id} at {otToBuffer.start}")
            # Remove the currently considered observation task by checking if ground target matches
            otListMod.remove(otToBuffer)

    completeScheduleFound = len(otListMod) == len(otList)
    return completeScheduleFound, btList, dtList, otListMod


def generateNewOTList(possibleTTW: list[TTW], otListScheduled: list[OT], btListScheduled: list[BT],
                      dtListScheduled: list[DT], gstwList: list[GSTW], p: TransmissionParams) -> list[OT]:
    """
    Based on a list of possible target time windows, generate a list of observation tasks that could be scheduled.

    Args:
        possibleTTW (list[TTW]): List of target time windows that could still be used to schedule the unscheduled observation tasks.
        otListScheduled (list[OT]): List of observation tasks that have been successfully scheduled.
        btListScheduled (list[BT]): List of buffering tasks that have been successfully scheduled.
        dtListScheduled (list[DT]): List of downlinking tasks that have been successfully scheduled.
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
            # Check for a conflict of this OT with the already scheduled tasks and the new ones
            fullOTList = otListScheduled + newOTList
            if not observationTaskConflicting(otCandidate, btListScheduled, dtListScheduled, fullOTList, gstwList, p):
                newOTList.append(otCandidate)
                break

    return newOTList
