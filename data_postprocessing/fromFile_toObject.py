import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import csv
import numpy as np 
from datetime import timedelta, datetime

from scheduling_model import TW, GT, OT, OH, TTW


""" 
- Create a function that takes in the test number as input, 
and reads and formats back the BS and OH corresponding to that test, 
the output of the function will be a list/ dictionary of BS and the OH object.
DONE: evaluateBestSchedual

- Create a function that takes in the BS and the corresponding OH as input, 
claculates the datetime objecte corresponding to each capture, 
returns a list (or similar) that can be used in further processing.
"""

# Functions that read data from json files and recreate the original data structure

def getSchedualFromFile(filepath: str):
    """ Extract the list of scheduled targets from the JSON file, and recreate the GT and OT objects """

    try: 
        # Load the schedual data from the JSON file
        with open(filepath, mode='r') as file:
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

    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return schedual
def getOHFromFile(filepath: str):
    """ Extract the utc start and end times, oh duration, oh delay and hypso number from file, and recreate the OH object"""

    oh = None
    try:
        utcStart, utcEnd, ohDurationInDays, ohDelayInHours, hypsoNr = None, None, None, None, None
        # Open and read the CSV file
        with open(filepath, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0].strip() == "Sat model input data (ohDurationDays, ohDelayHours, HypsoNr):":
                    ohDurationInDays, ohDelayInHours, hypsoNr = row[1], row[2], row[3]
                if row[0].strip() == "Observation Horizon (start/end):":
                    utcStart, utcEnd = datetime.fromisoformat(row[1]), datetime.fromisoformat(row[2])
        oh = OH(
            utcStart=utcStart,
            utcEnd=utcEnd,
            durationInDays=ohDurationInDays,
            delayInHours=ohDelayInHours,
            hypsoNr=hypsoNr
        )
    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return oh
def getAlgorithmData(filepath: str):
    """ Extract the algorithm data from the file and recreate printArray list returned by the algorithm """
   
    try:
        # Load the algorithm data from the JSON file
        with open(filepath, mode='r') as file:
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

    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return algData
def getFinalPopulation(filepath: str):
    """ Extract from file the schedule corresponding to the final population and recreate the finalPop array,
    that was returned by the algorithm """
    
    # Load the schedual data from the JSON file
    try:
        with open(filepath, mode='r') as file:
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

    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return schedualsFinalPop
def getBSTTW(filepath: str):
    """ Extract JSON object from file and recreate ttwList object of best schedule """

    try:
        # Load the ttwList data from the JSON file
        with open(filepath, mode='r') as file:
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

    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return ttwList
    


# Functions to transform the object 

def convertSchedualToDateTime(schedualWithRelativeTime: list, oh: OH) -> list:
    """ Convert the time representation in the schedule to the absolute datetime representation, 
    instead of relative to the start of optimization horizon"""

    schedualWithDatetimeObj = []
    for ot in schedualWithRelativeTime:
        # Convert the start and end times of each OT to datetime objects
        captureStart = oh.utcStart + timedelta(seconds=ot.start)
        captureEnd = oh.utcStart + timedelta(seconds=ot.end)

        otWithDatetime = OT(
            GT=ot.GT,
            start=captureStart,
            end=captureEnd
        )
        schedualWithDatetimeObj.append(otWithDatetime)
    return schedualWithDatetimeObj


