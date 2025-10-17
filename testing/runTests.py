
import os
import sys
import json
import datetime

from test_scenario import TestScenario
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from campaignPlanner_interaction.intergrate_campaign_planner import recreateOTListFromCmdFile, getTargetIdPriorityDictFromJson
from scheduling_model import OH


algorithmRuns = 20

## Define test scenarios
scenarios = [
    TestScenario(SenarioID="H2Mission_17-10", startOH="2025-10-17T13:05:00Z", algorithmRuns=algorithmRuns),
]

## Run test scenarios
print(f"Running a total of {len(scenarios)} test scenarios...")
# for scenario in scenarios:
#     print(f"Scenario OH{scenario.SenarioID} starting at {scenario.startOH} with {scenario.algorithmRuns} algorithm runs")
#     scenario.createInputFiles(
#         os.path.join(os.path.dirname(__file__),"../data_input/input_parameters.csv"), 
#         os.path.join(os.path.dirname(__file__), "../data_input/HYPSO_data/ground_stations.csv")
#     )
#     scenario.runTestScenario()


#Analyse tests

#Recreate oh from json file
pathOHFile = os.path.join(os.path.dirname(__file__), f"OHH2Mission_17-10/oh.json")
with open(pathOHFile, "r") as f:
    ohData = json.load(f)

oh = OH(
    utcStart = datetime.datetime.fromisoformat(ohData["utcStart"].replace('Z', '+00:00')),
    utcEnd = datetime.datetime.fromisoformat(ohData["utcEnd"].replace('Z', '+00:00'))
)

schedules = []
targetPriorityDict = getTargetIdPriorityDictFromJson(os.path.join(os.path.dirname(__file__), "../data_input/HYPSO_data/targets.json"))
for runNr in range(algorithmRuns):
    pathScript = os.path.join(os.path.dirname(__file__), f"OHH2Mission_17-10/output/{runNr}_cmdLines.txt")
    otList = recreateOTListFromCmdFile(pathScript, oh)

    for ot in otList:
        ot.GT.priority = targetPriorityDict.get(ot.GT.id, 0)

    schedules.append(otList)

# Find sum of priorities for each schedule


