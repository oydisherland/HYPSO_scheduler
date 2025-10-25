import sys
import os
import json
import glob
import datetime
from dataclasses import dataclass

# Add the parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scheduling_model import SP, list_toDict, TTW_toDict, GSTW_toDict, OH_toDict, dict_toTTW, dict_toGSTW
from algorithm.NSGA2 import runNSGA
from data_preprocessing.create_data_objects import createTTWList, createOH, createGSTWList
from data_postprocessing.generate_cmdLine import createCmdFile, createCmdLinesForCaptureAndBuffering, recreateOTListFromCmdFile, recreateBTListFromCmdFile
from data_postprocessing.algorithmData_api import convertOTListToDateTime, convertBTListToDateTime, convertDTListToDateTime, getAlgorithmDatafromJsonFile, saveAlgorithmDataInJsonFile
from data_preprocessing.objective_functions import objectiveFunctionImageQuality, objectiveFunctionPriority
from transmission_scheduling.clean_schedule import cleanUpSchedule, OrderType
from transmission_scheduling.input_parameters import getTransmissionInputParams, getTransmissionInputParamsFromJsonFile
from data_input.utility_functions import InputParameters

from scheduling_model import OH

@dataclass
class TestScenario:
    
    # public attributes
    senarioID: str
    startOH: str = None
    algorithmRuns: int = None

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
    _algorithmDataAllRuns = None


    def __init__(self, senarioID: str, startOH: str = None, algorithmRuns: int = None):
        
        self.senarioID = senarioID
        if startOH is not None and algorithmRuns is not None:
            # Both OH start time and algorithm runs given
            self.startOH = startOH
            self.algorithmRuns = algorithmRuns
            
        elif startOH is None and algorithmRuns is None:
            # Algorithm runs and OH start Time not given, read from existing test folder
            testfolderPath = os.path.join(os.path.dirname(__file__), f"testing_results/OH{senarioID}")
            if not os.path.exists(testfolderPath):
                raise FileNotFoundError(f"Invalid scenarioId, no corresponding output exists.")
            
            # Find input parameters
            pathInputParamsFile = os.path.join(testfolderPath,"input_parameters.json")
            self._inputParameters = InputParameters.from_json(pathInputParamsFile)
            
            # Find start OH time
            pathOHFile = os.path.join(testfolderPath,"oh.json")
            with open(pathOHFile, "r") as f:
                ohData = json.load(f)
            self._oh = OH(
                utcStart = datetime.datetime.fromisoformat(ohData["utcStart"].replace('Z', '+00:00')),
                utcEnd = datetime.datetime.fromisoformat(ohData["utcEnd"].replace('Z', '+00:00'))
            )

            # Find number of algorithm runs
            outputfolderPath = os.path.join(testfolderPath, "cmdLines")
            self.algorithmRuns = len([name for name in os.listdir(outputfolderPath) if os.path.isfile(os.path.join(outputfolderPath, name)) and name.endswith("_cmdLines.txt")])
        
        else:
            raise ValueError("Either both startOH and algorithmRuns must be provided, or neither.")

    def setInputParameters(self, inputParameters: InputParameters):
        """ Set the input parameters for the test scenario """
        self._inputParameters = inputParameters

    def getObservationSchedules(self) -> list:
        """ Get the observation schedules for each run of the algorithm """
        return self._observationSchedules
    def getBufferSchedules(self) -> list:
        """ Get the buffer schedules for each run of the algorithm """
        return self._bufferSchedules
    def getAllObjectiveValues(self) -> list:
        """ Get the objective values for each run of the algorithm """
        return self._objectiveValues
    def getOh(self) -> OH:
        """ Get the observation horizon object """
        return self._oh
    def getInputParameters(self) -> InputParameters:
        """ Get the input parameters object """
        return self._inputParameters
    def getAlgorithmDataAllRuns(self) -> list:
        """ Get the algorithm data for each run of the algorithm """
        return self._algorithmDataAllRuns
    def getTTWList(self) -> list:
        """ Get the time to wait list """
        return self._ttwList

    # Set input attributes needed to run test scenario, either create new data or read existing data from files
    def createInputAttributes(self, inputParameterFilePath: str):
        """ Create input files for testing """

        # Read initial input parameters from cvs file
        self._inputParameters = InputParameters.from_csv(inputParameterFilePath)
        self._transmissionParameters = getTransmissionInputParams(inputParameterFilePath)


        # Create input data Objects
        self._oh = createOH(datetime.datetime.fromisoformat(self.startOH), int(self._inputParameters.durationInDaysOH))
        self._ttwList = createTTWList(int(self._inputParameters.captureDuration), self._oh, int(self._inputParameters.hypsoNr))
        self._gstwList = createGSTWList(self._oh.utcStart, self._oh.utcEnd,
                                        self._transmissionParameters.minGSWindowTime, int(self._inputParameters.hypsoNr),
                                        commInterface=self._inputParameters.commInterface)

        # Save input data in files
        folderPathTestScenario = os.path.join(os.path.dirname(__file__), f"testing_results/OH{self.senarioID}")
        os.makedirs(folderPathTestScenario, exist_ok=True)

        with open(os.path.join(folderPathTestScenario, "input_parameters.json"), "w") as f:
            f.write(self._inputParameters.to_json())
        with open(os.path.join(folderPathTestScenario, "ttw_list.json"), "w") as f:
            json.dump(list_toDict(self._ttwList, TTW_toDict), f, indent=4)
        with open(os.path.join(folderPathTestScenario, "gstw_list.json"), "w") as f:
            json.dump(list_toDict(self._gstwList, GSTW_toDict), f, indent=4)
        with open(os.path.join(folderPathTestScenario, "oh.json"), "w") as f:
            json.dump(OH_toDict(self._oh), f, indent=4)
    def recreateInputAttributes(self):
        """ Recreate input attributes from existing input files """
        folderPathOutput = os.path.join(os.path.dirname(__file__), f"testing_results/OH{self.senarioID}")
        if not os.path.exists(folderPathOutput):
            raise FileNotFoundError(f"Folder {folderPathOutput} does not exist. Cannot read existing input files.")

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
    

    # Run test: create output attributes and cmd-files for each run of the algorithm
    def runTestScenario(self):
        """ Run the algorithm and create output file for each run of the algorithm """
        # Initialize result attributes
        self._observationSchedules = []
        self._bufferSchedules = []
        self._downlinkSchedules = []
        self._objectiveValues = []
        self._algorithmDataAllRuns = []

        # Create folder to save cmd files and algorithm iteration data. 
        folderPathCmdLines = os.path.join(os.path.dirname(__file__), f"testing_results/OH{self.senarioID}/cmdLines")
        folderPathAlgorithmData = os.path.join(os.path.dirname(__file__), f"testing_results/OH{self.senarioID}/algorithmData")
        
        # If folders already exsists, remove all previous files
        if os.path.exists(folderPathCmdLines):
            files = glob.glob(os.path.join(folderPathCmdLines, "*"))
            for file in files:
                if os.path.isfile(file):
                    os.remove(file)
        else:
            os.makedirs(folderPathCmdLines, exist_ok=True)
        if os.path.exists(folderPathAlgorithmData):
            files = glob.glob(os.path.join(folderPathAlgorithmData, "*"))
            for file in files:
                if os.path.isfile(file):
                    os.remove(file)
        else:
            os.makedirs(folderPathAlgorithmData, exist_ok=True)

        # Create model parameters
        schedulingParameters = SP(int(self._inputParameters.maxCaptures), int(self._inputParameters.captureDuration), int(self._inputParameters.transitionTime), int(self._inputParameters.hypsoNr))

        # Run algorithm
        for runNr in range(self.algorithmRuns):
            # Create observation schedule. bestSchedule, bestBufferSchedule, bestDownlinkSchedule, algorithmData, bestSolution, bestIndex, oldPopulation
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
            if bufferSchedule is None or downlinkSchedule is None:
                raise ValueError("Error in transmission scheduling, no buffer or downlink schedule created.")
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
            algorithmData = (iterationData, bestIndex)
            # Save output data in files
            cmdLines = createCmdLinesForCaptureAndBuffering(observationSchedule, bufferSchedule, downlinkSchedule, self._inputParameters, self._oh)
            createCmdFile(f"{folderPathCmdLines}/{runNr}_cmdLines.txt", cmdLines)
            saveAlgorithmDataInJsonFile(f"{folderPathAlgorithmData}/{runNr}_algorithmData.json", algorithmData)

            # Calculate objective values
            totalPriority = objectiveFunctionPriority(observationSchedule)
            totalImageQuality = objectiveFunctionImageQuality(observationSchedule, self._oh, int(self._inputParameters.hypsoNr))

            # Save result in attributes
            self._observationSchedules.append(convertOTListToDateTime(observationSchedule, self._oh))
            self._bufferSchedules.append(convertBTListToDateTime(bufferSchedule, self._oh))
            self._downlinkSchedules.append(convertDTListToDateTime(downlinkSchedule, self._oh))
            self._objectiveValues.append((totalPriority, totalImageQuality))
            self._algorithmDataAllRuns.append(algorithmData)
    def runGreedyAlgorithm(self):
        """ Run the greedy algorithm and create output file for the run """
        # Initialize result attributes
        self._observationSchedules = []
        self._bufferSchedules = []
        self._downlinkSchedules = []
        self._objectiveValues = []
        self._algorithmDataAllRuns = []

       
        folderPathScenario = os.path.join(os.path.dirname(__file__), f"testing_results/OH{self.senarioID}")


        
        # Create model parameters
        schedulingParameters = SP(int(self._inputParameters.maxCaptures), int(self._inputParameters.captureDuration), int(self._inputParameters.transitionTime), int(self._inputParameters.hypsoNr))

        # Run greedy algorithm
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
            int(self._inputParameters.maxTabBank),
            greedyAlgorithm=True
        )
        if bufferSchedule is None or downlinkSchedule is None:
            raise ValueError("Error in transmission scheduling, no buffer or downlink schedule created.")
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
        createCmdFile(f"{folderPathScenario}/GA_cmdLines.txt", cmdLines)



    # If output from running test already exsists, recreate all alltributes of TestScenario object
    def recreateTestScenario(self):
        """ Recreate observation schedules from the output cmd files, and set attributes """
        folderPathOutput = os.path.join(os.path.dirname(__file__), f"testing_results/OH{self.senarioID}")

        self.recreateInputAttributes()

        # Recreate observation and buffer schedules
        obsSchedules= []
        bufSchedules = []
        downLinkSchedules = []
        for runNr in range(self.algorithmRuns):
            pathScript = os.path.join(folderPathOutput, f"cmdLines/{runNr}_cmdLines.txt")
            otList = recreateOTListFromCmdFile(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), f"data_input/HYPSO_data/targets.json"),
                pathScript,
                self._oh,
                bufferDurationSec=int(self._inputParameters.bufferingTime)
            )
            btList = recreateBTListFromCmdFile(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), f"data_input/HYPSO_data/targets.json"),
                pathScript,
                self._oh,
                bufferDurationSec=int(self._inputParameters.bufferingTime)
            )
            dtList = recreateOTListFromCmdFile(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), f"data_input/HYPSO_data/targets.json"),
                pathScript,
                self._oh,
                bufferDurationSec=0
            )
            obsSchedules.append(otList)
            bufSchedules.append(btList)
            downLinkSchedules.append(dtList)

        self._observationSchedules = obsSchedules
        self._bufferSchedules = bufSchedules
        self._downlinkSchedules = downLinkSchedules

        #Recreate objective values
        objVals = []
        for runNr in range(self.algorithmRuns):
            totalPriority = objectiveFunctionPriority(self._observationSchedules[runNr])
            totalImageQuality = objectiveFunctionImageQuality(self._observationSchedules[runNr], self._oh, int(self._inputParameters.hypsoNr))
            objVals.append((totalPriority, totalImageQuality))
        self._objectiveValues = objVals

        # Recreate iteration data
        self._algorithmDataAllRuns = []
        for runNr in range(self.algorithmRuns):
            pathAlgorithmDataFile = os.path.join(folderPathOutput, f"algorithmData/{runNr}_algorithmData.json")
            algorithmData = getAlgorithmDatafromJsonFile(pathAlgorithmDataFile)
            self._algorithmDataAllRuns.append(algorithmData)

