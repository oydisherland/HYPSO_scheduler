import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import json
import time

from NSGA2 import runNSGA, findKneePoint
from scheduling_model import SP, OH, OT, GT, TTW, TW
from visualize_schedual import createPlotSchedual, createPlotObjectiveSpace, createPlotKneePointHistogram 
from get_target_passes import getModelInput
from optimizeSchedule import checkFeasibility, improveIQ, findMaxPriority
from objective_functions import objectiveFunctionImageQuality
from scheduling_model import SP
from rhga import RHGA
from operators import greedyPrioritySort


def runGreedyAlgorithm(ttwList, oh, schedulingParameters):
    otList = []
    unfeasibleTargets = []
    ttwListSorted = greedyPrioritySort(ttwList)
    schedule, objectiveVals = RHGA(ttwListSorted, otList, unfeasibleTargets ,schedulingParameters, oh, False, True)

    optimizedSchedule, _, hasChanged = improveIQ(schedule, ttwList, oh, schedulingParameters)
    if hasChanged:
        print("Greedy schedule was improved")
        return optimizedSchedule, objectiveVals
    else:
        return schedule, objectiveVals
    
    
# from analyseResults
def plotCompareKneePoints(testnr: list, nRuns: int):
    """
    Compare the kneepoints of the differents tests, each test  .
    """

    plt.figure(figsize=(10, 6))

    for i, test in enumerate(testnr):
        colormap = plt.get_cmap('viridis', len(testnr))
        bestSolutionsForOneTest = []
        for run in range(nRuns):
            algDataFileName = f"results/test{test}/algorithmData/AD_test{test}-run{run}.json"
            algData = evaluateAlgorithmData(algDataFileName)
            bestSolution = algData[-1][-1]
            bestSolutionsForOneTest.append(bestSolution)

        # Extract x and y values from the kneePoints list
        x_values = [point[0] for point in bestSolutionsForOneTest]  # First dimension of each knee point
        y_values = [point[1] for point in bestSolutionsForOneTest]  # Second dimension of each knee point

        # Plot the knee points
        plt.scatter(x_values, y_values, color=colormap(i), marker='o', label=f'Test {test}')
    

    # Add labels, title, and grid
    plt.xlabel('Sum of priorities', fontsize=12)
    plt.ylabel('Image quality', fontsize=12)
    title = [f"{test} " for test in testnr]
    plt.title(f"Best solutions for tests: {title}", fontsize=14)
    plt.grid(True)
    plt.legend(loc='upper right', fontsize=10)

    # Save or display the plot
    plt.tight_layout()
    plt.show()
    plt.close()
def calculateMeanAndStd(testnr: list, nRuns: int, plot: bool):
    
    ObjectiveP = []
    ObjectiveIQ = []
    meanPopP = []
    meanPopIQ = []

    for test in testnr:
        bestSolutionsForOneTest = []
        variancePopP = []
        variancePopIQ = []

        for run in range(nRuns):
            algDataFileName = f"results/test{test}/algorithmData/AD_test{test}-run{run}.json"
            algData = evaluateAlgorithmData(algDataFileName)
            bestSolution = algData[-1][-1]
            bestSolutionsForOneTest.append(bestSolution)

            finalPopulation = algData[-1][1]
            ObjectiveP_pop = []
            ObjectiveIQ_pop = []
            for individual in finalPopulation:
                ObjectiveP_pop.append(individual[0])
                ObjectiveIQ_pop.append(individual[1])
            variancePopP.append(np.std(ObjectiveP_pop, axis=None))
            variancePopIQ.append(np.std(ObjectiveIQ_pop, axis=None))

        # Extract objective values from the kneePoints list
        ObjectiveP.append([point[0] for point in bestSolutionsForOneTest])
        ObjectiveIQ.append([point[1] for point in bestSolutionsForOneTest])

        #Calculate the mean of the population variance
        meanPopP = np.mean(variancePopP, axis=None)
        meanPopIQ = np.mean(variancePopIQ, axis=None)

    
    meanObjectiveP = np.mean(ObjectiveP, axis=None)
    meanObjectiveIQ = np.mean(ObjectiveIQ, axis=None)
    stdObjectiveP = np.std(ObjectiveP, axis=None)
    stdObjectiveIQ = np.std(ObjectiveIQ, axis=None)
    
    # Plotting the results
    if plot:
        plotObjectiveHistogram(ObjectiveP)
        plotObjectiveHistogram(ObjectiveIQ)
    bestSolMeanAndStd = [meanObjectiveP, stdObjectiveP, meanObjectiveIQ, stdObjectiveIQ]
    popMean = [meanPopP, meanPopIQ]


    return bestSolMeanAndStd, popMean

def plotObjectiveHistogram(Objective):
    """
    Plots a histogram based on the values in ObjectiveP.
    The y-axis represents the frequency of each bin,
    and the x-axis represents the values in ObjectiveP.
    """
    # Flatten ObjectiveP if it's a 2D list
    Objective_flat = np.array(Objective).flatten()

    # Create the histogram
    plt.figure(figsize=(10, 6))
    plt.hist(Objective_flat, bins=10, color='blue', alpha=0.7, edgecolor='black')

    # Add labels, title, and grid
    plt.xlabel('Objective Value', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title('Histogram of Objective Value', fontsize=14)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Show the plot
    plt.tight_layout()
    plt.show()
    plt.close()
def plotEllipticalBubble(meanObjectiveP, meanObjectiveIQ, stdObjectiveP, stdObjectiveIQ, testLabels):
    """
    Creates an elliptical bubble plot.
    - x-axis: meanObjectiveP
    - y-axis: meanObjectiveIQ
    - x-radius: stdObjectiveP
    - y-radius: stdObjectiveIQ
    """
    plt.figure(figsize=(10, 6))
    colormap = plt.get_cmap('viridis', len(meanObjectiveP))
    # Loop through each test and plot an ellipse
    for i in range(len(meanObjectiveP)):
        ellipse = Ellipse(
            (meanObjectiveP[i], meanObjectiveIQ[i]),  # Center of the ellipse
            width=0.5 * stdObjectiveP[i],              # Width (2 * std for x-radius)
            height=0.5 * stdObjectiveIQ[i],            # Height (2 * std for y-radius)
            alpha=0.5,                               # Transparency
            edgecolor='black',                       # Border color
            facecolor=colormap(i)                         # Fill color
        )
        plt.gca().add_patch(ellipse)  # Add the ellipse to the plot
        plt.text(meanObjectiveP[i], meanObjectiveIQ[i], testLabels[i], fontsize=10, ha='center')

    # Add labels, title, and grid
    plt.xlabel('Mean Objective Priority', fontsize=12)
    plt.ylabel('Mean Objective Image Quality', fontsize=12)
    plt.title('Elliptical Bubble Plot', fontsize=14)
    plt.grid(True)

    # Set axis limits for better visualization
    plt.xlim(min(meanObjectiveP) - max(stdObjectiveP), max(meanObjectiveP) + max(stdObjectiveP))
    plt.ylim(min(meanObjectiveIQ) - max(stdObjectiveIQ), max(meanObjectiveIQ) + max(stdObjectiveIQ))

    # Show the plot
    plt.tight_layout()
    plt.show()

# Functions that read data from json files and recreate the original data structure
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
def evaluateBSTTW(ttwList_filename: str):
    """ Evaluate the ttwList and recreate printArray from the JSON file """
    # Load the ttwList data from the JSON file

    with open(ttwList_filename, mode='r') as file:
        serialized_ttwList = json.load(file)

    # Reconstruct ttwList from the serialized data
    ttwList = []
    for entry in serialized_ttwList:
        groundTarget = entry["Ground Target"]
        gt = GT(
            id = groundTarget[0],
            lat = None,
            long = None,
            priority = groundTarget[1],
            idealIllumination = None
        )
        tws = []
        for tw in entry["Time Windows"]:
            tws.append(TW(float(tw["start"]), float(tw["end"])))
        ttwList.append(TTW(gt, tws))

    return ttwList

# Functions to evaluate data
def schedualedTargetsHistogram(testnr: str, repeatedRuns: int, savetoFile: bool, printPlot: bool):
    """
    This function creates a histogram of the scheduled targets from the given filename.
    It extracts the scheduled targets from the file and counts their occurrences.
    """
    ## Extract all scheduals from the seperate runs
    scheduals = []
    for i in range(repeatedRuns):
        filename_BS = f"results/test{testnr}/schedual/BS_test{testnr}-run{i}.json"
        scheduals.append(evaluateBestSchedual(filename_BS))


    ## Evaluates the similarities between the scheduals
    schedualedTaregts = {}
    for schedual in scheduals:
        for target in schedual:
            if target.GT.id not in schedualedTaregts:
                schedualedTaregts[target.GT.id] = 1
                continue
            schedualedTaregts[target.GT.id] += 1


    # Sort the dictionary by values in descending order
    sorted_targets = sorted(schedualedTaregts.items(), key=lambda item: item[1], reverse=True)

    # Extract sorted keys and values
    x_values = [item[0] for item in sorted_targets]  # Sorted keys for the x-axis
    y_values = [item[1] for item in sorted_targets]  # Sorted values for the y-axis

    plt.figure(figsize=(10, 6))
    plt.bar(x_values, y_values, color='blue', alpha=0.7)
    plt.xlabel('Scheduled Targets', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title('Histogram of Scheduled Targets', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()  
    if savetoFile:
        plt.savefig(f"results/test{testnr}/plots/analyse/schedualedTargetsHistogram.pdf", format='pdf', dpi=300) 
    if printPlot:
        plt.show()
    plt.close()
def objectiveSpaceHistogram(testnr: str, repeatedRuns: int, savetoFile: bool, printPlot: bool):
    """
    This function creates a histogram of the objective space from the given filename.
    It extracts the objective space from the file and counts their occurrences.
    """
    ## Extract all scheduals from the seperate runs
    kneePoints = []
    allChangesInPF = []
    for runNr in range(repeatedRuns):
        paretoFrontEvolution = []
        changesInParetoFront = []
        filename_AD = f"results/test{testnr}/algorithmData/AD_test{testnr}-run{runNr}.json"
        algData = evaluateAlgorithmData(filename_AD)

        ### Evaluate the evolution of the pareto front
        for nsgaLoopNr in range(len(algData)):

            fronts, objectiveSpace, _,_ = algData[nsgaLoopNr]
            pf = fronts[0] #paretofront of the current loop

            pfSolutions = [objectiveSpace[i] for i in pf]
            if paretoFrontEvolution:  # Ensure paretoFrontEvolution is not empty
                pfSolutions_tuples = {tuple(solution) for solution in pfSolutions}
                lastParetoFront_tuples = {tuple(solution) for solution in paretoFrontEvolution[-1]}
                commonSolutions = len(pfSolutions_tuples.intersection(lastParetoFront_tuples))
                changesInParetoFront.append(abs(len(pfSolutions)-commonSolutions))

            paretoFrontEvolution.append(pfSolutions)
        plotname = f"run{runNr}"
        plotChangesInParetoFront(changesInParetoFront, testnr, plotname, savetoFile, printPlot)
        plotParetoFrontEvolution(paretoFrontEvolution, testnr, plotname, savetoFile, printPlot)

        kneePointBestSolution = algData[-1][-1]
        kneePoints.append(kneePointBestSolution)
        allChangesInPF.append(changesInParetoFront)

    ### Evaluate the final knee point in all induviduals in population
    plotKneePoints(kneePoints, testnr, savetoFile, printPlot)
    return allChangesInPF
def saveResultsToFile(testnr: str, repeatedRuns: int, savetoFile: bool, printPlot: bool, changesInParetoFront: list):
    
    kneePointMeanAndStd, finalPopMedianOfStd = calculateMeanAndStd([testnr], repeatedRuns, plot=False)
    
    # find Median and std of knee points form all runs in the current test
    medianPriority, stdPriority, medianIQ, stdIQ = kneePointMeanAndStd
    kneePointsMedian = [round(medianPriority, 2), round(medianIQ, 2)]
    kneePointsStd = [round(stdPriority, 2), round(stdIQ, 2)]
    
    # find the median of the std of the final population
    finalPopMedianOfStd = [round(finalPopMedianOfStd[0], 2), round(finalPopMedianOfStd[1], 2)]

    nrOfChangesInPFLastHalf = []
    runtime = []
    for i in range(repeatedRuns):
        #Summerize how mush the pareto front has chnaged over the last half of the NSGA iterations
        halfLength = len(changesInParetoFront) // 2
        chenges = sum(changesInParetoFront[i][halfLength:])
        nrOfChangesInPFLastHalf.append(chenges)

        # Extract the runtime
        testName = f"test{testNumber}-run{i}"
        testData_filepath = f"results/test{testNumber}/testData/TD_{testName}.csv"
        try:
            # Open and read the CSV file
            with open(testData_filepath, mode='r') as file:
                reader = csv.reader(file)
                for row in reader:
                    # Check if the row contains the "Runtime" label
                    if row[0].strip() == "Runtime:":
                        runtime.append(float(row[1]))
        except FileNotFoundError:
            print(f"File not found: {testData_filepath}")
        except Exception as e:
            print(f"An error occurred: {e}")
    nrOfChangesInPFLastHalfMedian = round(np.median(nrOfChangesInPFLastHalf), 2)
    runtimeMedian = round(np.median(runtime), 2)

    # Save the data to a CSV file
    testPlan_filename = f"results/testPlan/test{testnr}.csv"
    with open(testPlan_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Evaluation Method", "Value (priority)", "Value(image quality)"])  # Header row
        writer.writerow(["Knee points median", kneePointsMedian[0], kneePointsMedian[1]])
        writer.writerow(["Knee points std", kneePointsStd[0], kneePointsStd[1]])
        writer.writerow(["Final pop median of std", finalPopMedianOfStd[0], finalPopMedianOfStd[1]])
        writer.writerow(["Changes in PF last half", nrOfChangesInPFLastHalfMedian])
        writer.writerow(["Runtime median", runtimeMedian])

#Function to create plots
def plotKneePoints(kneePoints, testnr: str, savetoFile: bool, printPlot: bool):
    """
    Plots the kneePoints list, where each element corresponds to a dot in a 2D plot.
    Each element in the kneePoints list is a 2D array.
    """
    plt.figure(figsize=(10, 6))

    # Extract x and y values from the kneePoints list
    x_values = [point[0] for point in kneePoints]  # First dimension of each knee point
    y_values = [point[1] for point in kneePoints]  # Second dimension of each knee point

    # Plot the knee points
    plt.scatter(x_values, y_values, color='red', marker='o', label='Knee Points')

    # Add labels, title, and grid
    plt.xlabel('Objective 1', fontsize=12)
    plt.ylabel('Objective 2', fontsize=12)
    plt.title('Knee Points', fontsize=14)
    plt.grid(True)

    # Save or display the plot
    plt.tight_layout()
    if savetoFile:
        plt.savefig(f"results/test{testnr}/plots/analyse/kneePoints.pdf", format='pdf', dpi=300)
    if printPlot:
        plt.show()
    plt.close()
def plotChangesInParetoFront(changesInParetoFront, testnr: str, plotname: str, savetoFile: bool, printPlot: bool):
    """
    Plots the changes in Pareto Front solutions over NSGA iterations.
    The x-axis represents the NSGA iteration, and the y-axis represents the number of common solutions.
    """
    plt.figure(figsize=(10, 6))

    # Create the x-axis values (indices of the list)
    x_values = list(range(len(changesInParetoFront)))

    # Plot the data
    plt.plot(x_values, changesInParetoFront, marker='o', color='blue', label='Solution Changes')

    # Add labels, title, and grid
    plt.xlabel('NSGA Iteration', fontsize=12)
    plt.ylabel('Solution Changes in Pareto Front', fontsize=12)
    plt.title('Changes in Pareto Front Over Iterations', fontsize=14)
    plt.xticks(ticks=x_values)
    y_min, y_max = min(changesInParetoFront), max(changesInParetoFront)
    plt.yticks(ticks=list(range(y_min, y_max + 1)))
    plt.tight_layout()
    
    if savetoFile:
        plt.savefig(f"results/test{testnr}/plots/analyse/changesInParetoFront_{plotname}.pdf", format='pdf', dpi=300) 
    if printPlot:
        plt.show()

    plt.close()
def plotParetoFrontEvolution(paretoFrontEvolution, testnr: str, plotname: str, savetoFile: bool, printPlot: bool):
    """
    Plots each item in paretoFrontEvolution[i] as dots in a 2D plot.
    The dots start as blue for i=0 and gradually transition to red for i > 0.
    """
    plt.figure(figsize=(10, 6))

    # Normalize the color gradient based on the number of iterations
    num_iterations = len(paretoFrontEvolution)
    color_gradient = np.linspace(0, 1, num_iterations)  # Values from 0 (blue) to 1 (red)

    for i, paretoFront in enumerate(paretoFrontEvolution):
        # Extract x and y values from the current paretoFront
        x_values = [solution[0] for solution in paretoFront]  # First objective
        y_values = [solution[1] for solution in paretoFront]  # Second objective

        # Define the color for the current iteration
        color = (color_gradient[i], 0, 1 - color_gradient[i])  # RGB: Transition from blue to red

        # Plot the points
        plt.scatter(x_values, y_values, color=color, alpha=0.7)

    # Add labels, legend, and title
    plt.xlabel('Objective 1', fontsize=12)
    plt.ylabel('Objective 2', fontsize=12)
    plt.title('Pareto Front Evolution', fontsize=14)
    plt.grid(True)
    plt.tight_layout()
    if savetoFile:
        plt.savefig(f"results/test{testnr}/plots/analyse/paretofrontEvolution_{plotname}.pdf", format='pdf', dpi=300) 
    if printPlot:
        plt.show()
    plt.close()
def plotParetoFrontWithMaxOV(points, maxObjectiveValues, testnr: str, plotname: str, savetoFile: bool, printPlot: bool):
        # Extract x and y values from objectiveSpace
    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]

    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.scatter(x_values, y_values, color='blue', label='Objective Space Points', alpha=0.7)

    # Add horizontal and vertical lines
    plt.axvline(x=maxObjectiveValues[0], color='green', linestyle='--', label=f'Max Priority ({maxObjectiveValues[0]})')
    plt.axhline(y=maxObjectiveValues[1], color='red', linestyle='--', label=f'Max Image quality ({round(maxObjectiveValues[1],2)})')

   # Set axis limits to start from 0
    plt.xlim(0, max(maxObjectiveValues[0], max(x_values)) * 1.1)  # Add 10% padding for better visualization
    plt.ylim(0, max(maxObjectiveValues[1], max(y_values)) * 1.1)  # Add 10% padding for better visualization
    
    # Add labels, title, and legend
    plt.xlabel('Priority', fontsize=12)
    plt.ylabel('Image Quality', fontsize=12)
    plt.title('Objective Space', fontsize=14)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=10)
    plt.grid(True)

    # Show the plot
    plt.tight_layout()
    if savetoFile:
        plt.savefig(f"results/test{testnr}/plots/analyse/obSpace_wLimits_{plotname}.pdf", format='pdf', dpi=300) 
    if printPlot:
        plt.show()
    plt.close()
    plt.show()


# Run algorithm and save data in json files
def runAlgFormatResults(testName: str,
                        testNumber: int,
                        ttwList: list,
                        oh: OH,
                        destructionNumber: int,
                        maxSizeTabooBank: int,
                        printResults, 
                        saveToFile,
                        nRuns: int,
                        popSize: int,
                        schedulingParameters: SP, 
                        alnsRuns: int,
                        isTabooBankFIFO: bool,
                        iqNonLinear: bool,
                        ohDurationInDays: int, 
                        ohDelayInHours: int,
                        hypsoNr: int):
    
    start_time = time.time()

    printArray, bestSolution, bestIndex, population = runNSGA(popSize, nRuns, ttwList, schedulingParameters, oh, alnsRuns, isTabooBankFIFO, iqNonLinear, destructionNumber, maxSizeTabooBank=maxSizeTabooBank)

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
    plotObjectiveSpace_filename = f"results/test{testNumber}/plots/OS_{testName}.pdf"
    createPlotObjectiveSpace(fronts, objectiveSpace, selectedObjectiveVals, plotObjectiveSpace_filename, printResults)
    plotSchedual_filename = f"results/test{testNumber}/plots/S_{testName}.pdf"
    try:
        createPlotSchedual(population[bestIndex].schedual, plotSchedual_filename, printResults)
    except IndexError:
        print(f"BestIndex = {bestIndex} is out of range for population of size {len(population)}")

    plotKneePoints_filename = f"results/test{testNumber}/plots/KP_{testName}.pdf"
    createPlotKneePointHistogram(kneePoints, plotKneePoints_filename, printResults)

    # Find max IQ in final population
    maxIQ = 0
    for i in range(len(population)):
        individual = population[i]
        _, maxImproved, _ = improveIQ(individual.schedual, ttwList, oh, schedulingParameters)
        newIQ = objectiveFunctionImageQuality(maxImproved, oh)
        if newIQ > maxIQ:
            maxIQ = newIQ
    maxP = findMaxPriority(ttwList, schedulingParameters)

    # create plot of ob space with maxIQ and maxP
    plotParetoFrontWithMaxOV(objectiveSpace, [maxP, maxIQ], testNumber, testName, saveToFile, printResults)

    #Chekc if best solution can be improved
    improvedBS, _, canBeImproved = improveIQ(population[bestIndex].schedual, ttwList, oh, schedulingParameters)    
    if checkFeasibility(improvedBS, schedulingParameters.captureDuration, schedulingParameters.transitionTime):
        if canBeImproved:
            print("Best solution can be improved")
            # save to file
            bestSchedual_filename = f"results/test{testNumber}/schedual/Imporved_BS_{testName}.json"
            serializable_schedual = [
                {"Ground Target": row[0], "Start Time": row[1], "End Time": row[2]} for row in improvedBS
            ]
            

    
    if not saveToFile:
        # End function here without saving results
        return
    
    # Save parameter data from the run to csv file
    testData_filename = f"results/test{testNumber}/testData/TD_{testName}.csv"
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

    schedualsFinalPop_filename = f"results/test{testNumber}/schedual/SFP_{testName}.json"
    with open(schedualsFinalPop_filename, mode='w') as file:
        json.dump(serializable_schedualsFinalPop, file, indent=4)

    ### Save best schedual to json file
    bestSchedual_filename = f"results/test{testNumber}/schedual/BS_{testName}.json"
    serializable_schedual = [
        {"Ground Target": row[0], "Start Time": row[1], "End Time": row[2]} for row in population[bestIndex].schedual
    ]

    with open(bestSchedual_filename, mode='w') as file:
        json.dump(serializable_schedual, file, indent=4)

    ### Save ttwList of best solution to json file
    ttwList_filename = f"results/test{testNumber}/schedual/TTWL_{testName}.json"
    serializable_ttwList = []
    for ttw in population[bestIndex].ttwList:
        ttwData = {
            "Ground Target": [ttw.GT.id, ttw.GT.priority]
,            "Time Windows": [{"start": tw.start, "end": tw.end} for tw in ttw.TWs]
        }
        serializable_ttwList.append(ttwData)

    with open(ttwList_filename, mode='w') as file:
        json.dump(serializable_ttwList, file, indent=4)


    ### Save fronts, objectiveSpace, and selectedIbjectiveVals and kneepoint to json file
    json_filename = f"results/test{testNumber}/algorithmData/AD_{testName}.json"
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


#Variables that say fixed during all tests
schedulingParameters = SP(40, 60, 90)
startTime = "2025-04-01 16:47:49.990785"
ohDurationInDays, ohDelayInHours, hypsoNr = 2, 2, 1

oh, ttwList = getModelInput(schedulingParameters.captureDuration, ohDurationInDays, ohDelayInHours, hypsoNr, startTime)

optimizedSchedule, objVals = runGreedyAlgorithm(ttwList, oh, schedulingParameters)
print(objVals)



### RUN THE TEST #### 
#stay fixed during all tests
RepetedRuns = 1
popSize = 1

# Variables that change during different tests
isTabooBankFIFO = True
iqNonLinear = False
nsgaRunds = 1
ALNSRuns = 1
maxTabBank = 10
desNumber = 6


###################################################################
testNumber = 36
for i in range(RepetedRuns):
    runAlgFormatResults(
        testName = f"test{testNumber}-run{i}",
        testNumber = testNumber,
        ttwList = ttwList,
        oh = oh,
        destructionNumber = desNumber, 
        maxSizeTabooBank = maxTabBank,
        printResults = False, 
        saveToFile = True,
        nRuns = nsgaRunds,
        popSize = popSize, 
        schedulingParameters = schedulingParameters,
        alnsRuns = ALNSRuns,
        isTabooBankFIFO = isTabooBankFIFO,
        iqNonLinear= iqNonLinear,
        ohDurationInDays = ohDurationInDays,
        ohDelayInHours = ohDelayInHours,
        hypsoNr = hypsoNr
    )
print(f"Test {i+1}/{RepetedRuns} finished")

schedualedTargetsHistogram(testNumber, RepetedRuns, True, False)
objectiveSpaceHistogram(testNumber, RepetedRuns, True, False)
changesInPF = objectiveSpaceHistogram(testNumber, RepetedRuns, True, False)
saveResultsToFile(testNumber, RepetedRuns, True, False, 0)

# ###################################################################
# testNumber = 32
# ALNSRuns = 30
# for i in range(RepetedRuns):
#     runAlgFormatResults(
#         testName = f"test{testNumber}-run{i}",
#         testNumber = testNumber,
#         ttwList = ttwList,
#         oh = oh,
#         destructionNumber = desNumber, 
#         maxSizeTabooBank = maxTabBank,
#         printResults = False, 
#         saveToFile = True,
#         nRuns = nsgaRunds,
#         popSize = popSize, 
#         schedulingParameters = schedulingParameters,
#         alnsRuns = ALNSRuns,
#         isTabooBankFIFO = isTabooBankFIFO,
#         iqNonLinear= iqNonLinear,
#         ohDurationInDays = ohDurationInDays,
#         ohDelayInHours = ohDelayInHours,
#         hypsoNr = hypsoNr
#     )
# print(f"Test {i+1}/{RepetedRuns} finished")
# schedualedTargetsHistogram(testNumber, RepetedRuns, True, False)
# objectiveSpaceHistogram(testNumber, RepetedRuns, True, False)
# changesInPF = objectiveSpaceHistogram(testNumber, RepetedRuns, True, False)
# saveResultsToFile(testNumber, RepetedRuns, True, False, changesInPF)



# print("All tests finished")

 