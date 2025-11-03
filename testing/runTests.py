
import datetime
import os
import sys
import time
from contextlib import contextmanager

from test_scenario import TestScenario
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data_preprocessing.create_data_objects import createOH


@contextmanager
def timer(description="Operation"):
    start_time = time.time()
    print(f"{description} started...")
    try:
        yield
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"{description} completed in {execution_time:.2f} seconds ({execution_time/60:.2f} minutes)")


algorithmRuns = 1
# Path to the file containing the ground targets data
targetsFilePath_world = os.path.join(os.path.dirname(__file__),"../data_input/HYPSO_data/targets_world.json")
targetsFilePathEurope = os.path.join(os.path.dirname(__file__),"../data_input/HYPSO_data/targets_europe.json")

## Define test scenarios
scenarios = [
    # TestScenario(senarioID="g2", startOH="2025-11-04T13:00:00Z", algorithmRuns=algorithmRuns),
    # TestScenario(senarioID="g4", startOH="2025-11-04T13:00:00Z", algorithmRuns=algorithmRuns),
    # TestScenario(senarioID="g6", startOH="2025-11-04T13:00:00Z", algorithmRuns=algorithmRuns),
    TestScenario(senarioID="e2_v2", startOH="2025-11-04T13:00:00Z", algorithmRuns=algorithmRuns),
    TestScenario(senarioID="e4_v2", startOH="2025-11-04T13:00:00Z", algorithmRuns=algorithmRuns),
    TestScenario(senarioID="e6_v2", startOH="2025-11-04T13:00:00Z", algorithmRuns=algorithmRuns)
]

targetFiles = [
    # targetsFilePath_world,
    # targetsFilePath_world,
    # targetsFilePath_world,
    targetsFilePathEurope,
    targetsFilePathEurope,
    targetsFilePathEurope
]
OHdurations = [ 2, 4, 6]
maxCaptures = [ 25, 50, 75]

popsizes = [ 100, 100, 100]
alnsRuns = [ 50, 50, 50]


for scenario, i in zip(scenarios, range(len(scenarios))):
    
    
    # Get input attributes from correct target file
    scenario.createInputAttributes(os.path.join(os.path.dirname(__file__),"../data_input/input_parameters.csv"), targetFiles[i])
    
    # Set OP duration and maxCaptures in input parameters
    input = scenario.getInputParameters()
    input.durationInDaysOH = OHdurations[i]
    input.maxCaptures = maxCaptures[i]
    input.populationSize = popsizes[i]
    input.ALNSRuns = alnsRuns[i]
    scenario.setInputParameters(input)

    # Update all data input attributes
    scenario.updateInputAttributes()

    print(f"Scenario OH{scenario.senarioID} start time: {scenario.getOh().utcStart}, end time: {scenario.getOh().utcEnd}")
    # Run Greedy algorithm 
    scenario.runGreedyAlgorithm()
    
    # Run ALNS + NSGA-II algorithm
    with timer(f"Scenario OH{scenario.senarioID}"):
        scenario.runTestScenario()


# #Analyse tests
for scenario in scenarios:
    otLists = scenario.getObservationSchedules()
    schedulePriorities = [sum(ot.GT.priority for ot in otList) for otList in otLists]
    obVals = scenario.getAllObjectiveValues()
    print(f"Scenario OH{scenario.senarioID}: Best run is run number {schedulePriorities.index(max(schedulePriorities))} with total priority {max(schedulePriorities)}")