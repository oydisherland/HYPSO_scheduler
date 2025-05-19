from runAlgFormatResults import evaluateAlgorithmData

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

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

    for test in testnr:
        bestSolutionsForOneTest = []
        for run in range(nRuns):
            algDataFileName = f"results/test{test}/algorithmData/AD_test{test}-run{run}.json"
            algData = evaluateAlgorithmData(algDataFileName)
            bestSolution = algData[-1][-1]
            bestSolutionsForOneTest.append(bestSolution)

        # Extract objective values from the kneePoints list
        ObjectiveP.append([point[0] for point in bestSolutionsForOneTest])
        ObjectiveIQ.append([point[1] for point in bestSolutionsForOneTest])
    
    meanObjectiveP = np.mean(ObjectiveP, axis=None)
    meanObjectiveIQ = np.mean(ObjectiveIQ, axis=None)
    stdObjectiveP = np.std(ObjectiveP, axis=None)
    stdObjectiveIQ = np.std(ObjectiveIQ, axis=None)
    
    # Plotting the results
    if plot:
        plotObjectiveHistogram(ObjectiveP)
        plotObjectiveHistogram(ObjectiveIQ)


    return meanObjectiveP, stdObjectiveP, meanObjectiveIQ, stdObjectiveIQ

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


#destroyRate = 0.4
testList1 = [9]
mP1, sP1, mIQ1, sIQ1, = calculateMeanAndStd(testList1, 10, False)
print(f"mP1: {mP1}, sP1: {sP1}, mIQ1: {mIQ1}, sIQ1: {sIQ1}")
#destroyRate = 0.6
testList2 = [12, 10, 11]
mP2, sP2, mIQ2, sIQ2  = calculateMeanAndStd(testList2, 10, False)
#destroyRate = 0.8
testList3 = [13, 14, 15]
mP3, sP3, mIQ3, sIQ3 = calculateMeanAndStd(testList3, 10, False)

testnames = ["dr=0.4", "dr=0.6", "dr=0.8"]
plotEllipticalBubble([mP1, mP2, mP3], [mIQ1, mIQ2, mIQ3], [sP1, sP2, sP3], [sIQ1, sIQ2, sIQ3], testnames)


# plotCompareKneePoints(testList, 10)

