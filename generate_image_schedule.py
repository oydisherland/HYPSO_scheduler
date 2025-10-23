import os
import datetime

from data_preprocessing.objective_functions import objectiveFunctionPriority, objectiveFunctionImageQuality
from scheduling_model import SP
from algorithm.NSGA2 import runNSGA
from data_preprocessing.create_data_objects import createTTWList, createOH, createGSTWList
from campaignPlanner_interaction.intergrate_campaign_planner import createCmdFile, createCmdLinesForCaptureAndBuffering, recreateOTListFromCmdFile

from transmission_scheduling.clean_schedule import cleanUpSchedule, OrderType
from transmission_scheduling.input_parameters import getTransmissionInputParams
from transmission_scheduling.util import plotSchedule, plotCompareSchedule
from data_input.utility_functions import InputParameters




### Create the image schedule ####

inputParametersFilePath = os.path.join(os.path.dirname(__file__),"data_input/input_parameters.csv")
ttwListFilePath = os.path.join(os.path.dirname(__file__),"data_input/HYPSO_data/ttw_list_2025_10_09_1600.json")

inputParameters = InputParameters.from_csv(inputParametersFilePath)

# # Check if start time is now
if inputParameters.startTimeOH == "now":
    inputParameters.startTimeOH = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

# Create model parameters
schedulingParameters = SP(
    int(inputParameters.maxCaptures),
    int(inputParameters.captureDuration),
    int(inputParameters.transitionTime),
    int(inputParameters.hypsoNr))
oh = createOH(datetime.datetime.fromisoformat(inputParameters.startTimeOH), int(inputParameters.durationInDaysOH))
transmissionParameters = getTransmissionInputParams(inputParametersFilePath)

# Create data Objects
ttwList = createTTWList( int(inputParameters.captureDuration), oh, int(inputParameters.hypsoNr), ttwListFilePath, ttwListFilePath)
gstwList = createGSTWList(oh.utcStart, oh.utcEnd, transmissionParameters.minGSWindowTime, int(inputParameters.hypsoNr))

# Create observation schedule
observationSchedule, bufferSchedule, downlinkSchedule, _, _, _, _ = runNSGA(
    int(inputParameters.populationSize),
    int(inputParameters.nsga2Runs),
    ttwList,
    gstwList,
    schedulingParameters,
    transmissionParameters,
    oh, 
    int(inputParameters.alnsRuns),
    bool(inputParameters.isTabooBankFIFO),
    bool(inputParameters.iqNonLinear),
    int(inputParameters.desNumber),
    int(inputParameters.maxTabBank)
)

bufferSchedule, downlinkSchedule = cleanUpSchedule(
    observationSchedule,
    bufferSchedule,
    downlinkSchedule,
    gstwList,
    transmissionParameters,
    OrderType.FIFO,
    OrderType.FIFO
)
saveplotPathCompare = os.path.join(os.path.dirname(__file__), f"output/{inputParameters.testName}_schedule")
plotSchedule(
    observationSchedule,
    observationSchedule,
    bufferSchedule,
    downlinkSchedule,
    gstwList,
    ttwList,
    transmissionParameters,
    savePlotPath=saveplotPathCompare
)

print(f"Priority objective value: {objectiveFunctionPriority(observationSchedule)}")
print(f"Image quality objective value: {objectiveFunctionImageQuality(observationSchedule, oh, schedulingParameters.hypsoNr)}")

### CREATE COMMAND LINES FOR SATELLITE CAPTURE AND BUFFERING ###

cmdLines = createCmdLinesForCaptureAndBuffering(observationSchedule, bufferSchedule, inputParameters, oh)
outputFolderPath = os.path.join(os.path.dirname(__file__), f"output/")
createCmdFile(f"{outputFolderPath}{inputParameters.testName}_cmdLines.txt", cmdLines)



### COMPARE SCRIPTS ###
pathScript = os.path.join(os.path.dirname(__file__), "output/cp_test.txt")

otList = recreateOTListFromCmdFile(pathScript, oh)
for ot in otList:
    print(f"Target ID: {ot.GT.id:10}, Start: {ot.start}")
print(f"Total number of observation tasks: {len(otList)}")  
for ot in observationSchedule:
    print(f"Target ID: {ot.GT.id:10}, Start: {ot.start}")
print(f"Total number of observation tasks: {len(observationSchedule)}")
saveplotPathCompare = os.path.join(os.path.dirname(__file__), f"output/{inputParameters.testName}_compare_schedule")

plotCompareSchedule(
    observationSchedule,
    otList,
    observationSchedule,
    bufferSchedule,
    downlinkSchedule,
    gstwList,
    ttwList,
    transmissionParameters,
    savePlotPath=saveplotPathCompare
)