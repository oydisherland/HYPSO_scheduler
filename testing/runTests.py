
import os
import sys

from test_scenario import TestScenario
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



algorithmRuns = 4

## Define test scenarios
scenarios = [
    TestScenario(SenarioID="H2Mission_17-10", startOH="2025-10-17T13:05:00Z", algorithmRuns=algorithmRuns),
]

# Run test scenarios
print(f"Running a total of {len(scenarios)} test scenarios...")
for scenario in scenarios:
    print(f"Scenario OH{scenario.SenarioID} starting at {scenario.startOH} with {scenario.algorithmRuns} algorithm runs")
    # scenario.createInputFiles(
    #     os.path.join(os.path.dirname(__file__),"../data_input/input_parameters.csv"), 
    #     os.path.join(os.path.dirname(__file__), "../data_input/HYPSO_data/ground_stations.csv")
    # )
    scenario.recreateInputAttributes()
    scenario.runTestScenario()


#Analyse tests


for scenario in scenarios:
    scenario.recreateTestScenario()

    otLists = scenario.getOtLists()
    schedulePriorities = [sum(ot.GT.priority for ot in otList) for otList in otLists]
    obVals = scenario.getAllObjectiveValues()
    print(f"Scenario OH{scenario.SenarioID}: Best run is run number {schedulePriorities.index(max(schedulePriorities))} with total priority {max(schedulePriorities)}")
    print(f"Compared to the stores objective values: {obVals[schedulePriorities.index(max(schedulePriorities))]}")
