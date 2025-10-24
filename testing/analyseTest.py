
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

import datetime
from dataclasses import dataclass
from test_scenario import TestScenario

from data_postprocessing.generate_cmdLine import recreateOTListFromCmdFile
from scheduling_model import OH
from data_input.utility_functions import InputParameters
from data_preprocessing.create_data_objects import createOH
from data_preprocessing.objective_functions import objectiveFunctionPriority, objectiveFunctionImageQuality
from data_preprocessing.parseTargetsFile import getTargetIdPriorityDictFromJson


#plt.rcParams['text.usetex'] = True  # Optional: for LaTeX rendering
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['cmr10']  # Computer Modern Roman
plt.rcParams['mathtext.fontset'] = 'cm'  # Computer Modern for math text
plt.rcParams['axes.formatter.use_mathtext'] = True 

@dataclass
class AnalyseTest:
    scenarios: list[TestScenario]
    cp_observationSchedules : list[list]


    def __init__(self, scenarioIds: list):
        self.scenarios = []
        self.cp_observationSchedules = []
        # Handle both single string and list of strings
        if isinstance(scenarioIds, str):
            # Single scenario ID
            scenario_list = [scenarioIds]
        elif isinstance(scenarioIds, list):
            # List of scenario IDs
            scenario_list = scenarioIds
        else:
            raise ValueError("scenarioIds must be either a string or a list of strings")
        
        for scenarioId in scenario_list:
            # Recreate TestScenario object
            scenario = TestScenario(senarioID=scenarioId)
            scenario.recreateTestScenario()
            self.scenarios.append(scenario)

            # Recreate observation schedules from cp_planner
            cp_cmdFilePath = os.path.join(os.path.dirname(__file__), f"../testing/testing_results/OH{scenarioId}/{scenarioId}_cp_cmdLines.txt")
            targetFilePath = os.path.join(os.path.dirname(__file__), f"../data_input/HYPSO_data/targets.json") 
            oh = scenario.getOh()
            inputParameters = scenario.getInputParameters()
            cp_otList = recreateOTListFromCmdFile(targetFilePath, cp_cmdFilePath, oh, inputParameters.bufferingTime, inputParameters.captureDuration)
            self.cp_observationSchedules.append(cp_otList)

    def plotObjectiveValues(self):
        """ Plot the objective values for each scenario """
        
    
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Define colors for different scenarios
        colors = ['#03045E', '#00A8E0', '#90E0EF', '#0077B6', '#CAF0F8', '#023E8A', '#EAFCFF', '#48CAE4']
        
        for i, (scenario, cp_otList) in enumerate(zip(self.scenarios, self.cp_observationSchedules)):
            # Get algorithm results
            obVals = scenario.getAllObjectiveValues()  # List of tuples (priority, imageQuality)
            
            # Get CP planner results
            cp_totalPriority = objectiveFunctionPriority(cp_otList)
            cp_totalImageQuality = objectiveFunctionImageQuality(cp_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
            
            # Choose color for this scenario
            base_color = colors[i % len(colors)]
            
            # Plot algorithm results (darker shade)
            if obVals:
                priorities = [val[0] for val in obVals]
                imageQualities = [val[1] for val in obVals]
                ax.scatter(priorities, imageQualities, 
                        c=base_color, 
                        alpha=1, 
                        s=50, 
                        label=f'Scenario {scenario.senarioID} - Algorithm',
                        marker='o')
            
            # Plot CP planner result (lighter shade, different marker)
            ax.scatter(cp_totalPriority, cp_totalImageQuality, 
                    c=base_color, 
                    alpha=1, 
                    s=100, 
                    label=f'Scenario {scenario.senarioID} - CP Planner',
                    marker='s',  # Square marker
                    edgecolors='black',
                    linewidth=1)
        
        # Customize plot
        ax.set_xlabel('Priority', fontsize=12)
        ax.set_ylabel('Image Quality', fontsize=12)
        ax.set_title('Objective Space', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Adjust layout to prevent legend cutoff
        plt.tight_layout()
        plt.show()         
    def plotTargetsChosen(self):
        """ Plot the targets chosen in each scenario """

        targetFilePath = os.path.join(os.path.dirname(__file__), "../data_input/HYPSO_data/targets.json")
        targetIdPriorityDict = getTargetIdPriorityDictFromJson(targetFilePath)
        

        
        for i, (scenario, cp_otList) in enumerate(zip(self.scenarios, self.cp_observationSchedules)):
            # One plot each scenario

            sorted_targets = sorted(targetIdPriorityDict.items(), key=lambda x: x[1], reverse=True)

            targetCount_NA = {targetId: 0 for targetId in targetIdPriorityDict.keys()} # Todo: come up with a better naming scheme than NA
            targetCount_CP = {targetId: 0 for targetId in targetIdPriorityDict.keys()}
            
            obsSchedsAllRuns = scenario.getObservationSchedules()

            for obsSched in obsSchedsAllRuns:
                for ot in obsSched:
                    targetCount_NA[ot.GT.id] += 1
            for ot in cp_otList:
                targetCount_CP[ot.GT.id] += 1
            
            # Filter out targets with 0 count in both NA and CP
            filtered_targets = [
                (targetId, priority) for targetId, priority in sorted_targets 
                if targetCount_NA[targetId] > 0 or targetCount_CP[targetId] > 0
            ]
            # Prepare data for plotting
            target_names = [targetId for targetId, priority in filtered_targets]
            na_counts = [targetCount_NA[targetId] for targetId, priority in filtered_targets]
            cp_counts = [targetCount_CP[targetId] for targetId, priority in filtered_targets]
            
            # Create the stacked bar chart
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Create bars
            bar_width = 0.8
            x_positions = range(len(target_names))
            
            # Bottom bars (NA counts)
            bars1 = ax.bar(x_positions, na_counts, bar_width, 
                        label='NSGA-II Algorithm', color='#03045E', alpha=0.8)
            
            # Top bars (CP counts) - stacked on top of NA counts
            bars2 = ax.bar(x_positions, cp_counts, bar_width, 
                        bottom=na_counts, label='CP Planner', color='#00A8E0', alpha=0.8)
            
            # Customize the plot 
            ax.set_xlabel('Target ID', fontsize=12)
            ax.set_ylabel('Selection Count', fontsize=12)
            ax.set_title(f'Target Selection Frequency - Scenario {scenario.senarioID}', 
                        fontsize=14, fontweight='bold')
            ax.set_xticks(x_positions)
            ax.set_xticklabels(target_names, rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
            
            # Add value labels on bars
            for j, (na_count, cp_count) in enumerate(zip(na_counts, cp_counts)):
                total = na_count + cp_count
                if total > 0:
                    ax.text(j, total + 0.1, str(total), ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            plt.show()           
    def plotNumberOfCapturedTargets(self):
        """ Plot the number of unique targets captured in each scenario """
        # Calculate averages for NSGA-II algorithm
        sumOfCapturesNA_averages = []
        for scenario in self.scenarios:
            obsSchedsAllRuns = scenario.getObservationSchedules()
            average = sum(len(obsSched) for obsSched in obsSchedsAllRuns) / len(obsSchedsAllRuns)
            sumOfCapturesNA_averages.append(average)
        
        # Calculate totals for CP Planner
        sumOfCapturesCP = [len(cp_otList) for cp_otList in self.cp_observationSchedules]
        
        # Prepare data for plotting
        scenario_labels = [f"Scenario {scenario.senarioID}" for scenario in self.scenarios]
        
        # Create the bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x_positions = range(len(scenario_labels))
        bar_width = 0.35
        
        # Create side-by-side bars
        bars1 = ax.bar([x - bar_width/2 for x in x_positions], sumOfCapturesNA_averages, bar_width,
                    label='NSGA-II Algorithm (Average)', color='#03045E', alpha=0.8)
        bars2 = ax.bar([x + bar_width/2 for x in x_positions], sumOfCapturesCP, bar_width,
                    label='CP Planner', color='#00A8E0', alpha=0.8)
        
        # Customize the plot
        ax.set_xlabel('Scenario', fontsize=12)
        ax.set_ylabel('Number of Captures', fontsize=12)
        ax.set_title('Number of Captures Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(scenario_labels)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for i, (na_avg, cp_count) in enumerate(zip(sumOfCapturesNA_averages, sumOfCapturesCP)):
            na_label = f'{na_avg:.0f}' if na_avg % 1 == 0 else f'{na_avg:.1f}'
            ax.text(i - bar_width/2, na_avg + 0.5, na_label, 
                ha='center', va='bottom', fontweight='bold')
            ax.text(i + bar_width/2, cp_count + 0.5, str(cp_count), 
                ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.yticks(range(0,int(max(sumOfCapturesNA_averages + sumOfCapturesCP)) + 2, 5))
        plt.show()           
    def plotParetoFrontEvolution(self, scenarioIndex: int, runIndex: int):
        """ Plot the evolution of the Pareto front for each scenario """
        
        #Extract the data for the spesific scenario and run
        scenario = self.scenarios[scenarioIndex]
        algDataAllRuns = scenario.getAlgorithmDataAllRuns()
        algData = algDataAllRuns[runIndex]  
        iterationData, bestIndex = algData

        # Create the plot
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Create a colormap for different iterations
        num_iterations = len(iterationData)
        custom_colors = ['#03045E', '#023E8A', '#0077B6', '#00A8E0', '#48CAE4', '#90E0EF']

        # Create a custom colormap
        custom_cmap = LinearSegmentedColormap.from_list("custom_blues", custom_colors)
        colors = custom_cmap(np.linspace(0, 1, num_iterations))
        
        for iteration in range(num_iterations):
            fronts, objectiveSpace, _ = iterationData[iteration]
            
            # Get the Pareto front (first front)
            if len(fronts) > 0 and len(fronts[0]) > 0:
                pareto_front_indices = fronts[0]
                pareto_front_points = [objectiveSpace[elem] for elem in pareto_front_indices]
                
                # Extract priorities and image qualities
                priorities = [point[0] for point in pareto_front_points]
                image_qualities = [point[1] for point in pareto_front_points]
                
                finalParetoFront = True if iteration == num_iterations - 1 else False
                
                # Plot the Pareto front for this iteration
                ax.scatter(priorities, image_qualities, 
                        alpha=0.7, 
                        s=50, 
                        label=f'Iteration {iteration + 1}',
                        marker='o',
                        facecolors='none' if finalParetoFront else colors[iteration],
                        edgecolors= colors[0] if finalParetoFront else 'none',)
                
                # print a cirkle around the kneepoint in the final pareto front
                if finalParetoFront:
                    kneePoint = objectiveSpace[bestIndex]
                    # Plot a big circle around the knee point
                    ax.scatter(kneePoint[0], kneePoint[1], 
                            facecolors='none',
                            edgecolors=colors[1],  # circle for visibility
                            s=200,  # Large size
                            linewidth=3,  # Thick edge
                            marker='o',
                            label='Knee Point')
        # Customize the plot
        ax.set_xlabel('Priority', fontsize=12)
        ax.set_ylabel('Image Quality', fontsize=12)
        ax.set_title(f'Pareto Front Evolution - Scenario {scenario.senarioID}, Run {runIndex + 1}', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Handle legend - only show every nth iteration if there are too many
        handles, labels = ax.get_legend_handles_labels()
        if len(labels) > 10:  # If more than 10 iterations, show every 5th
            step = max(1, len(labels) // 10)
            handles = handles[::step]
            labels = labels[::step]
        
        ax.legend(handles, labels, bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        plt.show()


def scaleObjectiveValues(scenario: TestScenario, objectiveValues: tuple) -> tuple:
    """ Scale the objective values to [0, 1] range for better visualization """
    # Assume the max priority score is if the max amount of captures is scheduled with the highest priority found
    maxCapturePriority = max([ttw.GT.priority for ttw in scenario.getTTWList()])
    maxPrioritySchedule = scenario.getSchedulingParameters().maxCaptures * maxCapturePriority
    # Max image quality score is an average of 90 degrees elevation
    imageQualityMax = 90
    priority = objectiveValues[0] / maxPrioritySchedule
    # TODO make the scaling of image quality clearer and easier to adjust
    imageQuality = objectiveValues[1] / imageQualityMax * 0.25
    return (priority, imageQuality)

def descaleObjectiveValues(scenario: TestScenario, scaledObjectiveValues: tuple) -> tuple:
    """ Descale the objective values from [0, 1] range back to original values """
    # Assume the max priority score is if the max amount of captures is scheduled with the highest priority found
    maxCapturePriority = max([ttw.GT.priority for ttw in scenario.getTTWList()])
    maxPrioritySchedule = scenario.getInputParameters().maxCaptures * maxCapturePriority
    # Max image quality score is an average of 90 degrees elevation
    imageQualityMax = 90
    priority = scaledObjectiveValues[0] * maxPrioritySchedule
    # TODO make the scaling of image quality clearer and easier to adjust
    imageQuality = scaledObjectiveValues[1] / 0.25 * imageQualityMax
    return (priority, imageQuality)

scenarioIds = ["1", "2"]

analyse = AnalyseTest('_H2Miss24-10')
analyse.plotParetoFrontEvolution(scenarioIndex=0, runIndex=0)
## Calculate objective values for cmd files

# pathToCp_cmd = os.path.join(os.path.dirname(__file__), "../testing/testing_results/OHH2Mission22.10_v4/H2Mission22.10_cp_cmdLine.txt")
# pathToNA_cmd = os.path.join(os.path.dirname(__file__), "../testing/testing_results/OHH2Mission22.10_v4/cmdLines/0_cmdLines.txt")

# cmdPaths = [pathToCp_cmd, pathToNA_cmd]
# for cmdPath in cmdPaths:
#     targetFilePath = os.path.join(os.path.dirname(__file__), "../data_input/HYPSO_data/targets.json")
#     pathInputParamsFile = os.path.join(os.path.dirname(__file__), "../data_input/input_parameters.csv")
#     startTimeStr = "2025-10-22T13:00:00Z"
#     oh = createOH(datetime.datetime.fromisoformat(startTimeStr), 2)
#     ip = InputParameters.from_csv(pathInputParamsFile)

#     schedule = recreateOTListFromCmdFile(targetFilePath, cmdPath, oh, ip.bufferingTime, ip.captureDuration)

#     totalPriority = objectiveFunctionPriority(schedule)
#     totalImageQuality = objectiveFunctionImageQuality(schedule, oh, int(ip.hypsoNr))
    
#     print(f"Cmd file: {cmdPath}")
#     print(f" Total Priority: {totalPriority}, and Total Image Quality: {totalImageQuality}")
        


