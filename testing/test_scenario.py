import sys
import os
import json
import datetime
from dataclasses import dataclass

# Add the parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scheduling_model import SP, list_toDict, TTW_toDict, GSTW_toDict, OH_toDict
from algorithm.NSGA2 import runNSGA
from data_preprocessing.create_data_objects import createTTWList, createOH, createGSTWList
from campaignPlanner_interaction.intergrate_campaign_planner import createCmdFile, createCmdLinesForCaptureAndBuffering, recreateOTListFromCmdFile

from transmission_scheduling.clean_schedule import cleanUpSchedule, OrderType
from transmission_scheduling.input_parameters import getTransmissionInputParams
from data_input.utility_functions import InputParameters

@dataclass
class TestScenario:
    
    # public attributes
    SenarioID: str
    startOH: str
    algorithmRuns: int

    # private attributes
    _inputParameters = None
    _transmissionParameters = None
    _ttwList = None
    _gstwList = None
    _oh = None

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
        folderPathTestScenario = os.path.join(os.path.dirname(__file__), f"OH{self.SenarioID}")
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
        
        # Create folder to save algorithm output data
        folderPathOutput = os.path.join(os.path.dirname(__file__), f"testing_results/OH{self.SenarioID}/output")
        os.makedirs(folderPathOutput, exist_ok=True)

        # Create model parameters
        schedulingParameters = SP(int(self._inputParameters.maxCaptures), int(self._inputParameters.captureDuration), int(self._inputParameters.transitionTime), int(self._inputParameters.hypsoNr))

        # Run algorithm
        for runNr in range(self.algorithmRuns):
            # Create observation schedule
            observationSchedule, bufferSchedule, downlinkSchedule, _, _, _, _ = runNSGA(
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
            cmdLines = createCmdLinesForCaptureAndBuffering(observationSchedule, bufferSchedule, self._inputParameters, self._oh)
            createCmdFile(f"{folderPathOutput}/{runNr}_cmdLines.txt", cmdLines)



