import csv
import os
import datetime

from data_preprocessing.objective_functions import objectiveFunctionPriority, objectiveFunctionImageQuality
from scheduling_model import SP
from algorithm.NSGA2 import runNSGA
from data_preprocessing.create_data_objects import createTTWList, createOH, createGSTWList
from campaignPlanner_interaction.intergrate_campaign_planner import createCmdFile, createCmdLinesForCaptureAndBuffering, recreateOTListFromCmdFile

from transmission_scheduling.clean_schedule import cleanUpSchedule, OrderType
from transmission_scheduling.input_parameters import getTransmissionInputParams
from transmission_scheduling.two_stage_transmission_insert import twoStageTransmissionScheduling
from transmission_scheduling.util import plotSchedule, plotCompareSchedule



# Utility functions
def csvToDict(filepath) -> dict:
    """
    Reads a CSV file and returns a dictionary where each row's first column is the key and the second column is the value.
    Ignores rows starting with #.
    Output:
    - dict: dictionary with key-value pairs ( the first and second element of each row) from the CSV file
    """
    dict= {}
    with open(filepath, mode='r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
            if len(row) >= 2:
                key = row[0].strip()
                value = row[1].strip()
                dict[key] = value
    return dict


### Create the image schedule ####

groundStationFilePath = os.path.join(os.path.dirname(__file__), "data_input/HYPSO_data/ground_stations.csv")
inputParametersFilePath = os.path.join(os.path.dirname(__file__),"data_input/input_parameters.csv")
ttwListFilePath = os.path.join(os.path.dirname(__file__),"data_input/HYPSO_data/ttw_list.json")

inputParameters = csvToDict(inputParametersFilePath)

# # Check if start time is now
if inputParameters["startTimeOH"] == "now":
    inputParameters["startTimeOH"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

# Create model parameters
schedulingParameters = SP(
    int(inputParameters["maxCaptures"]), 
    int(inputParameters["captureDuration"]), 
    int(inputParameters["transitionTime"]),
    int(inputParameters["hypsoNr"]))
oh = createOH(datetime.datetime.fromisoformat(inputParameters["startTimeOH"]), int(inputParameters["durationInDaysOH"]))
transmissionParameters = getTransmissionInputParams(inputParametersFilePath)

# Create data Objects
ttwList = createTTWList( int(inputParameters["captureDuration"]), oh, int(inputParameters["hypsoNr"]), ttwListFilePath)
gstwList = createGSTWList(oh.utcStart, oh.utcEnd, transmissionParameters.minGSWindowTime, groundStationFilePath, int(inputParameters["hypsoNr"]))

# Create observation schedule
observationSchedule, _, _, _, _ = runNSGA(
    int(inputParameters["populationSize"]), 
    int(inputParameters["NSGA2Runs"]), 
    ttwList,
    gstwList,
    schedulingParameters,
    transmissionParameters,
    oh, 
    int(inputParameters["ALNSRuns"]), 
    bool(inputParameters["isTabooBankFIFO"]), 
    bool(inputParameters["iqNonLinear"]), 
    int(inputParameters["desNumber"]), 
    int(inputParameters["maxTabBank"])
)

# Sort the schedule by priority to indicate for which tasks buffering should be scheduled first
_, bufferSchedule, downlinkSchedule, modifiedObservationSchedule = twoStageTransmissionScheduling(
    observationSchedule,
    ttwList,
    gstwList,
    transmissionParameters
)

bufferSchedule, downlinkSchedule = cleanUpSchedule(
    modifiedObservationSchedule,
    bufferSchedule,
    downlinkSchedule,
    gstwList,
    transmissionParameters,
    OrderType.FIFO,
    OrderType.PRIORITY
)
saveplotPathCompare = os.path.join(os.path.dirname(__file__), f"output_folder/{inputParameters['testName']}_schedule")
plotSchedule(
    modifiedObservationSchedule,
    observationSchedule,
    bufferSchedule,
    downlinkSchedule,
    gstwList,
    ttwList,
    transmissionParameters,
    savePlotPath=saveplotPathCompare
)

print(f"Priority objective value: {objectiveFunctionPriority(modifiedObservationSchedule)}")
print(f"Image quality objective value: {objectiveFunctionImageQuality(modifiedObservationSchedule, oh, schedulingParameters.hypsoNr)}")

### CREATE COMMAND LINES FOR SATELLITE CAPTURE AND BUFFERING ###

cmdLines = createCmdLinesForCaptureAndBuffering(modifiedObservationSchedule, bufferSchedule, inputParameters, oh)
outputFolderPath = os.path.join(os.path.dirname(__file__), f"output_folder/")
createCmdFile(f"{outputFolderPath}{inputParameters['testName']}_cmdLines.txt", cmdLines)



### COMPARE SCRIPTS ###
pathScript = os.path.join(os.path.dirname(__file__), "output_folder/CP_output/cp_test.txt")

otList = recreateOTListFromCmdFile(pathScript, oh)
for ot in otList:
    print(f"Target ID: {ot.GT.id:10}, Start: {ot.start}")
print(f"Total number of observation tasks: {len(otList)}")  
for ot in modifiedObservationSchedule:
    print(f"Target ID: {ot.GT.id:10}, Start: {ot.start}")
print(f"Total number of observation tasks: {len(modifiedObservationSchedule)}")
saveplotPathCompare = os.path.join(os.path.dirname(__file__), f"output_folder/{inputParameters['testName']}_compare_schedule")

plotCompareSchedule(
    modifiedObservationSchedule,
    otList,
    observationSchedule,
    bufferSchedule,
    downlinkSchedule,
    gstwList,
    ttwList,
    transmissionParameters,
    savePlotPath=saveplotPathCompare
)