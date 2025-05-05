import csv
import numpy as np
import ast
import json
import time

from NSGA2 import runNSGA, findKneePoint
from get_target_passes import getModelInput
from scheduling_model import SP, OH, OT, GT
from visualize_schedual import createPlotSchedual, createPlotObjectiveSpace, createPlotKneePointHistogram

def runAlgFormatResults(testName: str,
                        ttwList: list,
                        oh: OH,
                        destructionRate: float,
                        maxSizeTabooBank: int,
                        printResults = True, 
                        saveToFile = True,
                        nRuns: int=3,
                        popSize: int=20,
                        schedulingParameters: SP = SP(20, 60, 90), 
                        ohDurationInDays: int = 2, 
                        ohDelayInHours: int = 2,
                        hypsoNr: int = 1):
    
    start_time = time.time()

    printArray, bestSolution, bestIndex, population = runNSGA(popSize, nRuns, ttwList, schedulingParameters, oh, destructionRate=destructionRate, maxSizeTabooBank=maxSizeTabooBank)

    end_time = time.time()
    NSGArunTime = end_time - start_time
    
    kneePoints = []
    for iteration in range(len(printArray)):
        fronts, objectiveSpace, selectedObjectiveVals = printArray[iteration]
        kneePoint_sub, _ = findKneePoint(fronts, objectiveSpace)
        kneePoints.append(kneePoint_sub)

    

    fronts, objectiveSpace, selectedObjectiveVals = printArray[-1]
    print(f"Best solution: {bestSolution}")

    ### Create plots and save to file
    plotObjectiveSpace_filename = f"results/plots/OS_{testName}.pdf"
    createPlotObjectiveSpace(fronts, objectiveSpace, selectedObjectiveVals, plotObjectiveSpace_filename, printResults)
    plotSchedual_filename = f"results/plots/S_{testName}.pdf"
    try:
        createPlotSchedual(population[bestIndex].schedual, plotSchedual_filename, printResults)
    except IndexError:
        print(f"BestIndex = {bestIndex} is out of range for population of size {len(population)}")

    plotKneePoints_filename = f"results/plots/KP_{testName}.pdf"
    createPlotKneePointHistogram(kneePoints, plotKneePoints_filename, printResults)

    
    if not saveToFile:
        # End function here without saving results
        return
    
    # Save parameter data from the run to csv file
    testData_filename = f"results/testData/TD_{testName}.csv"
    with open(testData_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Observation Horizon (start/end): ", oh.utcStart, oh.utcEnd])
        writer.writerow(["Scheduling Parameters (maxCaptures, captureDuration, transitionTime): ", schedulingParameters.maxCaptures, schedulingParameters.captureDuration, schedulingParameters.transitionTime])
        writer.writerow(["Sat model input data (ohDurationDays, ohDelayHours, HypsoNr): ", ohDurationInDays, ohDelayInHours, hypsoNr])
        writer.writerow(["Population size: ", popSize])
        writer.writerow(["Number of runs main loop: ", nRuns])
        writer.writerow(["Runtime: ", NSGArunTime])

    ### Save all scheduals to json file
    serializable_schedualsFinalPop = []
    for i in range(len(population)//2):
        # Add the schedual parent and the schedual child after eachother
        parent = population[i].schedual
        child = population[i + len(population)//2].schedual
        serializable_induvidual = []
        for row in parent:
            serializable_induvidual.append({
                "Ground Target": row[0],
                "Start Time": row[1], 
                "End Time": row[2]  
            })
        serializable_schedualsFinalPop.append(serializable_induvidual)
        serializable_induvidual.clear()
        for row in child:
            serializable_induvidual.append({
                "Ground Target": row[0],
                "Start Time": row[1], 
                "End Time": row[2]  
            })
        serializable_schedualsFinalPop.append(serializable_induvidual)

    schedualsFinalPop_filename = f"results/schedual/SFP_{testName}.json"
    with open(schedualsFinalPop_filename, mode='w') as file:
        json.dump(serializable_schedualsFinalPop, file, indent=4)

    ### Save best schedual to json file
    bestSchedual_filename = f"results/schedual/BS_{testName}.json"
    serializable_schedual = [
        {"Ground Target": row[0], "Start Time": row[1], "End Time": row[2]} for row in population[bestIndex].schedual
    ]

    with open(bestSchedual_filename, mode='w') as file:
        json.dump(serializable_schedual, file, indent=4)

    ### Save fronts, objectiveSpace, and selectedIbjectiveVals and kneepoint to json file
    json_filename = f"results/algorithmData/AD_{testName}.json"
    serializable_printArray = []
    for i in range(len(printArray)):
        fronts, objectiveSpace, selectedObjectiveVals = printArray[i]
        serializable_printArray.append({
            "fronts": [front.tolist() for front in fronts],  # Convert NumPy arrays to lists
            "objectiveSpace": [obj.tolist() for obj in objectiveSpace],  # Convert NumPy arrays to lists
            "selectedObjectiveVals": [val.tolist() for val in selectedObjectiveVals],  # Convert NumPy arrays to lists
            "kneePoint": kneePoints[i].tolist()  # Convert NumPy array to list
        })

    with open(json_filename, mode='w') as file:
        json.dump(serializable_printArray, file, indent=4)



def evaluateAlgorithmData(algData_filename: str):
    """ Evaluate the algorithm data and recreate printArray from the JSON file """
    # Load the algorithm data from the JSON file

    with open(algData_filename, mode='r') as file:
        serialized_data = json.load(file)

    # Reconstruct printArray from the serialized data
    algData = []
    for entry in serialized_data:
        fronts = [np.array(front) for front in entry["fronts"]]  # Convert lists back to NumPy arrays
        objectiveSpace = [np.array(obj) for obj in entry["objectiveSpace"]]  # Convert lists back to NumPy arrays
        selectedObjectiveVals = [np.array(val) for val in entry["selectedObjectiveVals"]]  # Convert lists back to NumPy arrays
        kneePoints = [np.array(point) for point in entry["kneePoint"]]  # Convert lists back to NumPy arrays
        algData.append((fronts, objectiveSpace, selectedObjectiveVals, kneePoints))

    # Reconstruct Kneepoints from the serialized data
    # kneePoints = [np.array(entry["kneePoint"]) for entry in serialized_data]

    return algData

def evaluateSchedualsFinalPop(schedual_filename: str):
    """ Evaluate the schedual and recreate printArray from the JSON file """
    # Load the schedual data from the JSON file

    with open(schedual_filename, mode='r') as file:
        serialized_schedual = json.load(file)

    schedualsFinalPop = []
    for individSchedual in serialized_schedual:
        
        # Reconstruct schedual from the serialized data
        schedualData = [(entry["Ground Target"], entry["Start Time"], entry["End Time"]) for entry in individSchedual]
        schedual = []
        for i in range(len(schedualData)):
            groundTarget = schedualData[i][0]
            gt = GT(
                id = groundTarget[0],
                lat = float(groundTarget[1]),
                long = float(groundTarget[2]),
                priority = int(groundTarget[3]),
                idealIllumination = int(groundTarget[4])
            )

            scheduledOT = OT(
                GT = gt,
                start = float(schedualData[i][1]),
                end = float(schedualData[i][2])
            )
            schedual.append(scheduledOT)
        schedualsFinalPop.append(schedual)

    return schedualsFinalPop


def evaluateBestSchedual( schedual_filename: str):
    """ Evaluate the schedual and recreate printArray from the JSON file """
    # Load the schedual data from the JSON file

    with open(schedual_filename, mode='r') as file:
        serialized_schedual = json.load(file)

    # Reconstruct schedual from the serialized data
    schedualData = [(entry["Ground Target"], entry["Start Time"], entry["End Time"]) for entry in serialized_schedual]
    schedual = []
    for i in range(len(schedualData)):
        groundTarget = schedualData[i][0]
        gt = GT(
            id = groundTarget[0],
            lat = float(groundTarget[1]),
            long = float(groundTarget[2]),
            priority = int(groundTarget[3]),
            idealIllumination = int(groundTarget[4])
        )

        scheduledOT = OT(
            GT = gt,
            start = float(schedualData[i][1]),
            end = float(schedualData[i][2])
        )
        schedual.append(scheduledOT)

    return schedual



#Variables that say fixed during all tests
schedulingParameters = SP(40, 60, 90)
startTime = "2025-04-01 16:47:49.990785"
ohDurationInDays, ohDelayInHours, hypsoNr = 2, 2, 1


oh, ttwList = getModelInput(schedulingParameters.captureDuration, ohDurationInDays, ohDelayInHours, hypsoNr, startTime)

#### RUN THE TEST ####
#Variables that change during different tests
popSize = 20
nsgaRunds = 40
desRate = 0.4
maxTabBank = 15

RepetedRuns = 10

for i in range(RepetedRuns):
    runAlgFormatResults(
        testName = f"test2-run{i}",
        ttwList = ttwList,
        oh = oh,
        destructionRate = desRate, 
        maxSizeTabooBank = maxTabBank,
        printResults = False, 
        saveToFile = True,
        nRuns = nsgaRunds,
        popSize = popSize
    )


# evaluateAlgorithmData("test1")
# evaluateSchedualsFinalPop("test1")
# evaluateBestSchedual("test1")



"""
How to present the result of the algorithm
- Objective values of the best solution
- Objective values of the Pareto front
- Schedual of the best solution
- Runtime
- Objective values of best solution after each main loop iteration 

Input data: 
- Max Runs in main loop
- Population size
- Max captures 

"""


 