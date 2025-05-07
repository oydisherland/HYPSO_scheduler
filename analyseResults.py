from runAlgFormatResults import evaluateAlgorithmData
from runAlgFormatResults import evaluateBestSchedual
from runAlgFormatResults import evaluateSchedualsFinalPop

import matplotlib.pyplot as plt
import numpy as np

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

    ### Evaluate the final knee point in all induviduals in population
    plotKneePoints(kneePoints, testnr, savetoFile, printPlot)

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

testNumber = 7

schedualedTargetsHistogram(testNumber, 10, True, False)
objectiveSpaceHistogram(testNumber, 10, True, False)



