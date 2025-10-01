import csv
import os
import datetime

import data_postprocessing.algorithmData_api as AD_api
from scheduling_model import SP, GT
from algorithm.NSGA2 import runNSGA
from data_preprocessing.get_target_passes import getModelInput
from campaignPlanner_interaction.intergrate_campaign_planner import createCmdFile, createCaptureCmdLine, createBufferCmdLine, convertScheduleToDateTime
from data_postprocessing.quaternions import generate_quaternions
from data_input.satellite_positioning_calculations import createSatelliteObject, findSatelliteTargetElevation
from campaignPlanner_interaction.compareSchedules  import captureScriptVsCampaignScript, compareScripts


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
def calculateQuaternions(hypsoNr: int, groundTarget: GT, timestamp: datetime.datetime):

    quaternions = {}

    satellite_skf = createSatelliteObject(hypsoNr)
    elevation = findSatelliteTargetElevation(float(groundTarget.lat), float(groundTarget.long), timestamp, hypsoNr)
    q = generate_quaternions(satellite_skf, timestamp, float(groundTarget.lat), float(groundTarget.long), elevation)

    quaternions['r'] = q[0]
    quaternions['l'] = q[1]
    quaternions['j'] = q[2]
    quaternions['k'] = q[3]

    return quaternions


### RUN THE ALGORITHM ####

filePath_inputParameters = os.path.join(os.path.dirname(__file__),"data_input/input_parameters.csv")
inputParameters = csvToDict(filePath_inputParameters)

# Check if start time is now
if inputParameters["startTimeOH"] == "now":
    inputParameters["startTimeOH"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

oh, ttwList = getModelInput(
    int(inputParameters["captureDuration"]),
    int(inputParameters["durationInDaysOH"]),
    int(inputParameters["delayInHoursOH"]),
    int(inputParameters["hypsoNr"]),
    (inputParameters["startTimeOH"]))

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

schedule_dt = convertScheduleToDateTime(schedule, oh)
cmdLines = []
for ot in schedule_dt:
    groundTarget = ot.GT
    quaternions = calculateQuaternions(int(inputParameters["hypsoNr"]), groundTarget, ot.start)
    newCommandLine = createCaptureCmdLine(ot, int(inputParameters["hypsoNr"]), quaternions)
    cmdLines.append(newCommandLine)

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

