import datetime

import data_postprocessing.algorithmData_api as AD_api
from data_preprocessing.get_target_passes import getGroundStationTimeWindows
from scheduling_model import TTW, TW
import time

from input_parameters import getInputParams
from transmission_scheduling.two_stage_transmission_insert import twoStageTransmissionScheduling
from transmission_scheduling.util import bufferFileCounter
from util import plotSchedule


# TODO re-order transmission tasks such that split up transmission tasks are next to each other
# TODO make a cleaning sweep re-assigning transmission tasks to buffer tasks that are close to each other, same could be done for captures and their buffering
# TODO after/inter task/capture time are used quite randomly, it should be more clear where they are used (for example when checking for conflicts), they are not used uniformly and difficult to change
# TODO consider that data transmission cannot happen or is at least slower during a capture when in the transmission window
# TODO possibly add support for spreading transmission over more than 2 ground station passes

parametersFilePath = "../data_input/input_parameters.csv"
p = getInputParams(parametersFilePath)

otList = AD_api.getScheduleFromFile("BS_test12-run1.json")  # observation task
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

startTimeOH = datetime.datetime(2025, 8, 27, 15, 29, 0)
startTimeOH = startTimeOH.replace(tzinfo=datetime.timezone.utc)
endTimeOH = startTimeOH + datetime.timedelta(seconds=p.ohDuration)

groundStationFilePath = "data_input/HYPSO_data/ground_stations.csv"
gstwList = getGroundStationTimeWindows(startTimeOH, endTimeOH, p.minGSWindowTime, groundStationFilePath, p.hypsoNr)

start_time = time.perf_counter()
valid, btList, dtList, otListModified = twoStageTransmissionScheduling(otListPrioSorted, ttwList, gstwList, p)
end_time = time.perf_counter()

btList = sorted(btList, key=lambda x: x.GT.priority, reverse=True)
dtList = sorted(dtList, key=lambda x: x.GT.priority, reverse=True)
otListModified = sorted(otListModified, key=lambda x: x.GT.priority, reverse=True)


print(f"{(end_time - start_time) * 1000:.4f} milliseconds")

bufferFileCounter(btList, dtList)
print(f"Number of buffering tasks: {len(btList)}")

plotSchedule(otListModified, otListPrioSorted, btList, dtList, gstwList, ttwList, p)
