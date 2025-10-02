import csv
import os
import datetime

from scheduling_model import SP, GT
from algorithm.NSGA2 import runNSGA
from data_preprocessing.get_target_passes import getModelInput
from campaignPlanner_interaction.intergrate_campaign_planner import createCmdFile, createCmdLinesForCaptureAndBuffering

from transmission_scheduling.clean_schedule import cleanUpSchedule, OrderType
from transmission_scheduling.input_parameters import getTransmissionInputParams
from transmission_scheduling.two_stage_transmission_insert import twoStageTransmissionScheduling
from transmission_scheduling.util import plotSchedule


# Utility functions
def csvToDict(filepath):
    """
    Reads a CSV file and returns a dictionary where each row's first column is the key and the second column is the value.
    Ignores rows starting with #.
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



### RUN THE ALGORITHM ####

filePath_inputParameters = os.path.join(os.path.dirname(__file__),"data_input/input_parameters.csv")
inputParameters = csvToDict(filePath_inputParameters)
parametersFilePath = os.path.join(os.path.dirname(__file__),"data_input/input_parameters.csv")
inputParamsTransmission = getTransmissionInputParams(parametersFilePath)

# Check if start time is now
if inputParameters["startTimeOH"] == "now":
    inputParameters["startTimeOH"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

oh, ttwList, gstwList = getModelInput(
    int(inputParameters["captureDuration"]),
    int(inputParameters["durationInDaysOH"]),
    int(inputParameters["delayInHoursOH"]),
    int(inputParameters["hypsoNr"]),
    inputParamsTransmission.minGSWindowTime,
    (inputParameters["startTimeOH"]))
ttwlistCopy = ttwList.copy()
schedulingParameters = SP(
    int(inputParameters["maxCaptures"]), 
    int(inputParameters["captureDuration"]), 
    int(inputParameters["transitionTime"]))

schedule, _, _, _, _ = runNSGA(
    int(inputParameters["populationSize"]), 
    int(inputParameters["NSGA2Runds"]), 
    ttwList, 
    schedulingParameters, 
    oh, 
    int(inputParameters["ALNSRuns"]), 
    bool(inputParameters["isTabooBankFIFO"]), 
    bool(inputParameters["iqNonLinear"]), 
    int(inputParameters["desNumber"]), 
    int(inputParameters["maxTabBank"])
)

# Sort the schedule by priority to indicate for which tasks buffering should be scheduled first
schedule = sorted(schedule, key=lambda x: x.GT.priority, reverse=True)

_, bufferSchedule, downlinkSchedule, modifiedObservationSchedule = twoStageTransmissionScheduling(
    schedule,
    ttwList,
    gstwList,
    inputParamsTransmission
)

bufferSchedule, downlinkSchedule = cleanUpSchedule(
    modifiedObservationSchedule,
    bufferSchedule,
    downlinkSchedule,
    gstwList,
    inputParamsTransmission,
    OrderType.FIFO,
    OrderType.PRIORITY
)

plotSchedule(
    modifiedObservationSchedule,
    schedule,
    bufferSchedule,
    downlinkSchedule,
    gstwList,
    ttwList,
    inputParamsTransmission
)

## Create command lines for campaign planner

cmdLines = createCmdLinesForCaptureAndBuffering(modifiedObservationSchedule, bufferSchedule, inputParameters, oh)
createCmdFile(os.path.join(os.path.dirname(__file__), f"campaignPlanner_interaction/{inputParameters['testName']}_TargetsCmds.txt"), cmdLines)


# myScript = "campaignPlanner_interaction/campaign_scripts_h2_2025-09-26_mine.txt"
# campaignScript = "campaignPlanner_interaction/campaign_scripts_h2_2025-09-26.txt"
# fullPathMyScript= os.path.join(os.path.dirname(__file__),myScript)
# fullPathCampaignScript= os.path.join(os.path.dirname(__file__),campaignScript)

# priorities, uniqueCaptures = compareScripts(fullPathMyScript, fullPathCampaignScript)

# p_me, p_camp = priorities
# print(f"Sum of priorities - My script: {p_me}, Campaign script: {p_camp}")

# unique_me, unique_camp = uniqueCaptures
# print(f"Unique captures - My script: {unique_me}, \nCampaign script: {unique_camp}")

