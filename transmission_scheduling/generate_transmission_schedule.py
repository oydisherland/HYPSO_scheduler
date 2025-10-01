import datetime

import data_postprocessing.algorithmData_api as AD_api
from data_preprocessing.get_target_passes import getGroundStationTimeWindows
from scheduling_model import TTW, TW
import time

import cProfile
from input_parameters import getInputParams
from transmission_scheduling.clean_schedule import cleanUpSchedule, OrderType
from transmission_scheduling.two_stage_transmission_insert import twoStageTransmissionScheduling
from transmission_scheduling.util import latencyCounter
from util import plotSchedule

# TODO re-insertion iterations take a long time, find a way to cancel insertions earlier
# TODO figure what to do with captures that can only be planned during a ground station pass
# TODO experiment with having more than 7 buffers between buffer clearings, this does require adjustments in the priority cleanup/reassignment of the downlink tasks
# TODO prioritize scheduling in less busy parts of the schedule first

def generate_schedule():
    parametersFilePath = "../data_input/input_parameters.csv"
    p = getInputParams(parametersFilePath)

    otList = AD_api.getScheduleFromFile("test-schedule.json")  # observation task
    otListPrioSorted = sorted(otList, key=lambda x: x.GT.priority, reverse=True)

    # Create TTW list by adding some time before and after each observation task
    ttwList: list[TTW] = []
    for ot in otList:
        ttwStart = max(0, ot.start - 50)
        ttwEnd = min(p.ohDuration, ot.end + 50)
        ttwStart2 = max(0, ot.start + 12000)
        ttwEnd2 = min(p.ohDuration, ot.end + 12100)
        ttwStart3 = max(0, ot.start + 6000)
        ttwEnd3 = min(p.ohDuration, ot.end + 6100)
        ttwList.append(TTW(ot.GT, [TW(ttwStart, ttwEnd), TW(ttwStart2, ttwEnd2), TW(ttwStart3, ttwEnd3)]))

    # startTimeOH = datetime.datetime(2025, 8, 27, 15, 29, 0)
    # startTimeOH = datetime.datetime(2025, 8, 4, 20, 35, 0)
    startTimeOH = datetime.datetime(2025, 9, 12, 16, 39, 0)


    startTimeOH = startTimeOH.replace(tzinfo=datetime.timezone.utc)
    endTimeOH = startTimeOH + datetime.timedelta(seconds=p.ohDuration)

    groundStationFilePath = "data_input/HYPSO_data/ground_stations.csv"
    gstwList = getGroundStationTimeWindows(startTimeOH, endTimeOH, p.minGSWindowTime, groundStationFilePath, p.hypsoNr)

    start_time = time.perf_counter()
    valid, btList, dtList, otListModified = twoStageTransmissionScheduling(otListPrioSorted, ttwList, gstwList, p)
    end_time = time.perf_counter()
    latencyCounter(otListModified, dtList)
    btList, dtList = cleanUpSchedule(otListModified, btList, dtList, gstwList, p, OrderType.FIFO, OrderType.PRIORITY)
    latencyCounter(otListModified, dtList)

    btList = sorted(btList, key=lambda x: x.GT.priority, reverse=True)
    dtList = sorted(dtList, key=lambda x: x.GT.priority, reverse=True)
    otListModified = sorted(otListModified, key=lambda x: x.GT.priority, reverse=True)


    print(f"{(end_time - start_time) * 1000:.4f} milliseconds")

    print(f"Number of buffering tasks: {len(btList)}")

    if not profiling:
        plotSchedule(otListModified, otListPrioSorted, btList, dtList, gstwList, ttwList, p)


profiling = False

if not profiling:
    generate_schedule()
else:
    cProfile.run('generate_schedule()', 'cprofile_output.prof')
    pass