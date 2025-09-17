import copy

from scheduling_model import OT, TTW, GSTW, BT, DT
from transmission_scheduling import insertion
from transmission_scheduling.conflict_checks import observationTaskConflicting
from transmission_scheduling.generate_downlink import generateDownlinkTask
from transmission_scheduling.input_parameters import TransmissionParams
from transmission_scheduling.util import getClosestGSTW, gstwToSortedTupleList


def twoStageTransmissionScheduling(otList: list[OT], ttwList: list[TTW], gstwList: list[GSTW],
                                   parameters: TransmissionParams) -> tuple[bool, list[BT], list[DT], list[OT]]:
    """
    Try to schedule the transmission of each observed target in otList.
    Transmission consists of transmitting to Ground Station and buffering the capture before actually transmitting.
    The observation tasks will be considered in the order that they are provided, so sorting by priority is recommended.

    The first phase will try to insert the bufferings and transmissions with several strategies.
    The second phase will try to re-insert the observation tasks that could not be scheduled in the first phase.
    This re-insertion is attempted at other target time windows (other passes of the satellite over the target)

    Args:
        otList (list[OT]): List of observation tasks to schedule transmissions for.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.
        gstwList (list[GSTW]): List of ground station time windows with time windows corresponding to each GS.
        parameters (TransmissionParams): Parameters for the transmission scheduling.

    Returns:
        tuple[bool, list[BT], list[DT], list[OT]]: A tuple containing:

            - A boolean indicating if a transmission schedule has been found for all observation tasks.
                If false, there can still be a useful output containing a schedule for the tasks that were able to fit.
            - A list of scheduled buffering tasks (BT).
            - A list of scheduled downlink tasks (DT).
            - A list of observation tasks, possibly changed to fit the buffering and downlinking tasks.
    """
    p = parameters
    valid, btList, dtList, otListScheduled = scheduleTransmissions(otList, ttwList, gstwList, p)

    if valid:
        # A full schedule has been found in the first attempt, so we can return
        return valid, btList, dtList, otListScheduled

    # Find the observation tasks that could not be scheduled
    otListUnscheduled = otList.copy()
    ttwListUnscheduled = copy.deepcopy(ttwList)
    for otScheduled in otListScheduled:
        for ttw in ttwList:
            if ttw.GT == otScheduled.GT:
                ttwListUnscheduled.remove(ttw)
                break
        for ot in otList:
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

    # Try to find other time windows that are free to schedule the observation tasks
    otListReInsert: list[OT] = []
    for ttw in ttwListUnscheduled:
        for tw in ttw.TWs:
            halfTime = (tw.start + tw.end) / 2
            # The new observation task will be centered, the insertion algorithms could always shift it if needed
            otCandidate = OT(ttw.GT, halfTime - p.captureDuration / 2, halfTime + p.captureDuration / 2)
            if not observationTaskConflicting(otCandidate, btList, otListScheduled, gstwList, p):
                otListReInsert.append(otCandidate)
                break

    print("======= Starting re-insertion phase for unscheduled observation tasks =======")
    n_before = len(otListScheduled)
    valid, btList, dtList, otListScheduled = scheduleTransmissions(otListReInsert, ttwList, gstwList, p,
                                                                   otListScheduled, btList, dtList)
    n_after = len(otListScheduled)
    print(f"Succesfully re-inserted {n_after - n_before} observation tasks out of {len(otListReInsert)}")
    return valid, btList, dtList, otListScheduled



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

    # Merge the existing observation tasks into the new list based on ground target
    # We will assume that the existing observation tasks are more up to date than otList
    if existingOTList is not None:
        existingOTListCopy = existingOTList.copy()
        for existingOT in existingOTList:
            for ot in otListMod:
                if ot.GT == existingOT.GT:
                    # Remove the old OT and replace it with the existing one
                    # Add it at the start, because existing tasks should have higher priority
                    otListMod.remove(ot)
                    otListMod.insert(0, existingOT)
                    existingOTListCopy.remove(existingOT)
                    break

        # There might be some observation tasks left in the existing list that are not in otList
        # We will add them as highest priority to the list, making it less likely for them to be modified or deleted
        otListMod = existingOTListCopy + otListMod

    completeScheduleFound = True

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

        if observationTaskConflicting(otToBuffer, btList, otListMod, gstwList, p):
            # The observation task is conflicting with already scheduled tasks, so we cannot buffer it
            completeScheduleFound = False
            otListMod.remove(otToBuffer)
            continue

        validBTFound = False
        closestGSTW = getClosestGSTW(otToBuffer, gstwList, p.maxGSTWAhead)
        closestGSTWSorted = gstwToSortedTupleList(closestGSTW)

        for insertMethod in insertList:
            if validBTFound:
                # If a valid buffer task has been found we don't need to look further
                break
            # Iterate over the closest ground station passes and try to buffer it before the pass
            for i, entry in enumerate(closestGSTWSorted):
                gstw = GSTW(entry[0], [entry[1]])
                nextGSTW = GSTW(closestGSTWSorted[i + 1][0], [closestGSTWSorted[i + 1][1]]) \
                    if i + 1 < len(closestGSTWSorted) else None

                candidateDTList = generateDownlinkTask(gstw, nextGSTW, p.downlinkDuration, dtList, otToBuffer, p)
                if candidateDTList is None: continue  # No valid downlink task could be scheduled in this ground station time window

                bt, otListMod, btList = insertMethod.generateBuffer(otToBuffer, gstw, otListMod, btList, gstwList,
                                                                    ttwList)

                if bt is not None:
                    btList.append(bt)
                    for candidate in candidateDTList:
                        dtList.append(candidate)
                    validBTFound = True
                    # We found a buffer task and corresponding GSTW to downlink, so we don't need to consider other GSTW
                    break

        if not validBTFound:
            # No valid GSTW has been found to downlink the buffered data
            completeScheduleFound = False
            print(f"Transmission scheduling failed for {otToBuffer.GT.id} at {otToBuffer.start}")
            # Remove the currently considered observation task by checking if ground target matches
            otListMod.remove(otToBuffer)

    return completeScheduleFound, btList, dtList, otListMod
