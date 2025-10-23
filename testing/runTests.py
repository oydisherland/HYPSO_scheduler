
import os
import sys

from test_scenario import TestScenario
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



algorithmRuns = 1

## Define test scenarios
scenarios = [
    TestScenario(senarioID="test", startOH="2025-10-23T13:00:00Z", algorithmRuns=algorithmRuns),
]
capturesMax = [26]

# Run test scenarios
print(f"Running a total of {len(scenarios)} test scenarios...")
for scenario, maxC in zip(scenarios, capturesMax):
    print(f"Scenario OH{scenario.senarioID} starting at {scenario.startOH} with {scenario.algorithmRuns} algorithm runs")
    scenario.createInputAttributes(
        os.path.join(os.path.dirname(__file__),"../data_input/input_parameters.csv"), 
        os.path.join(os.path.dirname(__file__), "../data_input/HYPSO_data/ground_stations.csv")
    )
    #scenario.recreateInputAttributes()
    # ip = scenario.getInputParameters()
    # ip.maxCaptures = maxC
    # scenario.setInputParameters(ip)
    #
    scenario.runTestScenario()


# #Analyse tests
for scenario in scenarios:
    scenario.recreateTestScenario()

    otLists = scenario.getObservationSchedules()
    schedulePriorities = [sum(ot.GT.priority for ot in otList) for otList in otLists]
    obVals = scenario.getAllObjectiveValues()
    print(f"Scenario OH{scenario.senarioID}: Best run is run number {schedulePriorities.index(max(schedulePriorities))} with total priority {max(schedulePriorities)}")
    print(f"Compared to the stores objective values: {obVals[schedulePriorities.index(max(schedulePriorities))]}")
