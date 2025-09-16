import datetime

import data_postprocessing.algorithmData_api as AD_api
from data_preprocessing.get_target_passes import getGroundStationTimeWindows
from scheduling_model import OT, TTW, BT, GSTW, TW, DT
import time

from conflict_checks import downlinkTaskConflicting
import insertion
from input_parameters import getInputParams
from transmission_scheduling.generate_downlink import generateDownlinkTask
from util import plotSchedule, getClosestGSTW, gstwToSortedTupleList


# TODO re-order transmission tasks such that split up transmission tasks are next to each other
# TODO make a cleaning sweep re-assigning transmission tasks to buffer tasks that are close to each other, same could be done for captures and their buffering
# TODO after/inter task/capture time are used quite randomly, it should be more clear where they are used (for example when checking for conflicts), they are not used uniformly and difficult to change
# TODO consider that data transmission cannot happen or is at least slower during a capture when in the transmission window
# TODO possibly add support for spreading transmission over more than 2 ground station passes



def scheduleTransmissions(otList: list[OT], ttwList: list[TTW], gstwList: list[GSTW]):
    """
    Try to schedule the transmission of each observed target in otList.
    Transmission consists of transmitting to Ground Station and buffering the capture before actually transmitting.
    The observation tasks will be considered in the order that they are provided, so sorting by priority is recommended.

    Args:
        otList (list[OT]): List of observation tasks to schedule transmissions for.
        ttwList (list[TTW]): List of target time windows, which will be consulted when shifting observation tasks to fit buffering.
        gstwList (list[GSTW]): List of ground station time windows with time windows corresponding to each GS.

    Returns:
        tuple[bool, list[BT], list[DT], list[OT]]: A tuple containing:

            - A boolean indicating if a transmission schedule has been found for all observation tasks.
                If false, there can still be a useful output containing a schedule for the tasks that were able to fit.
            - A list of scheduled buffering tasks (BT).
            - A list of scheduled downlink tasks (DT).
            - A list of observation tasks, possibly changed to fit the buffering and downlinking tasks.
    """
    directInsert = insertion.DirectInsertion(p)
    slideInsert = insertion.SlideInsertion(p)
    deleteInsert = insertion.DeleteInsertion(p)
    insertList: list[insertion.InsertionInterface] = [directInsert, slideInsert, deleteInsert]

    btList: list[BT] = []
    dtList: list[DT] = []

    otListMod = otList.copy() # This is the list of observation tasks that will be kept updated as tasks are deleted or shifted
    completeScheduleFound = True

    for otOriginal in otList:
        # First match the original OT to the most recently updated version that has been possibly shifted or deleted
        otToBuffer = None
        for ot in otListMod:
            if ot.GT == otOriginal.GT:
                otToBuffer = ot
                break

        # If we could not find the OT in the modified list, it has been deleted, and we can continue to the next OT
        if otToBuffer is None:
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

                bt, otListMod, btList = insertMethod.generateBuffer(otToBuffer, gstw, otListMod, btList, gstwList, ttwList)

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
            print(
                f"Transmission scheduling failed for {otToBuffer.GT.id} at {otToBuffer.start}")
            # Remove the currently considered observation task by checking if ground target matches
            otListMod.remove(otToBuffer)

    return completeScheduleFound, btList, dtList, otListMod

def getInputs():
    parametersFilePath = "../data_input/input_parameters.csv"
    p = getInputParams(parametersFilePath)

    groundStationFilePath = "data_input/HYPSO_data/ground_stations.csv"

    otList = AD_api.getScheduleFromFile("BS_test12-run1.json")  # observation task
    otListPrioSorted = sorted(otList, key=lambda x: x.GT.priority, reverse=True)

    # Create TTW list by adding some time before and after each observation task
    ttwList: list[TTW] = []
    for ot in otList:
        ttwStart = max(0, ot.start - 50)
        ttwEnd = min(p.ohDuration, ot.end + 50)
        ttwList.append(TTW(ot.GT, [TW(ttwStart, ttwEnd)]))

    startTimeOH = datetime.datetime(2025, 8, 27, 15, 29, 0)
    startTimeOH = startTimeOH.replace(tzinfo=datetime.timezone.utc)
    endTimeOH = startTimeOH + datetime.timedelta(seconds=p.ohDuration)

    gstwList = getGroundStationTimeWindows(startTimeOH, endTimeOH, p.minGSWindowTime, groundStationFilePath, p.hypsoNr)

    return otListPrioSorted, ttwList, gstwList, p

otListPrioSorted, ttwList, gstwList, p = getInputs()

start_time = time.perf_counter()
valid, btList, dtList, otListModified = scheduleTransmissions(otListPrioSorted, ttwList, gstwList)
end_time = time.perf_counter()

print(f"{(end_time - start_time) * 1000:.4f} milliseconds")

plotSchedule(otListModified, otListPrioSorted, btList, dtList, gstwList, ttwList, p)
