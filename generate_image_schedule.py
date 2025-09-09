import csv
import os

import data_postprocessing.algorithmData_api as AD_api
from scheduling_model import SP
from algorithm.NSGA2 import runNSGA
from data_preprocessing.get_target_passes import getModelInput

def csvToDict(filepath):
    """
    Reads a CSV file and returns a dictionary where each row's first column is the key and the second column is the value.
    Ignores rows starting with #.
    """
    dict= {}
    with open(filepath, mode='r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
            if len(row) >= 2:
                key = row[0].strip()
                value = row[1].strip()
                dict[key] = value
    return dict


### RUN THE ALGORITHM ####

filePath_inputParameters = os.path.join(os.path.dirname(__file__),"data_input/input_parameters.csv")
inputParameters = csvToDict(filePath_inputParameters)


oh, ttwList = getModelInput(
    int(inputParameters["captureDuration"]),
    int(inputParameters["durationInDaysOH"]),
    int(inputParameters["delayInHoursOH"]),
    int(inputParameters["hypsoNr"]),
    (inputParameters["startTimeOH"]))

schedulingParameters = SP(
    int(inputParameters["maxCaptures"]), 
    int(inputParameters["captureDuration"]), 
    int(inputParameters["transitionTime"]))

schedule, _, _, _, _ = runNSGA(
    int(inputParameters["populationSize"]), 
    int(inputParameters["NSGA2Runds"]), 
    ttwList, 
    schedulingParameters, 
    oh, 
    int(inputParameters["ALNSRuns"]), 
    bool(inputParameters["isTabooBankFIFO"]), 
    bool(inputParameters["iqNonLinear"]), 
    int(inputParameters["desNumber"]), 
    int(inputParameters["maxTabBank"])
)

# AD_api.saveScheduleInJsonFile(os.path.join(os.path.dirname(__file__), f"{inputParameters['testName']}.json"), schedule)
# print(AD_api.getScheduleFromFile(os.path.join(os.path.dirname(__file__), f"{inputParameters['testName']}.json")))
