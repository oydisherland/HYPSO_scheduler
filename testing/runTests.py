
import os
import sys
import time
from contextlib import contextmanager
from test_scenario import TestScenario
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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


id = "missionPlanning_29-10"
start = "2025-10-29T15:00:00Z"

## Define test scenarios
scenario= TestScenario(senarioID=id, startOH=start, algorithmRuns=1)


print(f"Scenario OH{scenario.senarioID} starting at {scenario.startOH}")
scenario.createInputAttributes(
    os.path.join(os.path.dirname(__file__),"../data_input/input_parameters.csv"), 
)
scenario.runGreedyAlgorithm()
with timer(f"Scenario OH{scenario.senarioID}"):
    scenario.runTestScenario()


# #Analyse tests

otLists = scenario.getObservationSchedules()
schedulePriorities = [sum(ot.GT.priority for ot in otList) for otList in otLists]
obVals = scenario.getAllObjectiveValues()
print(f"Scenario OH{scenario.senarioID}: Best run is run number {schedulePriorities.index(max(schedulePriorities))} with total priority {max(schedulePriorities)}")