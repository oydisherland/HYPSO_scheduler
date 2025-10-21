import sys
import os
import json
import datetime
from dataclasses import dataclass

# Add the parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scheduling_model import SP, list_toDict, TTW_toDict, GSTW_toDict, OH_toDict, dict_toTTW, dict_toBT, dict_toOT, dict_toGT, dict_toGS, dict_toGSTW
from algorithm.NSGA2 import runNSGA
from data_preprocessing.create_data_objects import createTTWList, createOH, createGSTWList
from campaignPlanner_interaction.intergrate_campaign_planner import createCmdFile, createCmdLinesForCaptureAndBuffering, recreateOTListFromCmdFile, recreateBTListFromCmdFile
from data_preprocessing.objective_functions import objectiveFunctionImageQuality, objectiveFunctionPriority
from transmission_scheduling.clean_schedule import cleanUpSchedule, OrderType
from transmission_scheduling.input_parameters import getTransmissionInputParams, getTransmissionInputParamsFromJsonFile
from data_input.utility_functions import InputParameters

from scheduling_model import OH

@dataclass
class TestScenario:
    
    # public attributes
    SenarioID: str
    startOH: str
    algorithmRuns: int

    # private attributes used as input to the algorithm
    _inputParameters = None
    _transmissionParameters = None
    _ttwList = None
    _gstwList = None
    _oh = None

    # private result attributes created after running the test
    _observationSchedules = None
    _bufferSchedules = None
    _downlinkSchedules = None
    _objectiveValues = None

    def createInputFiles(self, inputParameterFilePath: str, groundStationFilePath: str):
        """ Create input files for testing """

        # Read initial input parameters from cvs file
        self._inputParameters = InputParameters.from_csv(inputParameterFilePath)
        self._transmissionParameters = getTransmissionInputParams(inputParameterFilePath)
        
        # Create input data Objects
        self._oh = createOH(datetime.datetime.fromisoformat(self.startOH), int(self._inputParameters.durationInDaysOH))
        self._ttwList = createTTWList(int(self._inputParameters.captureDuration), self._oh, int(self._inputParameters.hypsoNr))
        self._gstwList = createGSTWList(self._oh.utcStart, self._oh.utcEnd, self._transmissionParameters.minGSWindowTime, groundStationFilePath, int(self._inputParameters.hypsoNr))

        # Save input data in files
        folderPathTestScenario = os.path.join(os.path.dirname(__file__), f"testing_results/OH{self.SenarioID}")
        os.makedirs(folderPathTestScenario, exist_ok=True)

        with open(os.path.join(folderPathTestScenario, "input_parameters.json"), "w") as f:
            f.write(self._inputParameters.to_json())
        with open(os.path.join(folderPathTestScenario, "ttw_list.json"), "w") as f:
            json.dump(list_toDict(self._ttwList, TTW_toDict), f, indent=4)
        with open(os.path.join(folderPathTestScenario, "gstw_list.json"), "w") as f:
            json.dump(list_toDict(self._gstwList, GSTW_toDict), f, indent=4)
        with open(os.path.join(folderPathTestScenario, "oh.json"), "w") as f:
            json.dump(OH_toDict(self._oh), f, indent=4)

    def runTestScenario(self):
        """ Run the algorithm and create output file for each run of the algorithm """
        # Initialize result attributes
        self._observationSchedules = []
        self._bufferSchedules = []
        self._downlinkSchedules = []
        self._objectiveValues = []

        # Create folder to save algorithm output data
        folderPathOutput = os.path.join(os.path.dirname(__file__), f"testing_results/OH{self.SenarioID}/output")
        os.makedirs(folderPathOutput, exist_ok=True)

        # Create model parameters
        schedulingParameters = SP(int(self._inputParameters.maxCaptures), int(self._inputParameters.captureDuration), int(self._inputParameters.transitionTime), int(self._inputParameters.hypsoNr))

        # Run algorithm
        for runNr in range(self.algorithmRuns):
            # Create observation schedule. bestSchedule, bestBufferSchedule, bestDownlinkSchedule, iterationData, bestSolution, bestIndex, oldPopulation
            observationSchedule, bufferSchedule, downlinkSchedule, iterationData, bestSolution, bestIndex, _ = runNSGA(
                int(self._inputParameters.populationSize),
                int(self._inputParameters.nsga2Runs),
                self._ttwList,
                self._gstwList,
                schedulingParameters,
                self._transmissionParameters,
                self._oh,
                int(self._inputParameters.alnsRuns),
                bool(self._inputParameters.isTabooBankFIFO),
                bool(self._inputParameters.iqNonLinear),
                int(self._inputParameters.desNumber),
                int(self._inputParameters.maxTabBank)
            )
            # Clean up schedule for transmission
            bufferSchedule, downlinkSchedule = cleanUpSchedule(
                observationSchedule,
                bufferSchedule,
                downlinkSchedule,
                self._gstwList,
                self._transmissionParameters,
                OrderType.FIFO,
                OrderType.FIFO
            )
            # Save output data in files
            cmdLines = createCmdLinesForCaptureAndBuffering(observationSchedule, bufferSchedule, downlinkSchedule, self._inputParameters, self._oh)
            createCmdFile(f"{folderPathOutput}/{runNr}_cmdLines.txt", cmdLines)

            # Calculate objective values
            totalPriority = objectiveFunctionPriority(observationSchedule)
            totalImageQuality = objectiveFunctionImageQuality(observationSchedule, self._oh, int(self._inputParameters.hypsoNr))

            # Save result in attributes
            self._observationSchedules.append(observationSchedule)
            self._bufferSchedules.append(bufferSchedule)
            self._downlinkSchedules.append(downlinkSchedule)
            self._objectiveValues.append((totalPriority, totalImageQuality))

    def getAllObjectiveValues(self) -> list:
        """ Get the objective values for each run of the algorithm """
        return self._objectiveValues
    

    def recreateTestScenarioFromFiles(self):
        """ Recreate observation schedules from the output cmd files, and set attributes """
        folderPathOutput = os.path.join(os.path.dirname(__file__), f"testing_results/OH{self.SenarioID}")

        # Recreate OH from json file
        pathOHFile = os.path.join(folderPathOutput,"oh.json")
        with open(pathOHFile, "r") as f:
            ohData = json.load(f)
        self._oh = OH(
            utcStart = datetime.datetime.fromisoformat(ohData["utcStart"].replace('Z', '+00:00')),
            utcEnd = datetime.datetime.fromisoformat(ohData["utcEnd"].replace('Z', '+00:00'))
        )
        # Recreate inputParameters from json file
        pathInputParamsFile = os.path.join(folderPathOutput,"input_parameters.json")
        self._inputParameters = InputParameters.from_json(pathInputParamsFile)

        # Recreate transmissionParameters from input parameters
        self._transmissionParameters = getTransmissionInputParamsFromJsonFile(pathInputParamsFile)

        # Recreate ttwList from json file
        pathTTWListFile = os.path.join(folderPathOutput,"ttw_list.json")
        with open(pathTTWListFile, "r") as f:
            ttwData = json.load(f)
        self._ttwList = []
        for ttwElement in ttwData:
            self._ttwList.append(dict_toTTW(ttwElement))

        # Recreate gstwList from json file
        pathGSTWListFile = os.path.join(folderPathOutput,"gstw_list.json")
        with open(pathGSTWListFile, "r") as f:
            gstwData = json.load(f)
        self._gstwList = []
        for gstwElement in gstwData:
            self._gstwList.append(dict_toGSTW(gstwElement))

        # Recreate observation and buffer schedules
        obsSchedules= []
        bufSchedules = []
        for runNr in range(self.algorithmRuns):
            pathScript = os.path.join(folderPathOutput, f"output/{runNr}_cmdLines.txt")
            otList = recreateOTListFromCmdFile(
                os.path.join(os.path.dirname(__file__), f"../data_input/HYPSO_data/targets.json"),
                pathScript,
                self._oh,
                bufferDurationSec=int(self._inputParameters.bufferingTime)
            )
            btList = recreateBTListFromCmdFile(
                os.path.join(os.path.dirname(__file__), f"../data_input/HYPSO_data/targets.json"),
                pathScript,
                self._oh,
                bufferDurationSec=int(self._inputParameters.bufferingTime)
            )
            obsSchedules.append(otList)
            bufSchedules.append(btList)

        self._observationSchedules = obsSchedules
        self._bufferSchedules = bufSchedules

        #Recreate objective values
        objVals = []
        for runNr in range(self.algorithmRuns):
            totalPriority = objectiveFunctionPriority(self._observationSchedules[runNr])
            totalImageQuality = objectiveFunctionImageQuality(self._observationSchedules[runNr], self._oh, int(self._inputParameters.hypsoNr))
            objVals.append((totalPriority, totalImageQuality))
        self._objectiveValues = objVals

    def getOtLists(self) -> list:
        """ Get the observation schedules for each run of the algorithm """
        return self._observationSchedules

    def getBtLists(self) -> list:
        """ Get the buffer schedules for each run of the algorithm """
        return self._bufferSchedules