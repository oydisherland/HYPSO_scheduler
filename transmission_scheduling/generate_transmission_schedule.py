import datetime

import data_postprocessing.algorithmData_api as AD_api
from data_preprocessing.get_target_passes import getGroundStationTimeWindows
from scheduling_model import TTW, TW
import time

from input_parameters import getInputParams
from transmission_scheduling.three_stage_transmission_insert import scheduleTransmissions
from util import plotSchedule


# TODO re-order transmission tasks such that split up transmission tasks are next to each other
# TODO make a cleaning sweep re-assigning transmission tasks to buffer tasks that are close to each other, same could be done for captures and their buffering
# TODO after/inter task/capture time are used quite randomly, it should be more clear where they are used (for example when checking for conflicts), they are not used uniformly and difficult to change
# TODO consider that data transmission cannot happen or is at least slower during a capture when in the transmission window
# TODO possibly add support for spreading transmission over more than 2 ground station passes

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

start_time = time.perf_counter()
valid, btList, dtList, otListModified = scheduleTransmissions(otListPrioSorted, ttwList, gstwList, p)
end_time = time.perf_counter()

print(f"{(end_time - start_time) * 1000:.4f} milliseconds")

plotSchedule(otListModified, otListPrioSorted, btList, dtList, gstwList, ttwList, p)
