from runAlgFormatResults import evaluateAlgorithmData

import numpy as np
import csv
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Patch
import matplotlib.colors as mcolors
from matplotlib import rcParams
import math

def darken_color(hex_color, factor=0.7):
    """Return a darker shade of the given hex color."""
    rgb = mcolors.to_rgb(hex_color)
    dark_rgb = tuple([c * factor for c in rgb])
    return dark_rgb


def objectiveSpaceHistogram(testnr: str, repeatedRuns: int):
    changesInParetoFrontList = []
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
        changesInParetoFrontList.append(changesInParetoFront)
    return changesInParetoFrontList

def plotChangesInParetoFront(changesInParetoFrontList: list, nameList: list, savetoFile: bool, printPlot: bool, fileName: str):
    
    rcParams['font.family'] = 'serif'
    rcParams['font.serif'] = ['Computer Modern']
    rcParams['text.usetex'] = True  # Set to True if LaTeX is installed

    colors = ['#36AB9F', '#FFC943', '#607196', darken_color('#F9EBE1', factor=0.8)]
    plt.figure(figsize=(10, 6))
    for i , change in enumerate(changesInParetoFrontList):
        # Create the x-axis values (indices of the list)
        x_values = list(range(len(change)))

        # Plot the data
        plt.plot(x_values, change, marker='o',label=nameList[i], color=colors[i % len(colors)])

    # Add labels, title, and grid
    plt.xlabel('NSGA Iteration [-]', fontsize=12)
    plt.ylabel('Changes in Pareto Front [-]', fontsize=12)
    plt.title('Mean Value of Changes in Pareto Front', fontsize=14)
    plt.xticks(ticks=x_values)
    y_min = min([min(changes) for changes in changesInParetoFrontList])
    y_max = max([max(changes) for changes in changesInParetoFrontList]) 
    plt.yticks(ticks=list(range(int(y_min), int(y_max) + 1)))
    plt.subplots_adjust(bottom=0.2)

    plt.legend( loc='upper center', bbox_to_anchor=(0.5, -0.09), fontsize=12, ncol=len(nameList))

    
    
    if savetoFile:
        plt.savefig(fileName, format='pdf', bbox_inches='tight') 
    if printPlot:
        plt.show()
    
    plt.close()


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

def plotSingleBarPlot(groupNames, values, ylabel: str, title: str, saveplot: bool, filename: str):
    rcParams['font.family'] = 'serif'
    rcParams['font.serif'] = ['Computer Modern']
    rcParams['text.usetex'] = True  # Set to True if LaTeX is installed

    x = np.arange(len(groupNames))
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['#36AB9F', '#FFC943', '#607196', '#F9EBE1']
    bar_colors = (colors * ((len(values) // len(colors)) + 1))[:len(values)]

    bars = ax.bar(x, values, color=bar_colors, capsize= 0)

    ax.set_xlabel('Test Nr', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(groupNames, fontsize=12)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Set y-axis limits with margin
    min_y = min(values)
    max_y = max(values) 
    y_margin = (max_y - min_y) * 0.1 if max_y > min_y else 1
    ax.set_ylim(min_y - y_margin, max_y + y_margin)

    plt.tight_layout()
    if saveplot:
        plt.savefig(filename, format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()

def plotBarPlot(groupNames: list, values1, values2, std1, std2, label1, label2, saveplot: bool, printplot: bool, plotName: str, filename: str):
    
    rcParams['font.family'] = 'serif'
    rcParams['font.serif'] = ['Computer Modern']
    rcParams['text.usetex'] = True  # Set to True if LaTeX is installed

    x = np.arange(len(groupNames))  # label locations
    width = 0.35  # width of the bars

    fig, ax = plt.subplots(figsize=(10, 6))
    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, values1, width,yerr=std1, label=label1, color='#36AB9F', capsize=5)
    bars2 = ax.bar(x + width/2, values2, width, yerr=std2, label=label2, color='#607196', capsize=5)

    ax.set_xlabel('Configuration', fontsize=12)
    ax.set_ylabel('Sum of Priority [-]', fontsize=12)
    ax.set_title(plotName, fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(groupNames, fontsize=12)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    minValues1 = [val - std for val, std in zip(values1, std1)]
    minValues2 = [val - std for val, std in zip(values2, std2)]
    maxValues1 = [val + std for val, std in zip(values1, std1)]
    maxValues2 = [val + std for val, std in zip(values2, std2)]
        # Set y-axis limits to start just below the minimum bar value
    all_valuesMin = np.concatenate([minValues1, minValues2])
    all_valuesMax = np.concatenate([maxValues1, maxValues2])
    min_y = all_valuesMin.min()
    max_y = all_valuesMax.max()
    y_margin = (max_y - min_y) * 0.1  # 10% margin
    ax.set_ylim(min_y - y_margin, max_y + y_margin)
    if saveplot:
        plt.savefig(filename, format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()

def plotRunTimeRegression(allRunTimes: list, index: list, alnsItr: list, saveplot: bool, printplot: bool, plotName: str, filename: str):
    """
    Plots the runtime regression for different groups.
    """
    rcParams['font.family'] = 'serif'
    rcParams['font.serif'] = ['Computer Modern']
    rcParams['text.usetex'] = True  # Set to True if LaTeX is installed

    plt.figure(figsize=(10, 6))
    colors = ['#36AB9F', '#FFC943', '#607196', '#F9EBE1']
    runTime = []
    for i, groupIndex in enumerate(index):
        runTime.append(allRunTimes[groupIndex - 1])
    
    plt.figure(figsize=(10, 6))
    plt.scatter(alnsItr, runTime, color=colors[0], label='Data points')

    # Fit and plot regression line
    coeffs = np.polyfit(alnsItr, runTime, 1)
    poly = np.poly1d(coeffs)
    x_fit = np.linspace(min(alnsItr), max(alnsItr), 100)
    y_fit = poly(x_fit)
    plt.plot(x_fit, y_fit, color=colors[1], linestyle='--', label=f'Regression: y={coeffs[0]:.2f}x+{coeffs[1]:.2f}')

    plt.xlabel('number of ALNS iterations', fontsize=12)
    plt.ylabel('Run Time', fontsize=12)
    plt.title(plotName, fontsize=14)
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    if saveplot:
        plt.savefig(filename, format='pdf', bbox_inches='tight')
    if printplot:
        plt.show()
    plt.close()
        


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

def plotEllipticalBubble(meanObjectiveP, meanObjectiveIQ, stdObjectiveP, stdObjectiveIQ, saveplot: bool, printplot: bool, groupNames: list, plotName: str, filename: str):
    
    # Set the font to Computer Modern
    rcParams['font.family'] = 'serif'
    rcParams['font.serif'] = ['Computer Modern']
    rcParams['text.usetex'] = True  # Set to True if LaTeX is installed

    plt.figure(figsize=(10, 6))
    colors = ['#36AB9F', '#FFC943', '#607196', '#F9EBE1']
    legend_patches = []
    # Loop through each test and plot an ellipse
    for i in range(len(meanObjectiveP)):
        fill_color = colors[i % len(colors)]
        edge_color = darken_color(fill_color, 0.6)
        ellipse = Ellipse(
            (meanObjectiveP[i], meanObjectiveIQ[i]),  # Center of the ellipse
            width= stdObjectiveP[i],              # Width (2 * std for x-radius)
            height= stdObjectiveIQ[i],            # Height (2 * std for y-radius)
            alpha=0.5,                               # Transparency
            edgecolor=edge_color,                       # Border color
            facecolor=fill_color                      # Fill color
        )
        plt.gca().add_patch(ellipse)  # Add the ellipse to the plot
        legend_patches.append(Patch(facecolor=fill_color, edgecolor=edge_color, label=groupNames[i]))
    #     if i == 7:
    #         continue
    #     plt.text(
    #         meanObjectiveP[i], meanObjectiveIQ[i], groupNames[i],
    #         fontsize=12, ha='center', va='center', fontweight='bold'
    #     )

    # plt.annotate(
    # '32',              # Label text
    # xy=(meanObjectiveP[7], meanObjectiveIQ[7] + 0.07),                 # Point to annotate (tip of arrow)
    # xytext=(meanObjectiveP[7] + 6, meanObjectiveIQ[7] - 0.45),           # Text position
    # arrowprops=dict(arrowstyle='->',linewidth=0.5, color='black')  # Arrow style
    # )

    # Add labels, title, and grid
    plt.xlabel('Sum of priorities [-]', fontsize=12)
    plt.ylabel('Image quality [degrees]', fontsize=12)
    plt.title(plotName, fontsize=14)
    plt.grid(True)

    # Set axis limits for better visualization
    plt.xlim(min(meanObjectiveP) - max(stdObjectiveP), max(meanObjectiveP) + max(stdObjectiveP))
    plt.ylim(min(meanObjectiveIQ) - max(stdObjectiveIQ), max(meanObjectiveIQ) + max(stdObjectiveIQ))
    plt.legend(handles=legend_patches, loc='upper center', bbox_to_anchor=(0.5, -0.09), fontsize=12, ncol=len(groupNames))

    plt.subplots_adjust(bottom=0.2)
    # Save or display the plot
    if saveplot:
        plt.savefig(filename, format='pdf', bbox_inches='tight') 
    if printplot:
        plt.show()
    
    plt.close()  

def getTestData(testList: list, rowName: str):

    data = []
    for testNr in testList:
        filepath = f"results/testPlan/test{testNr}.csv"

        try:
            with open(filepath, mode='r') as file:
                reader = csv.reader(file)
                for row in reader:
                    # Check if the row contains the "Knee points median" label
                    if row[0].strip() == rowName:
                        if len(row) == 2:
                            p = float(row[1])
                        else:
                            p = [ float(row[1]), float(row[2]) ]
                        data.append(p)
        except FileNotFoundError:
            print(f"File not found: {filepath}")
        except Exception as e:
            print(f"An error occurred: {e}")

    return data

def convertOBPoints(testsWLineariq: list, testsWNonLineariq: list):

    kpListLin = getTestData(testsWLineariq, "Knee points median")
    kpListNonLin = getTestData(testsWNonLineariq, "Knee points median")

    for kpPoint in kpListNonLin:
        iqValue = kpPoint[1]
        elevation = math.degrees(math.acos(1 - (iqValue / 100)))
        kpPoint[1] = elevation

    allKpPoints = []
    for i in range(len(testsWLineariq) + len(testsWNonLineariq)):
        if testsWLineariq:
            if i + 1 == testsWLineariq[0]:
                allKpPoints.append(kpListLin.pop(0))
                testsWLineariq.pop(0)
                continue
        if testsWNonLineariq:
            if i + 1 == testsWNonLineariq[0]:
                allKpPoints.append(kpListNonLin.pop(0))
                testsWNonLineariq.pop(0)
                continue
                
    return allKpPoints
def plotKneePointsFromAllTests(points: list, groupIndex: list, groupNames: list, saveplot: bool, printplot: bool, filename: str):
    """
    Plot the knee points from all tests.
    """
    # Set the font to Computer Modern
    rcParams['font.family'] = 'serif'
    rcParams['font.serif'] = ['Computer Modern']
    rcParams['text.usetex'] = True  # Set to True if LaTeX is installed
    
    plt.figure(figsize=(10, 6))
    colors = ['#36AB9F', '#FFC943', '#607196', '#F9EBE1']

    for i, group in enumerate(groupIndex):
        groupPoints = [points[j - 1] for j in group]
        x_values = [point[0] for point in groupPoints]
        y_values = [point[1] for point in groupPoints]

        plt.scatter(x_values, y_values, color=colors[i % len(colors)], label=groupNames[i], alpha=0.7)


    # Add labels, title, and grid
    plt.xlabel('Sum of priorities', fontsize=12)
    plt.ylabel('Image quality', fontsize=12)
    plt.title(f'Knee Points', fontsize=14)
    plt.grid(True)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.09), fontsize=12, ncol=len(groupNames))
    plt.subplots_adjust(bottom=0.2)

    # Save or display the plot
    if saveplot:
        plt.savefig(filename, format='pdf', bbox_inches='tight') 
    if printplot:
        plt.show()
    
    plt.close()

def plotKPStd(points: list, groupIndex: list, groupNames: list, saveplot: bool, printplot: bool):
    """
    Plot the knee points from all tests.
    """
    plt.figure(figsize=(10, 6))
    colormap = plt.get_cmap('viridis', len(groupIndex))

    for i, group in enumerate(groupIndex):
        groupPoints = [points[j - 1] for j in group]
        x_values = [point[0] for point in groupPoints]
        y_values = [point[1] for point in groupPoints]

        plt.scatter(x_values, y_values, color=colormap(i), label=groupNames[i], alpha=0.7)


    # Add labels, title, and grid
    plt.xlabel('Sum of priorities', fontsize=12)
    plt.ylabel('Image quality', fontsize=12)
    plt.title(f'Std of Knee Points from {groupNames}', fontsize=14)
    plt.grid(True)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=10)


    # Save or display the plot
    if saveplot:
        plt.savefig("results/plots/knee_points_all_tests.png")
    
    if printplot:
        plt.show()
    
    plt.close()

def plotAllConfigurations(points: list, groupIndex: list, groupNames: list, saveplot: bool, printplot: bool, plotName: str, filename: str):
    
    # Set the font to Computer Modern
    rcParams['font.family'] = 'serif'
    rcParams['font.serif'] = ['Computer Modern']
    rcParams['text.usetex'] = True  # Set to True if LaTeX is installed
    
    plt.figure(figsize=(10, 6))
    colors = ['#36AB9F', '#FFC943', '#607196', '#F9EBE1']
    legend_patches = []
    for i, group in enumerate(groupIndex):
        color = colors[i % len(colors)]
        groupPoints = [points[j - 1] for j in group]
        x_values = [point[0] for point in groupPoints]
        y_values = [point[1] for point in groupPoints]
        plt.scatter(x_values, y_values, color=color, alpha=0.7)
        # Annotate each point with its group label
        # for x, y in zip(x_values, y_values):
        #     plt.text(x, y, groupNames[i], fontsize=10, ha='left', va='bottom')
        legend_patches.append(Patch(facecolor=color, edgecolor=darken_color(color, 0.6), label=groupNames[i]))



    # Add labels, title, and grid
    plt.xlabel('Sum of priorities [-]', fontsize=12)
    plt.ylabel('Image quality [degrees]', fontsize=12)
    plt.title(plotName, fontsize=14)
    plt.grid(True)
    plt.legend(handles=legend_patches, loc='upper center', bbox_to_anchor=(0.5, -0.09), fontsize=12, ncol=len(groupNames))
    plt.subplots_adjust(bottom=0.2)
    # Save or display the plot
    if saveplot:
        plt.savefig(filename, format='pdf', bbox_inches='tight') 
    if printplot:
        plt.show()
    
    plt.close()


stdKP = getTestData(list(range(1,35)) , "Knee points std")
stdPop = getTestData(list(range(1,35)) , "Final pop median of std")
runTime = getTestData(list(range(1,35)) , "Runtime median")
changePop = getTestData(list(range(1,35)) , "Changes in PF last half")

testsWLineariq = list(range(1,7)) + list(range(13, 19)) + list(range(25, 35))
testsWNonLineariq = list(range(7, 13)) + list(range(19, 25))
allKPs = convertOBPoints(testsWLineariq, testsWNonLineariq)
# Groups 
alg1A = list(range(1, 7))
alg1B = list(range(7, 13))
alg2A = list(range(13, 19))
alg2B = list(range(19, 25))
alg1 = alg1A + alg1B
alg2 = alg2A + alg2B
algA = alg1A + alg2A
algB = alg1B + alg2B
nItr20 = list(range(1,4)) + list(range(7,10)) + list(range(13,16)) + list(range(19,22))
nItr40 = list(range(4,7)) + list(range(10,13)) + list(range(16,19)) + list(range(22,25))
tb30 = list(range(13, 16)) + list(range(19, 22))
tb20 = list(range(16, 19)) + list(range(22, 25))
a1dn1 = [1, 4, 7, 10]
a1dn2 = [2, 5, 8, 11]
a1dn3 = [3, 6, 9, 12]
a2dn2 = [13, 16, 19, 22]
a2dn4 = [14, 17, 20, 23]
a2dn8 = [15, 21, 18, 24]

alg1A_2 = list(range(25,29))
alg2A_2 = list(range(29,33))



groups = [alg1, alg2, algA, algB, nItr20, nItr40, tb30, tb20, a1dn1, a1dn2, a1dn3, a2dn2, a2dn4, a2dn8]
groupNames = [
    "Alg1", 
    "Alg2", 
    "AlgA", 
    "AlgB",
    "iteration 20 & 30",
    "iteration 40 & 15",
    "Taboobank 30",
    "Taboobank 20",
    "Alg 1: destruction nr 1",
    "Alg 1: destruction nr 2",
    "Alg 1: destruction nr 3",
    "Alg 2: destruction nr 2",
    "Alg 2: destruction nr 4",
    "Alg 2: destruction nr 8"
]

groupNames5 = ["Alg1 itr=[20|30]", "Alg1 itr=[40|15]", "Alg2 itr=[20|30]", "Alg2 itr=[40|15]"]
groups5 = [list(range(1, 4)) + list(range(7, 10)), list(range(4, 7)) + list(range(10, 13)), list(range(13, 16)) + list(range(19, 22)), list(range(16, 19)) + list(range(22, 25))] 
plotName5 = "Median and Std of Knee Points for Different Iteration Configurations, itr = [NSGA-II | ALNS]"

groups6 = [[25], [26], [27], [28], [29], [30], [31], [32]]
groupNames6 = ["25", "26", "27", "28", "29", "30", "31", "32"]
plotName6 = "Median and Std of Knee Points from Test Round 2"

groups7 = groups6 
groupNames7 = groupNames6
plotName7 = "std.Pop from Test Round 2"

groups8 = [a1dn1, a1dn2, a1dn3]
groupNames8 = ["destruction number = 1", "destruction number = 2", "destruction number = 3"]
plotName8 = "Median and Std of Knee Points for Different Destruction Numbers in Alg1"

groups9 = [a2dn2, a2dn4, a2dn8]
groupNames9 = ["destruction number = 2", "destruction number = 4", "destruction number = 6 and 8"]
plotName9 = "Median and Std of Knee Points for Different Destruction Numbers in Alg2"

groups10_1 = groups8
groupNames10_1 = groupNames8
plotName10_1 = "std.Pop for Different Destruction Numbers in Alg1"

groups10_2 = groups9
groupNames10_2 = groupNames9
plotName10_2 = "std.Pop for Different Destruction Numbers in Alg2"

groups11_1 = [list(range(1, 4)) + list(range(7, 10)), list(range(4, 7)) + list(range(10, 13)), [28], [25], [26], [27]]
groups11_2 = [list(range(13, 16)) + list(range(19, 22)), list(range(16, 19)) + list(range(22, 25)), [29], [30], [31], [32]]
groups11 = groups11_1 + groups11_2
groupNames11 = ["itr=[20|30]", "itr=[40|15]", "itr=[30|30]", "itr=[30|50]", "itr=[30|75]", "itr=[30|100]"]
labels11_1 = ["Alg1", "", "", "", "", ""]
labels11_2 = ["Alg2", "", "", "", "", ""]
plotName11 = "Mean and std: Sum of Priorities for Alg1 vs Alg2, itr = [NSGA-II | ALNS]"


groups12_1 = [list(range(1, 4)) + list(range(7, 10)), list(range(4, 7)) + list(range(10, 13))]
groups12_2 = [list(range(13, 16)) + list(range(19, 22)), list(range(16, 19)) + list(range(22, 25))]
groups12 = groups12_1 + groups12_2
groupNames12 = ["itr=[20|30]", "itr=[40|15]"]
labels12_1 = ["Alg1", ""]
labels12_2 = ["Alg2", ""]
plotName12 = "Mean and std: Image Quality for Alg1 vs Alg2, itr = [NSGA-II | ALNS]"

groups13 = [28, 25, 26, 27]
plotName13 = "Runtime Regression for Different ALNS Iterations"

groups14 = [[30], [34], [33]]
groupNames14 = ["Taboobank size=8", "Taboobank size=10", "Taboobank size=12"]
plotName14 = "Mean and std of Knee Point for Different Taboobank Sizes with ALNS itr=75"

groups15 = [list(range(1,35))]
groupNames15 = [f"{i}" for i in range(1, 35)]
plotName15 = "Changes in Sencond half of Pareto Front for all Configurations"

# plotRunTimeRegression(runTime, groups13, [30, 50, 75, 100], True, True, plotName13, "results/plots/runtimeRegression.pdf")

# plotAllConfigurations(stdPop, groups10_2, groupNames10_2, True, True, plotName10_2, filename="results/plots/compareStdPop_group10_2.pdf")

allChangeLists = objectiveSpaceHistogram("32", 10)
allChangeLists2 = objectiveSpaceHistogram("29", 10)
allChangeLists3 = objectiveSpaceHistogram("30", 10)
allChangeLists4 = objectiveSpaceHistogram("31", 10)

meanChangesValues1 = []
meanChangesValues2 = []
meanChangesValues3 = []
meanChangesValues4 = []
for i in range(len(allChangeLists[0])):
    # iterate through each test

    meanChangesValues1.append(np.mean([allChangeLists[j][i] for j in range(len(allChangeLists))]))
    meanChangesValues2.append(np.mean([allChangeLists2[j][i] for j in range(len(allChangeLists2))]))
    meanChangesValues3.append(np.mean([allChangeLists3[j][i] for j in range(len(allChangeLists3))]))
    meanChangesValues4.append(np.mean([allChangeLists4[j][i] for j in range(len(allChangeLists4))]))

# plotChangesInParetoFront([meanChangesValues1, meanChangesValues2, meanChangesValues3, meanChangesValues4],
                        #  ["ALNS itr=30", "ALNS itr=50", "ALNS itr=75", "ALNS itr=100"], 
                        #  True, 
                        #  True, 
                        #  "results/plots/changesInParetoFront.pdf")


## Plot ellipses
mP, sP, mIQ, sIQ = [], [], [], []
for subgroup in groups14:
    mP_, sP_, mIQ_, sIQ_ = [], [], [], []
    for index in subgroup:
        mP_.append(allKPs[index-1][0])
        mIQ_.append(allKPs[index-1][1])
        sP_.append(stdKP[index-1][0])
        sIQ_.append(stdKP[index-1][1])
    mP.append(np.mean(mP_))
    mIQ.append(np.mean(mIQ_))
    sP.append(np.mean(sP_))
    sIQ.append(np.mean(sIQ_))
# plotEllipticalBubble(mP, mIQ, sP, sIQ, True, True, groupNames14, plotName14, "results/plots/compareKP_ellipses_group14.pdf")         
# plotBarPlot(groupNames12, mIQ[0:2], mIQ[2:4], sIQ[0:2], sIQ[2:4], labels12_1, labels12_2, True, True, plotName12, "results/plots/compareKP_barplot_group12.pdf")
# plotBarPlot(groupNames11, mP[0:6], mP[6:12], sP[0:6], sP[6:12], labels11_1, labels11_2, True, True, plotName11, "results/plots/compareKP_barplot_group11.pdf")
plotSingleBarPlot(groupNames15, changePop, "change.Pop [-]", plotName15, True, "results/plots/chnagesPop_barplot_group15.pdf")

# #destroyRate = 0.4
# testList1 = [9]
# mP1, sP1, mIQ1, sIQ1, = calculateMeanAndStd(testList1, 10, False)
# print(f"mP1: {mP1}, sP1: {sP1}, mIQ1: {mIQ1}, sIQ1: {sIQ1}")
# #destroyRate = 0.6
# testList2 = [12, 10, 11]
# mP2, sP2, mIQ2, sIQ2  = calculateMeanAndStd(testList2, 10, False)
# #destroyRate = 0.8
# testList3 = [13, 14, 15]
# mP3, sP3, mIQ3, sIQ3 = calculateMeanAndStd(testList3, 10, False)

# testnames = ["dr=0.4", "dr=0.6", "dr=0.8"]
# plotEllipticalBubble([mP1, mP2, mP3], [mIQ1, mIQ2, mIQ3], [sP1, sP2, sP3], [sIQ1, sIQ2, sIQ3], testnames)


# plotCompareKneePoints(testList, 10)

