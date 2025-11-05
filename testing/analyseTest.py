
import os
import sys
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

import datetime
from dataclasses import dataclass
from test_scenario import TestScenario

from data_postprocessing.generate_cmdLine import recreateOTListFromCmdFile, recreateDTListFromCmdFile
from scheduling_model import OH
from data_input.utility_functions import InputParameters
from data_preprocessing.create_data_objects import createOH
from data_preprocessing.objective_functions import objectiveFunctionPriority, objectiveFunctionImageQuality, getIQFromOT
from data_preprocessing.parseTargetsFile import getTargetIdPriorityDictFromJson
from transmission_scheduling.util import latencyCounter
from data_postprocessing.algorithmData_api import convertDTListToRelativeTime


#plt.rcParams['text.usetex'] = True  # Optional: for LaTeX rendering
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['cmr10']  # Computer Modern Roman
plt.rcParams['mathtext.fontset'] = 'cm'  # Computer Modern for math text
plt.rcParams['axes.formatter.use_mathtext'] = True 

def scaleIQFromDegTo100(iqInDegrees: float) -> float:
    """ Scale image quality from degrees to a 0-100 scale """
    return (iqInDegrees - 40) / (90 - 40) * 100
def getDTFromImageFiles(imageFilePath: str) -> list:
    """ Get the datetime objects from image file names in the specified directory """
    imageFiles = [f for f in os.listdir(imageFilePath) if f.endswith('.png')]
    downLinkTimes = []
    targetIds = []
    for imageFile in imageFiles:
        # Extract datetime string from filename
        base = os.path.basename(imageFile)
        base_no_ext = os.path.splitext(base)[0]
        # split once at first underscore
        prefix, rest = base_no_ext.split('_', 1)
        # find the date substring that ends with Z (e.g. 2025-10-28T09-04-13Z)
        rest = rest.upper()
        m = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z)', rest)
        date_str = m.group(1) if m else None
        # parse to datetime (format uses hyphens between time fields)
        dt = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H-%M-%SZ') if date_str else None
        if dt is not None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        downLinkTimes.append(dt)
        targetIds.append(prefix)
    return zip(targetIds, downLinkTimes)

@dataclass
class AnalyseTest:
    scenarios: list[TestScenario]
    cp_observationSchedules : list[list]
    ga_observationSchedules : list[list]


    def __init__(self, scenarioIds: list):
        self.scenarios = []
        self.cp_observationSchedules = []
        self.ga_observationSchedules = []
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

            # Recreate output of scenario
            cp_cmdFilePath = os.path.join(os.path.dirname(__file__), f"../testing/testing_results/OH{scenarioId}/{scenarioId}_cp_cmdLines.txt")
            ga_cmdFilePath = os.path.join(os.path.dirname(__file__), f"../testing/testing_results/OH{scenarioId}/{scenarioId}_ga_cmdLines.txt")
            targetFilePath = scenario.getTargetsFilePath()
            oh = scenario.getOh()
            inputParameters = scenario.getInputParameters()
            # CP observation schedule
            cp_otList = recreateOTListFromCmdFile(targetFilePath, cp_cmdFilePath, oh, inputParameters.bufferingTime, inputParameters.captureDuration)
            self.cp_observationSchedules.append(cp_otList)
            # GA observation schedule   
            ga_otList = recreateOTListFromCmdFile(targetFilePath, ga_cmdFilePath, oh, inputParameters.bufferingTime, inputParameters.captureDuration)
            self.ga_observationSchedules.append(ga_otList)
               

    def plotOneschedule(self, scenarioIndex: int, runIndex: int, imageFilePath: str):
        """ Plot the observation schedule for a given scenario and run index """ 

        scenario = self.scenarios[scenarioIndex]

        otList = scenario.getObservationSchedules()[runIndex]
        btList = scenario.getBufferSchedules()[runIndex]
        dtList = convertDTListToRelativeTime(scenario.getDownlinkSchedules()[runIndex], scenario.getOh())
        gstwList = scenario.getGSTWList()
        ttwList = scenario.getTTWList()
        p = scenario.getTransmissionParameters()
        savePlotPath = True

        otListPrio = sorted(otList, key=lambda x: x.GT.priority, reverse=True)
        taskIDPrio = [ot.taskID for ot in otListPrio]
        taskIDPrio.insert(0, -1)  # So that taskID 0 is at index 1

        colors = ['#03045E', '#023E8A', '#0077B6',  '#00A8E0', '#48CAE4', '#90E0EF', '#CAF0F8']

        # Get actual downlink times from image files
        # dtActualTuples = getDTFromImageFiles(imageFilePath)
        # dtList_actual = []
        # for targetId, dt in dtActualTuples:
        #     relativeTime = (dt - scenario.getOh().utcStart).total_seconds()
        #     dtList_actual.append(relativeTime)

        dtList_actual = dtList # REMOVE THIS LATER, makes fake plot
        fig, ax = plt.subplots(figsize=(15, 3))
        
        # The sizing of the bars
        height = 0.3
        distance = 0.1
        ttw_y = 0
        ot_y = ttw_y + height / 2 + distance
        bt_y = ot_y + height + distance
        dt_y = bt_y + height + distance
        gstw_y = dt_y + height / 2 + distance
        dtA_y = gstw_y + height / 2 + distance
        
        # Target Passes, showed in dots
        dot_label_shown = False
        for ttw in ttwList:
            for tw in ttw.TWs:
                x_center = tw.start + (tw.end - tw.start) / 2
                duration = max(1.0, tw.end - tw.start)
                # Map duration to marker area (s). Adjust scaling factor if markers are too large/small.
                marker_area = max(40, (duration / max(1.0, p.ohDuration)) * 3000)
                dot_y = ttw_y   # -0.25 -> bottom of OT bars
                # show legend label only once
                lbl = "Target pass" if not dot_label_shown else None
                ax.scatter(
                    x_center,
                    dot_y,
                    s=marker_area,
                    color=colors[1],
                    alpha=0.9,
                    linewidths=0.5,
                    label=lbl
                )
                if lbl is not None:
                    dot_label_shown = True

        # Observation Tasks (blue)
        for i, ot in enumerate(otListPrio, start=1):
            w = ot.end - ot.start + 100
            ax.barh(
                y=ot_y,
                width=w,
                left=ot.start,
                height=height,
                color=colors[2],
                alpha=1,
                label="Observation Task" if i == 1 else ""
            )
            # Label under the box

        # Buffering Tasks (orange)
        for i, bt in enumerate(btList, start=1):
            ax.barh(
                y=bt_y,
                width=bt.end - bt.start,
                left=bt.start,
                height=height,
                color=colors[3],
                alpha=0.7,
                edgecolor=colors[6],
                label="BT" if i == 1 else ""
            )

        # GSTWs (green)
        counter = 1
        for gstw in gstwList:
            for tw in gstw.TWs:
                ax.barh(
                    y=gstw_y,
                    width=tw.end - tw.start,
                    left=tw.start,
                    height=height*2,
                    color=colors[6],
                    alpha=0.6,
                    label="Ground Station Pass" if counter == 1 else ""
                )
                counter += 1


        # Add DTlist plotting
        for i, dt in enumerate(dtList, start=1):
            ax.barh(
                y=dt_y,
                width=217, # 217 = downlink time, sorry should not be hardcoded
                left=dt.end - 217,
                height=height/2,
                color=colors[0],
                alpha=0.4,
                label="Estimated Downlink" if i == 1 else ""
            )
        # Add DTlist plotting
        for i, dt in enumerate(dtList_actual, start=1):
            ax.barh(
                y=dtA_y,
                width=217, # 217 = downlink time, sorry should not be hardcoded
                left=dt.end - 217, # otherwise dt
                height=height/2,
                color=colors[0],
                alpha=0.6,
                label="Actually downlinked" if i == 1 else ""
            )

        # Formatting
# increase font sizes for readability
        large_fs = 14
        med_fs = 14
        small_fs = 14       
        ax.set_xlabel('time 48h', fontsize=large_fs)
        ax.set_xticks([])   # hide numeric tick labels
        ax.set_yticks([])   # hide y ticks (targets rows)       # enlarge any tick labels (if you later enable them)
        ax.tick_params(axis='x', labelsize=small_fs)
        ax.tick_params(axis='y', labelsize=small_fs)        # place legend below the plot with larger text and a bit more space
        ax.set_xlim(-100, p.ohDuration - 1000)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=6, frameon=False, fontsize=med_fs)      # reduce padding so the figure stays compact while leaving room for the legend
        plt.tight_layout(rect=[0, 0.0, 1, 0.92])
        if savePlotPath is not None:
            out_pdf = os.path.join(os.path.dirname(__file__), f"../testing/testing_results/schedule.pdf")
            plt.savefig(out_pdf, format='pdf', bbox_inches='tight')
            plt.close()  # Close the figure to free memory
        else:
            plt.show()

    def plotObjectiveValues(self):
        """ Plot the objective values for each scenario """
        
    
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Define colors for different scenarios
        colors = ['#03045E', '#00A8E0', '#90E0EF', '#0077B6', '#CAF0F8', '#023E8A', '#EAFCFF', '#48CAE4']

        for i, (scenario, cp_otList, ga_otList) in enumerate(zip(self.scenarios, self.cp_observationSchedules, self.ga_observationSchedules)):
            # Get algorithm results
            obVals = scenario.getAllObjectiveValues()  # List of tuples (priority, imageQuality)
            
            # Get CP planner results
            cp_totalPriority = objectiveFunctionPriority(cp_otList)
            cp_totalImageQuality = objectiveFunctionImageQuality(cp_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))

            # Get GA planner results
            ga_totalPriority = objectiveFunctionPriority(ga_otList)
            ga_totalImageQuality = objectiveFunctionImageQuality(ga_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))

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
            # Plot GA planner result (triangles)
            ax.scatter(ga_totalPriority, ga_totalImageQuality, 
                    c=base_color, 
                    alpha=1, 
                    s=100, 
                    label=f'Scenario {scenario.senarioID} - GA Planner',
                    marker='^',  # Triangle marker
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
        """For each scenario create one figure containing three subplots (NSGA-II, CP, GA).
        Each subplot shows horizontal bars for targets (sorted by priority low->high)."""
        

        # Collect targets across all scenarios
        totalIQ_NA = []
        totalIQ_CP = []
        totalIQ_GA = []
        total_yPositions = []
        for scenario, cp_otList, ga_otList in zip(self.scenarios, self.cp_observationSchedules, self.ga_observationSchedules):
            targetFilePath = scenario.getTargetsFilePath()
            targetIdPriorityDict = getTargetIdPriorityDictFromJson(targetFilePath)  
            # Sort targets by priority low -> high
            sorted_targets = sorted(targetIdPriorityDict.items(), key=lambda x: x[1])
            # Prepare counts for NSGA-II (average over runs), CP and GA
            targetIdsChosenNA =  []
            imageQualityNA = []
            targetIdsChosenCP = []
            imageQualityCP = []
            targetIdsChosenGA = []
            imageQualityGA = []

            # Add target IDs is from the different schedules
            obsSchedsAllRuns = scenario.getObservationSchedules() or []

            for ot in obsSchedsAllRuns[0]: #using just the 0'th run for this plot
                # find the iq value of the observation
                imageQualityNA.append(scaleIQFromDegTo100(getIQFromOT(ot, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))))
                e = getIQFromOT(ot, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
                if e < 40:
                    e2 = getIQFromOT(ot, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
                targetIdsChosenNA.append(ot.GT.id)
            for ot in cp_otList:
                imageQualityCP.append(scaleIQFromDegTo100(getIQFromOT(ot, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))))
                targetIdsChosenCP.append(ot.GT.id)
            for ot in ga_otList:
                imageQualityGA.append(scaleIQFromDegTo100(getIQFromOT(ot, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))))
                targetIdsChosenGA.append(ot.GT.id)

            target_names = [targetID for targetID, _ in sorted_targets]
            y_positions = np.arange(len(target_names))

            allImageQualityNA, allImageQualityCP, allImageQualityGA = [], [], []
            for targetID in target_names:
                # Add the image quality if the target was chosen, else add 0
                if targetID in targetIdsChosenNA:
                    index = targetIdsChosenNA.index(targetID)
                    allImageQualityNA.append(imageQualityNA[index])
                else:
                    allImageQualityNA.append(0)

                if targetID in targetIdsChosenCP:
                    index = targetIdsChosenCP.index(targetID)
                    allImageQualityCP.append(imageQualityCP[index])
                else:
                    allImageQualityCP.append(0)

                if targetID in targetIdsChosenGA:
                    index = targetIdsChosenGA.index(targetID)
                    allImageQualityGA.append(imageQualityGA[index])
                else:
                    allImageQualityGA.append(0)

            totalIQ_NA.extend(allImageQualityNA)
            totalIQ_CP.extend(allImageQualityCP)
            totalIQ_GA.extend(allImageQualityGA)
            total_yPositions.extend(y_positions)

        fig, axes = plt.subplots(1, 3, figsize=(10, 5), sharey=True)
        if not isinstance(axes, (list, np.ndarray)):
            axes = [axes]

        algo_data = [
            ("NSGA-II", totalIQ_NA, '#00A8E0'),
            ("CP Planner", totalIQ_CP, '#00A8E0'),
            ("GA Planner", totalIQ_GA, '#00A8E0'),
        ]

        # Plot each algorithm in its own subplot
        for ax, (label, imageQuality, color) in zip(axes, algo_data):
            # Horizontal bars sorted by priority low->high (y_positions corresponds to that)
            ax.barh(total_yPositions, imageQuality, height=10, color=color, alpha=0.1)

            ax.set_xlabel('Image quality [%]', fontsize=10)
            # ax.set_xticks(range(0, 100))
            ax.set_title(label, fontsize=11, fontweight='bold')
            ax.grid(True, axis='x', alpha=0.25)


        fig.suptitle(f'Scenario {scenario.senarioID} — Target selections by algorithm', fontsize=14, fontweight='bold')
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.show()
    def plotNumberOfCapturedTargets(self):
        """ Plot the number of unique targets captured in each scenario """
        # Calculate averages for NSGA-II algorithm
        sumOfCapturesNA_averages = []
        for scenario in self.scenarios:
            obsSchedsAllRuns = scenario.getObservationSchedules()
            average = sum(len(obsSched) for obsSched in obsSchedsAllRuns) / len(obsSchedsAllRuns)
            sumOfCapturesNA_averages.append(average)
        
        # Calculate totals for CP and GA Planners
        sumOfCapturesCP = [len(cp_otList) for cp_otList in self.cp_observationSchedules]
        sumOfCapturesGA = [len(ga_otList) for ga_otList in self.ga_observationSchedules]
        
        # Prepare data for plotting
        scenario_labels = [f"Scenario {scenario.senarioID}" for scenario in self.scenarios]
        
        # Create the bar chart
        fig, ax = plt.subplots(figsize=(12, 8))
        
        x_positions = range(len(scenario_labels))
        bar_width = 0.25
        
        # Create side-by-side bars
        bars1 = ax.bar([x - bar_width for x in x_positions], sumOfCapturesNA_averages, bar_width,
                    label='NSGA-II Algorithm (Average)', color='#03045E', alpha=0.8)
        bars2 = ax.bar(x_positions, sumOfCapturesCP, bar_width,
                    label='CP Planner', color='#00A8E0', alpha=0.8)
        bars3 = ax.bar([x + bar_width for x in x_positions], sumOfCapturesGA, bar_width,
                    label='GA Planner', color='#90E0EF', alpha=0.8)
        
        # Customize the plot 
        ax.set_xlabel('Scenario', fontsize=12)
        ax.set_ylabel('Number of Captures', fontsize=12)
        ax.set_title('Number of Captures Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(scenario_labels, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for i, (na_avg, cp_count, ga_count) in enumerate(zip(sumOfCapturesNA_averages, sumOfCapturesCP, sumOfCapturesGA)):
            na_label = f'{na_avg:.0f}' if na_avg % 1 == 0 else f'{na_avg:.1f}'
            ax.text(i - bar_width, na_avg + 0.5, na_label, 
                ha='center', va='bottom', fontweight='bold')
            ax.text(i, cp_count + 0.5, str(cp_count), 
                ha='center', va='bottom', fontweight='bold')
            ax.text(i + bar_width, ga_count + 0.5, str(ga_count), 
                ha='center', va='bottom', fontweight='bold')
        
        # Force y-axis to show only integer values
        max_count = max(max(sumOfCapturesNA_averages), max(sumOfCapturesCP), max(sumOfCapturesGA))
        ax.set_ylim(0, max_count + 2)
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        
        plt.tight_layout()
        plt.show()     
    def plotNumTargIQandPriority(self):
        """ Plot the number of unique targets captured in each scenario grouped by metrics """
        
        sumOfCapturesNA, priorityNA, imageQualityNA = [], [], []
        sumOfCapturesCP, priorityCP, imageQualityCP = [], [], []
        sumOfCapturesGA, priorityGA, imageQualityGA = [], [], []

        for i, (scenario, cp_otList, ga_otList) in enumerate(zip(self.scenarios, self.cp_observationSchedules, self.ga_observationSchedules)):
            # Find sum of captures 
            obsSchedsAllRuns = scenario.getObservationSchedules()
            average = sum(len(obsSched) for obsSched in obsSchedsAllRuns) / len(obsSchedsAllRuns)

            # Find priority and image quality 
            # NA using average of all runs
            obsValuesNA = scenario.getAllObjectiveValues()
            averagePriority = sum(val[0] for val in obsValuesNA) / len(obsValuesNA)
            averageImageQuality = sum(val[1] for val in obsValuesNA) / len(obsValuesNA)
            value_priorityCP = objectiveFunctionPriority(cp_otList)
            value_imageQualityCP = objectiveFunctionImageQuality(cp_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
            value_priorityGA = objectiveFunctionPriority(ga_otList)
            value_imageQualityGA = objectiveFunctionImageQuality(ga_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
            
            #Normalize values
            maxCapture = max(average, len(cp_otList), len(ga_otList))
            maxPriority = max(averagePriority, value_priorityCP, value_priorityGA)
            maxImageQuality = max(averageImageQuality, value_imageQualityCP, value_imageQualityGA)

            # Add normalized values to list
            sumOfCapturesNA.append(average/maxCapture)
            sumOfCapturesCP.append(len(cp_otList)/maxCapture)
            sumOfCapturesGA.append(len(ga_otList)/maxCapture)
            priorityNA.append(averagePriority/maxPriority)
            priorityCP.append(value_priorityCP/maxPriority)
            priorityGA.append(value_priorityGA/maxPriority)
            imageQualityNA.append(averageImageQuality/maxImageQuality)
            imageQualityCP.append(value_imageQualityCP/maxImageQuality)
            imageQualityGA.append(value_imageQualityGA/maxImageQuality)

        # Create single plot with expanded x-axis grouped by metrics
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Colors for the three algorithms
        colors = ['#03045E', '#00A8E0', '#90E0EF']
        labels = ['NSGA-II Algorithm', 'GA Planner', 'CP Planner']
        
        # Create expanded x-axis labels grouped by metrics
        x_labels = []
        all_na_data = []
        all_ga_data = []
        all_cp_data = []
        
        # Group by metrics first, then by scenarios
        metrics = ['Captures', 'Priority', 'Image Quality']
        metric_data = {
            'Captures': (sumOfCapturesNA, sumOfCapturesGA, sumOfCapturesCP),
            'Priority': (priorityNA, priorityGA, priorityCP),
            'Image Quality': (imageQualityNA, imageQualityGA, imageQualityCP)
        }
        
        # Build data grouped by metrics
        for metric in metrics:
            na_data, ga_data, cp_data = metric_data[metric]
            
            for scenario_idx in range(len(self.scenarios)):
                scenario_id = self.scenarios[scenario_idx].senarioID
                x_labels.append(f'{scenario_id}')
                all_na_data.append(na_data[scenario_idx])
                all_ga_data.append(ga_data[scenario_idx])
                all_cp_data.append(cp_data[scenario_idx])
        
        # Bar settings - thinner bars
        x_positions = np.array(range(len(x_labels)))
        bar_width = 0.15  # Made thinner (was 0.25)
        
        # Create grouped bars
        bars1 = ax.bar(x_positions - bar_width, all_na_data, bar_width,
                    label=labels[0], color=colors[0], alpha=0.8)
        bars2 = ax.bar(x_positions, all_ga_data, bar_width,
                    label=labels[1], color=colors[1], alpha=0.8)
        bars3 = ax.bar(x_positions + bar_width, all_cp_data, bar_width,
                    label=labels[2], color=colors[2], alpha=0.8)
        
        # Customize the plot
        ax.set_xlabel('Scenarios', fontsize=12)
        ax.set_ylabel('Normalized Values', fontsize=12)
        ax.set_title('Performance Comparison Grouped by Metrics', 
                    fontsize=14, fontweight='bold')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=10)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, 1.1)
        
        # Add value labels on bars (smaller font)
        for i, (na_val, ga_val, cp_val) in enumerate(zip(all_na_data, all_ga_data, all_cp_data)):
            ax.text(i - bar_width, na_val + 0.02, f'{na_val:.2f}', 
                ha='center', va='bottom', fontweight='bold', fontsize=7)
            ax.text(i, ga_val + 0.02, f'{ga_val:.2f}', 
                ha='center', va='bottom', fontweight='bold', fontsize=7)
            ax.text(i + bar_width, cp_val + 0.02, f'{cp_val:.2f}', 
                ha='center', va='bottom', fontweight='bold', fontsize=7)
        
        # Add vertical lines and metric labels to separate metric groups
        num_scenarios = len(self.scenarios)
        for i, metric in enumerate(metrics):
            # Add metric label above the group
            group_center = i * num_scenarios + (num_scenarios - 1) / 2
            ax.text(group_center, 1.05, metric, ha='center', va='bottom', 
                fontsize=14, fontweight='bold', 
                bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.7))
            
            # Add vertical separator after each metric group (except the last)
            if i < len(metrics) - 1:
                separator_position = (i + 1) * num_scenarios - 0.5
                ax.axvline(x=separator_position, color='gray', linestyle='--', alpha=0.7, linewidth=2)

        plt.tight_layout()
        plt.show()
    def plotNumTargIQandPriorityAverage(self):
        """ Plot the average number of targets, priority, and image quality across all scenarios """
        
        # Collect data for all scenarios
        all_sumOfCapturesNA, all_priorityNA, all_imageQualityNA = [], [], []
        all_sumOfCapturesCP, all_priorityCP, all_imageQualityCP = [], [], []
        all_sumOfCapturesGA, all_priorityGA, all_imageQualityGA = [], [], []

        for i, (scenario, cp_otList, ga_otList) in enumerate(zip(self.scenarios, self.cp_observationSchedules, self.ga_observationSchedules)):
            # Find sum of captures 
            obsSchedsAllRuns = scenario.getObservationSchedules()
            average = sum(len(obsSched) for obsSched in obsSchedsAllRuns) / len(obsSchedsAllRuns)

            # Find priority and image quality 
            # NA using average of all runs
            obsValuesNA = scenario.getAllObjectiveValues()
            value_priorityNA = sum(val[0] for val in obsValuesNA) / len(obsValuesNA)
            value_imageQualityNA = sum(val[1] for val in obsValuesNA) / len(obsValuesNA)
            value_priorityCP = objectiveFunctionPriority(cp_otList)
            value_imageQualityCP = objectiveFunctionImageQuality(cp_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
            value_priorityGA = objectiveFunctionPriority(ga_otList)
            value_imageQualityGA = objectiveFunctionImageQuality(ga_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))

            # Scale IQ so that 0-1 maps 40 degrees to 90 degrees
            value_imageQualityNA = scaleIQFromDegTo100(value_imageQualityNA)
            value_imageQualityCP = scaleIQFromDegTo100(value_imageQualityCP)
            value_imageQualityGA = scaleIQFromDegTo100(value_imageQualityGA)

            #Normalize values
            maxCapture = max(average, len(cp_otList), len(ga_otList))
            maxPriority = max(value_priorityNA, value_priorityCP, value_priorityGA)
            maxImageQuality = max(value_imageQualityNA, value_imageQualityCP, value_imageQualityGA)

            # Add normalized values to lists
            all_sumOfCapturesNA.append(average/maxCapture)
            all_sumOfCapturesCP.append(len(cp_otList)/maxCapture)
            all_sumOfCapturesGA.append(len(ga_otList)/maxCapture)
            all_priorityNA.append(value_priorityNA/maxPriority)
            all_priorityCP.append(value_priorityCP/maxPriority)
            all_priorityGA.append(value_priorityGA/maxPriority)
            all_imageQualityNA.append(value_imageQualityNA/maxImageQuality)
            all_imageQualityCP.append(value_imageQualityCP/maxImageQuality)
            all_imageQualityGA.append(value_imageQualityGA/maxImageQuality)

        # Calculate averages and standard deviations across all scenarios
        metrics = ['Captures', 'Priority', 'Image Quality']
        
        # Average values for each algorithm
        na_averages = [
            np.mean(all_sumOfCapturesNA),
            np.mean(all_priorityNA),
            np.mean(all_imageQualityNA)
        ]
        ga_averages = [
            np.mean(all_sumOfCapturesGA),
            np.mean(all_priorityGA),
            np.mean(all_imageQualityGA)
        ]
        cp_averages = [
            np.mean(all_sumOfCapturesCP),
            np.mean(all_priorityCP),
            np.mean(all_imageQualityCP)
        ]
        
        # Standard deviations for error bars
        na_stds = [
            np.std(all_sumOfCapturesNA),
            np.std(all_priorityNA),
            np.std(all_imageQualityNA)
        ]
        ga_stds = [
            np.std(all_sumOfCapturesGA),
            np.std(all_priorityGA),
            np.std(all_imageQualityGA)
        ]
        cp_stds = [
            np.std(all_sumOfCapturesCP),
            np.std(all_priorityCP),
            np.std(all_imageQualityCP)
        ]

        # Create single plot with averages
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Colors for the three algorithms
        colors = ['#03045E', '#00A8E0', '#90E0EF']
        labels = ['NSGA-II Algorithm', 'GA Planner', 'CP Planner']
        
        # Bar settings
        x_positions = np.array(range(len(metrics)))
        bar_width = 0.25
        
        # Create grouped bars with error bars
        bars1 = ax.bar(x_positions - bar_width, na_averages, bar_width,
                    yerr=na_stds, capsize=5,
                    label=labels[0], color=colors[0], alpha=0.8)
        bars2 = ax.bar(x_positions, ga_averages, bar_width,
                    yerr=ga_stds, capsize=5,
                    label=labels[1], color=colors[1], alpha=0.8)
        bars3 = ax.bar(x_positions + bar_width, cp_averages, bar_width,
                    yerr=cp_stds, capsize=5,
                    label=labels[2], color=colors[2], alpha=0.8)
        
        # Customize the plot
        ax.set_xlabel('Metrics', fontsize=12)
        ax.set_ylabel('Normalized Values', fontsize=12)
        ax.set_title(f'Average Performance Across {len(self.scenarios)} Scenarios', 
                    fontsize=14, fontweight='bold')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(metrics, rotation=0, ha='center')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, 1.1)
        
        # Add value labels on bars
        for i, (na_val, ga_val, cp_val) in enumerate(zip(na_averages, ga_averages, cp_averages)):
            ax.text(i - bar_width, na_val + na_stds[i] + 0.02, f'{na_val:.2f}', 
                ha='center', va='bottom', fontweight='bold', fontsize=9)
            ax.text(i, ga_val + ga_stds[i] + 0.02, f'{ga_val:.2f}', 
                ha='center', va='bottom', fontweight='bold', fontsize=9)
            ax.text(i + bar_width, cp_val + cp_stds[i] + 0.02, f'{cp_val:.2f}', 
                ha='center', va='bottom', fontweight='bold', fontsize=9)

        plt.tight_layout()
        plt.show()
    def plotGraphNumTargIQandPrioritySubplots(self):
        """ Plot the average number of targets, priority, and image quality as line plots with standard deviation """
        
        # Collect data for all scenarios 
        all_sumOfCapturesNA, all_priorityNA, all_imageQualityNA = [], [], []
        all_sumOfCapturesCP, all_priorityCP, all_imageQualityCP = [], [], []
        all_sumOfCapturesGA, all_priorityGA, all_imageQualityGA = [], [], []

        for i, (scenario, cp_otList, ga_otList) in enumerate(zip(self.scenarios, self.cp_observationSchedules, self.ga_observationSchedules)):
            # Find sum of captures 
            obsSchedsAllRuns = scenario.getObservationSchedules()
            average = sum(len(obsSched) for obsSched in obsSchedsAllRuns) / len(obsSchedsAllRuns)

            # Find priority and image quality 
            # NA using average of all runs
            obsValuesNA = scenario.getAllObjectiveValues()
            value_priorityNA = sum(val[0] for val in obsValuesNA) / len(obsValuesNA)
            value_imageQualityNA = sum(val[1] for val in obsValuesNA) / len(obsValuesNA)
            value_priorityCP = objectiveFunctionPriority(cp_otList)
            value_imageQualityCP = objectiveFunctionImageQuality(cp_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
            value_priorityGA = objectiveFunctionPriority(ga_otList)
            value_imageQualityGA = objectiveFunctionImageQuality(ga_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))

            # Scale IQ so that 0-1 maps 40 degrees to 90 degrees
            value_imageQualityNA = (value_imageQualityNA - 40) / (90 - 40) 
            value_imageQualityCP = (value_imageQualityCP - 40) / (90 - 40) 
            value_imageQualityGA = (value_imageQualityGA - 40) / (90 - 40) 

            #Normalize values
            maxCapture = max(average, len(cp_otList), len(ga_otList))
            maxPriority = max(value_priorityNA, value_priorityCP, value_priorityGA)
            maxImageQuality = max(value_imageQualityNA, value_imageQualityCP, value_imageQualityGA)

            # Add normalized values to lists
            all_sumOfCapturesNA.append(average/maxCapture)
            all_sumOfCapturesCP.append(len(cp_otList)/maxCapture)
            all_sumOfCapturesGA.append(len(ga_otList)/maxCapture)
            all_priorityNA.append(value_priorityNA/maxPriority)
            all_priorityCP.append(value_priorityCP/maxPriority)
            all_priorityGA.append(value_priorityGA/maxPriority)
            all_imageQualityNA.append(value_imageQualityNA/maxImageQuality)
            all_imageQualityCP.append(value_imageQualityCP/maxImageQuality)
            all_imageQualityGA.append(value_imageQualityGA/maxImageQuality)
        
                # determine number of subplots (one per scenario)
        n = len(all_sumOfCapturesNA)
        if n == 0:
            return

        # layout: try to fit into a row up to 3 cols
        max_cols = 3
        ncols = min(n, max_cols)
        nrows = int(np.ceil(n / ncols))
        # create subplots with zero horizontal spacing between axes
        per_col_width = 2.0   # smaller width per subplot (reduce to make plot narrower)
        per_row_height = 3.0
        fig_width = max(6, per_col_width * ncols)   # ensure a minimum width
        fig_height = per_row_height * nrows
        fig, axes = plt.subplots(nrows, ncols,
                                 figsize=(fig_width, fig_height),
                                 sharey=True,
                                 gridspec_kw={'wspace': 0, 'hspace': 0.15})
        axes = np.array(axes).reshape(-1)  # flatten
         # set y-axis tick label font size for all subplots
        y_tick_fs = 14
        for a in axes:
            a.tick_params(axis='y', labelsize=y_tick_fs)
            for lbl in a.get_xticklabels() + a.get_yticklabels():
                lbl.set_bbox(dict(facecolor='white', edgecolor='none', alpha=0.5,pad=1))

        # remove y tick labels on all subplots except the first column to avoid clutter
        # for idx, a in enumerate(axes):
        #     if (idx % ncols) != 0 and idx != 3:
        #         a.set_yticklabels([])
        #         a.set_ylabel('')

        # tighten left/right margins so plots butt up against each other
        fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.06)
        metrics = ['C', 'P', 'IQ']
        x = np.arange(len(metrics))
        bar_width = 0.22

        colors = {'NA': '#03045E', 'GA': '#00A8E0', 'CP': '#90E0EF'}
        scenario_titles = ['W2', 'W4', 'W6', 'E2', 'E4', 'E6']
        for i in range(n):
            ax = axes[i]
            na_vals = [all_sumOfCapturesNA[i], all_priorityNA[i], all_imageQualityNA[i]]
            ga_vals = [all_sumOfCapturesGA[i], all_priorityGA[i], all_imageQualityGA[i]]
            cp_vals = [all_sumOfCapturesCP[i], all_priorityCP[i], all_imageQualityCP[i]]

            ax.bar(x - bar_width, na_vals, bar_width, label='ALNS+NSGA-II', color=colors['NA'], alpha=0.8, edgecolor='k', linewidth=0.4)
            ax.bar(x, ga_vals, bar_width, label='Greedy1', color=colors['GA'], alpha=0.8, edgecolor='k', linewidth=0.4)
            ax.bar(x + bar_width, cp_vals, bar_width, label='Greedy2', color=colors['CP'], alpha=0.8, edgecolor='k', linewidth=0.4)

            if i == 0 or i == 3:
                ax.set_ylabel('Normalized Score', fontsize=14)
            
            ax.set_xticks(x)
            # show metric tick labels only on bottom row and place them inside the plot

            ax.set_xticklabels(metrics, rotation=0, fontsize=14)
            # move the tick labels into the axes (negative pad)
            ax.tick_params(axis='x', labelsize=14, pad=-20)

            ax.set_ylim(0, 1.05)
            ax.grid(True, axis='y', alpha=0.25)

            scen = self.scenarios[i]
            ax.set_title(f'Scenario {scenario_titles[i]}', fontsize=14, fontweight='bold')

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, 0.08), ncols=3, fontsize=14)
        # reserve right margin so external legend is not clipped
        fig.subplots_adjust(bottom=0.18)
        # add explanatory text block below the legend
        fig.text(
            0.5,                      # x (center)
            0.04,                     # y (slightly above bottom)
            "C: number of captures, P: priority objective, IQ: image quality objective",
            ha='center',
            va='center',
            wrap=True,
            fontsize=13,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.0)
        )
        # Save plot in file
        out_pdf = os.path.join(os.path.dirname(__file__), f"../testing/testing_results/barPlot.pdf")
        fig.savefig(out_pdf, format='pdf', bbox_inches='tight')
        plt.show()
    def plotGraphNumTargIQandPriorityAverages(self):
        """ Plot the average number of targets, priority, and image quality as line plots with standard deviation """
        
        # Collect data for all scenarios 
        all_sumOfCapturesNA, all_priorityNA, all_imageQualityNA = [], [], []
        all_sumOfCapturesCP, all_priorityCP, all_imageQualityCP = [], [], []
        all_sumOfCapturesGA, all_priorityGA, all_imageQualityGA = [], [], []

        for i, (scenario, cp_otList, ga_otList) in enumerate(zip(self.scenarios, self.cp_observationSchedules, self.ga_observationSchedules)):
            # Find sum of captures 
            obsSchedsAllRuns = scenario.getObservationSchedules()
            average = sum(len(obsSched) for obsSched in obsSchedsAllRuns) / len(obsSchedsAllRuns)

            # Find priority and image quality 
            # NA using average of all runs
            obsValuesNA = scenario.getAllObjectiveValues()
            value_priorityNA = sum(val[0] for val in obsValuesNA) / len(obsValuesNA)
            value_imageQualityNA = sum(val[1] for val in obsValuesNA) / len(obsValuesNA)
            value_priorityCP = objectiveFunctionPriority(cp_otList)
            value_imageQualityCP = objectiveFunctionImageQuality(cp_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
            value_priorityGA = objectiveFunctionPriority(ga_otList)
            value_imageQualityGA = objectiveFunctionImageQuality(ga_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))

            # Scale IQ so that 0-1 maps 40 degrees to 90 degrees
            value_imageQualityNA = (value_imageQualityNA - 40) / (90 - 40) 
            value_imageQualityCP = (value_imageQualityCP - 40) / (90 - 40) 
            value_imageQualityGA = (value_imageQualityGA - 40) / (90 - 40) 

            #Normalize values
            maxCapture = max(average, len(cp_otList), len(ga_otList))
            maxPriority = max(value_priorityNA, value_priorityCP, value_priorityGA)
            maxImageQuality = max(value_imageQualityNA, value_imageQualityCP, value_imageQualityGA)

            # Add normalized values to lists
            all_sumOfCapturesNA.append(average/maxCapture)
            all_sumOfCapturesCP.append(len(cp_otList)/maxCapture)
            all_sumOfCapturesGA.append(len(ga_otList)/maxCapture)
            all_priorityNA.append(value_priorityNA/maxPriority)
            all_priorityCP.append(value_priorityCP/maxPriority)
            all_priorityGA.append(value_priorityGA/maxPriority)
            all_imageQualityNA.append(value_imageQualityNA/maxImageQuality)
            all_imageQualityCP.append(value_imageQualityCP/maxImageQuality)
            all_imageQualityGA.append(value_imageQualityGA/maxImageQuality)
            all_priorityPCapNA = [priority / numCaptures for priority, numCaptures in zip(all_priorityNA, all_sumOfCapturesNA)]
            all_priorityPCapCP = [priority / numCaptures for priority, numCaptures in zip(all_priorityCP, all_sumOfCapturesCP)]
            all_priorityPCapGA = [priority / numCaptures for priority, numCaptures in zip(all_priorityGA, all_sumOfCapturesGA)]

        # Calculate means and standard deviations across all scenarios
        # metrics = ['Captures', 'Priority', 'Priority per Capture', 'Image Quality']
        metrics = ['Captures', 'Priority', 'Image Quality']
        x_positions = range(len(metrics))
        
        # NSGA-II data
        na_means = [
            np.mean(all_sumOfCapturesNA),
            np.mean(all_priorityNA),
            np.mean(all_imageQualityNA),
            # np.mean(all_priorityPCapNA)
        ]
        na_stds = [
            np.std(all_sumOfCapturesNA),
            np.std(all_priorityNA),
            np.std(all_imageQualityNA),
            # np.std(all_priorityPCapNA)  
        ]
        
        # GA Planner data
        ga_means = [
            np.mean(all_sumOfCapturesGA),
            np.mean(all_priorityGA),
            np.mean(all_imageQualityGA),
            # np.mean(all_priorityPCapGA)
        ]
        ga_stds = [
            np.std(all_sumOfCapturesGA),
            np.std(all_priorityGA),
            np.std(all_imageQualityGA),
            # np.std(all_priorityPCapGA)
        ]
        
        # CP Planner data
        cp_means = [
            np.mean(all_sumOfCapturesCP),
            np.mean(all_priorityCP),
            np.mean(all_imageQualityCP),
            # np.mean(all_priorityPCapCP)
        ]
        cp_stds = [
            np.std(all_sumOfCapturesCP),
            np.std(all_priorityCP),
            np.std(all_imageQualityCP),
            # np.std(all_priorityPCapCP)
        ]

        # Create the combined plot
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Colors and styles for the three algorithms
        colors = ['#03045E', '#00A8E0', '#90E0EF']
        line_styles = ['-', '--', '-.']
        markers = ['o', 's', '^']
        labels = ['NSGA-II Algorithm', 'GA Planner', 'CP Planner']
        
        # Plot lines with error bands
        # NSGA-II
        ax.plot(x_positions, na_means, 
                color=colors[0], linestyle=line_styles[0], marker=markers[0],
                linewidth=3, markersize=10, alpha=0.9,
                label=labels[0])
        ax.fill_between(x_positions, 
                        np.array(na_means) - np.array(na_stds),
                        np.array(na_means) + np.array(na_stds),
                        color=colors[0], alpha=0.2)
        
        # GA Planner
        ax.plot(x_positions, ga_means, 
                color=colors[1], linestyle=line_styles[1], marker=markers[1],
                linewidth=3, markersize=10, alpha=0.9,
                label=labels[1])
        ax.fill_between(x_positions, 
                        np.array(ga_means) - np.array(ga_stds),
                        np.array(ga_means) + np.array(ga_stds),
                        color=colors[1], alpha=0.2)
        
        # CP Planner
        ax.plot(x_positions, cp_means, 
                color=colors[2], linestyle=line_styles[2], marker=markers[2],
                linewidth=3, markersize=10, alpha=0.9,
                label=labels[2])
        ax.fill_between(x_positions, 
                        np.array(cp_means) - np.array(cp_stds),
                        np.array(cp_means) + np.array(cp_stds),
                        color=colors[2], alpha=0.2)
        
        # Add value labels on points
        # for i, (na_mean, ga_mean, cp_mean) in enumerate(zip(na_means, ga_means, cp_means)):
        #     ax.text(i, na_mean + 0.05, f'{na_mean:.2f}±{na_stds[i]:.2f}', 
        #         ha='center', va='bottom', fontweight='bold', fontsize=9, color=colors[0])
        #     ax.text(i, ga_mean + 0.05, f'{ga_mean:.2f}±{ga_stds[i]:.2f}', 
        #         ha='center', va='bottom', fontweight='bold', fontsize=9, color=colors[1])
        #     ax.text(i, cp_mean + 0.05, f'{cp_mean:.2f}±{cp_stds[i]:.2f}', 
        #         ha='center', va='bottom', fontweight='bold', fontsize=9, color=colors[2])
        
        # Customize the plot
        ax.set_xlabel('Metrics', fontsize=14)
        ax.set_ylabel('Normalized Values', fontsize=14)
        ax.set_title(f'Average Performance Across {len(self.scenarios)} Scenarios', 
                    fontsize=16, fontweight='bold')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(metrics, rotation=0, ha='center')
        ax.legend(fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Set y-axis limits with some padding for labels
        all_values = na_means + ga_means + cp_means
        all_stds = na_stds + ga_stds + cp_stds
        max_val = max(np.array(all_values) + np.array(all_stds))
        min_val = min(np.array(all_values) - np.array(all_stds))
        # ax.set_ylim(max(0, min_val - 0.1), max_val + 0.15)
        
        # Set x-axis limits to center the points
        ax.set_xlim(-0.3, len(metrics) - 0.7)

        plt.tight_layout()
        plt.show()
    def plotParetoFrontEvolution(self, scenarioIndex: int, runIndex: int):
        """ Plot the evolution of the Pareto front for each scenario """
        
        #Extract the data for the spesific scenario and run
        scenario = self.scenarios[scenarioIndex]
        algDataAllRuns = scenario.getAlgorithmDataAllRuns()
        algData = algDataAllRuns[runIndex]  
        iterationData, bestIndex, = algData
        kneePoint = scenario.getAllObjectiveValues()[runIndex]

        # different approch
        p_val = objectiveFunctionPriority(scenario.getObservationSchedules()[runIndex])
        iq_val = objectiveFunctionImageQuality(scenario.getObservationSchedules()[runIndex], scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
        kneePoint = (p_val, iq_val)
       # Calculate objective values for CP and GA planners
        cp_otList = self.cp_observationSchedules[scenarioIndex]
        ga_otList = self.ga_observationSchedules[scenarioIndex]
        
        cp_priority = objectiveFunctionPriority(cp_otList)
        cp_imageQuality = objectiveFunctionImageQuality(cp_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
        cpOVPoints = (cp_priority, scaleIQFromDegTo100(cp_imageQuality))
        
        ga_priority = objectiveFunctionPriority(ga_otList)
        ga_imageQuality = objectiveFunctionImageQuality(ga_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
        gaOVPoints = (ga_priority, scaleIQFromDegTo100(ga_imageQuality))
       
        # Create the plot
        fig, ax = plt.subplots(figsize=(7, 6))
        
        font_size = 14  # set all text to size 14
        
        # Create a colormap for different iterations
        num_iterations = len(iterationData)
        custom_colors = ['#03045E', '#023E8A', '#0077B6', '#00A8E0', '#48CAE4', '#90E0EF']

        # Create a custom colormap
        custom_cmap = LinearSegmentedColormap.from_list("custom_blues", custom_colors)
        colors = custom_cmap(np.linspace(0, 1, num_iterations))
        
        for iteration in range(num_iterations):
            _, _, _, paretoFrontOtlists= iterationData[iteration]
            
            # Get the Pareto front (first front)
            if len(paretoFrontOtlists) > 0:

                # Extract priorities and image qualities
                priorities = [objectiveFunctionPriority(otList) for otList in paretoFrontOtlists]
                image_qualities = [scaleIQFromDegTo100(objectiveFunctionImageQuality(otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))) for otList in paretoFrontOtlists]
                
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
                    # Plot a big circle around the knee point
                    iq = scaleIQFromDegTo100(kneePoint[1])
                    ax.scatter(kneePoint[0], iq, 
                            facecolors='none',
                            edgecolors=colors[1],  # circle for visibility
                            s=200,  # Large size
                            linewidth=3,  # Thick edge
                            marker='o',
                            label='Knee Point')
        # Add CP planner point
        ax.scatter(cpOVPoints[0], cpOVPoints[1], 
                c=custom_colors[0], 
                alpha=1, 
                s=100, 
                label='Greedy2',
                marker='s',  # Square marker
                linewidth=1)
        
        # Add GA planner point
        ax.scatter(gaOVPoints[0], gaOVPoints[1], 
                c=custom_colors[0], 
                alpha=1, 
                s=100, 
                label='Greedy1',
                marker='^',  # Triangle marker
                linewidth=1)
        
        # Customize the plot (use font_size for all text)
        ax.set_xlabel('Priority', fontsize=font_size)
        ax.set_ylabel('Image Quality [1-100]', fontsize=font_size)
        ax.tick_params(axis='both', which='major', labelsize=font_size)
        ax.grid(True, alpha=0.3)
        
        # Handle legend - only show every nth iteration if there are too many
        handles, labels = ax.get_legend_handles_labels()
        if len(labels) > 10:  # If more than 10 iterations, show every 5th
            step = max(1, len(labels) // 10)
            handles = handles[::step]
            labels = labels[::step]

        ax.legend(handles, labels, bbox_to_anchor=(0.5, -0.5), loc='lower center', ncols=3, fontsize=font_size)
        # plt.tight_layout()
        out_pdf = os.path.join(os.path.dirname(__file__), f"../testing/testing_results/paretoFronts_{scenarioIndex}.pdf")
        fig.savefig(out_pdf, format='pdf', bbox_inches='tight')
        # plt.show()
    def plotParetoFrontCompared(self, scenarioIndex: int, runIndex: int):
        """ Plot the Pareto front compared with CP and GA planners """
        
        #Extract the data for the specific scenario and run
        scenario = self.scenarios[scenarioIndex]
        algDataAllRuns = scenario.getAlgorithmDataAllRuns()
        algData = algDataAllRuns[runIndex]  
        iterationData, bestIndex, finalPopulation = algData
        fronts, _, _ = iterationData[-1]

        otListsInParetoFront = [finalPopulation[index] for index in fronts[0]]
        bestOT = finalPopulation[bestIndex]

        # Calculate objective values for Pareto front points
        finalPopulationOVPoints = []
        for otList in otListsInParetoFront:
            priority = objectiveFunctionPriority(otList)
            imageQuality = objectiveFunctionImageQuality(otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
            finalPopulationOVPoints.append((priority, imageQuality))
        
        # Calculate objective values for CP and GA planners
        cp_otList = self.cp_observationSchedules[scenarioIndex]
        ga_otList = self.ga_observationSchedules[scenarioIndex]
        
        cp_priority = objectiveFunctionPriority(cp_otList)
        cp_imageQuality = objectiveFunctionImageQuality(cp_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
        cpOVPoints = (cp_priority, cp_imageQuality)
        
        ga_priority = objectiveFunctionPriority(ga_otList)
        ga_imageQuality = objectiveFunctionImageQuality(ga_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
        gaOVPoints = (ga_priority, ga_imageQuality)
        
        # Calculate objective values for the best solution
        best_priority = objectiveFunctionPriority(bestOT)
        best_imageQuality = objectiveFunctionImageQuality(bestOT, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))

        # Create the plot
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot Pareto front points
        if finalPopulationOVPoints:
            pareto_priorities = [point[0] for point in finalPopulationOVPoints]
            pareto_imageQualities = [point[1] for point in finalPopulationOVPoints]
            ax.scatter(pareto_priorities, pareto_imageQualities, 
                    c='#03045E', 
                    alpha=0.7, 
                    s=50, 
                    label='NSGA-II Pareto Front',
                    marker='o')
        
        # Plot CP planner point
        ax.scatter(cpOVPoints[0], cpOVPoints[1], 
                c='#00A8E0', 
                alpha=1, 
                s=100, 
                label='CP Planner',
                marker='s',  # Square marker
                edgecolors='black',
                linewidth=1)
        
        # Plot GA planner point
        ax.scatter(gaOVPoints[0], gaOVPoints[1], 
                c='#90E0EF', 
                alpha=1, 
                s=100, 
                label='GA Planner',
                marker='^',  # Triangle marker
                edgecolors='black',
                linewidth=1)
        
        # Plot best solution (knee point) with a circle around it
        ax.scatter(best_priority, best_imageQuality, 
                facecolors='none',
                edgecolors='red',  # Red circle for visibility
                s=200,  # Large size
                linewidth=3,  # Thick edge
                marker='o',
                label='Best Solution (Knee Point)')

        # Customize the plot
        ax.set_xlabel('Priority', fontsize=12)
        ax.set_ylabel('Image Quality', fontsize=12)
        ax.set_title(f'Pareto Front Comparison - Scenario {scenario.senarioID}, Run {runIndex + 1}', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        plt.show()
    
    def getdata(self):
        filePath = os.path.join(os.path.dirname(__file__), f"../testing/testing_results/data_tests.txt")

        data = []
        for scenario, cp_otList, ga_otList in zip(self.scenarios, self.cp_observationSchedules, self.ga_observationSchedules):
            # Find sum of captures 
            obsSchedsAllRuns = scenario.getObservationSchedules()
            average = sum(len(obsSched) for obsSched in obsSchedsAllRuns) / len(obsSchedsAllRuns)

            # Find priority and image quality 
            # NA using average of all runs
            obsValuesNA = scenario.getAllObjectiveValues()
            value_priorityNA = sum(val[0] for val in obsValuesNA) / len(obsValuesNA)
            value_imageQualityNA = sum(val[1] for val in obsValuesNA) / len(obsValuesNA)
            value_priorityCP = objectiveFunctionPriority(cp_otList)
            value_imageQualityCP = objectiveFunctionImageQuality(cp_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))
            value_priorityGA = objectiveFunctionPriority(ga_otList)
            value_imageQualityGA = objectiveFunctionImageQuality(ga_otList, scenario.getOh(), int(scenario.getInputParameters().hypsoNr))

            # Scale IQ so that 0-1 maps 40 degrees to 90 degrees
            value_imageQualityNA = round(scaleIQFromDegTo100(value_imageQualityNA), 2)
            value_imageQualityCP = round(scaleIQFromDegTo100(value_imageQualityCP), 2)
            value_imageQualityGA = round(scaleIQFromDegTo100(value_imageQualityGA), 2)

            data.append({
                "scenarioID": scenario.senarioID,
                "captures_NA": average,
                "priority_NA": value_priorityNA,
                "imageQuality_NA": value_imageQualityNA,
                "captures_CP": len(cp_otList),
                "priority_CP": value_priorityCP,
                "imageQuality_CP": value_imageQualityCP,
                "captures_GA": len(ga_otList),
                "priority_GA": value_priorityGA,
                "imageQuality_GA": value_imageQualityGA
            })
        
        # write to file
        with open(filePath, 'w') as f:
            for scenarioData in data:
                f.write(str(scenarioData["scenarioID"]) + " | " + str(scenarioData["captures_NA"]) + " | " + str(scenarioData["priority_NA"]) + " | " + str(scenarioData["imageQuality_NA"]) + "\n")
                f.write(str(scenarioData["scenarioID"]) + " | " + str(scenarioData["captures_CP"]) + " | " + str(scenarioData["priority_CP"]) + " | " + str(scenarioData["imageQuality_CP"]) + "\n")
                f.write(str(scenarioData["scenarioID"]) + " | " + str(scenarioData["captures_GA"]) + " | " + str(scenarioData["priority_GA"]) + " | " + str(scenarioData["imageQuality_GA"]) + "\n")





scenarioIds = ["_H2Miss26-10", "_H2Miss27-10", "_H2Miss28-10"]
scenarioIds1 = ["27"]
scenarioIds2 = ["mission27_v2"]
scenarioIdCCheck = [ "e4", "e6"]
allScenarioIds = scenarioIds + scenarioIds1 + scenarioIds2 + scenarioIdCCheck
scenarioIds_cl = [ "cl_5", "cl_6", "cl_5"]
test = ['g2', 'g4', 'g6', 'e2', 'e4', 'e6']

filename27_10 = "/Users/oydisherland/Documents/OBD scheduling paper/Testing/27-10/images"

analyse = AnalyseTest(test)
analyse.plotParetoFrontEvolution(scenarioIndex=2, runIndex=0)
# analyse.plotObjectiveValues()
# analyse.plotNumberOfCapturedTargets()
# analyse.plotNumTargIQandPriority()
# analyse.plotNumTargIQandPriorityAverage()
# analyse.plotGraphNumTargIQandPrioritySubplots()
# analyse.plotGraphNumTargIQandPriorityAverages()
# analyse.plotTargetsChosen()
# analyse.plotOneschedule(scenarioIndex=0, runIndex=0, imageFilePath=filename27_10)
# analyse.getdata()



