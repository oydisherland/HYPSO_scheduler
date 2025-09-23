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

# Functions that take in an object and save it in a json file

def saveScheduleInJsonFile(filepath: str, schedule: list):
    """ Save the schedule data to a JSON file """
    serializable_schedule = [
        {"Ground Target": row[0], "Start Time": row[1], "End Time": row[2]} for row in schedule
    ]

    with open(filepath, mode='w') as file:
        json.dump(serializable_schedule, file, indent=4)
def saveTTWListInJsonFile(filepath: str, ttwList: list):
    """ Save the TTW list data to a JSON file """
    serializable_ttwList = []
    for ttw in ttwList:
        ttwData = {
            "Ground Target": [ttw.GT.id, ttw.GT.priority],
            "Time Windows": [{"start": tw.start, "end": tw.end} for tw in ttw.TWs]
        }
        serializable_ttwList.append(ttwData)

    with open(filepath, mode='w') as file:
        json.dump(serializable_ttwList, file, indent=4)
def saveIterationDataInJsonFile(filepath: str, iterationData: list):
    """ Save the algorithm data to a JSON file """
    serializable_iterationData = []
    for i in range(len(iterationData)):
        fronts, objectiveSpace, selectedObjectiveVals = iterationData[i]
        serializable_iterationData.append({
            "fronts": [front.tolist() for front in fronts],  # Convert NumPy arrays to lists
            "objectiveSpace": [obj.tolist() for obj in objectiveSpace],  # Convert NumPy arrays to lists
            "selectedObjectiveVals": [val.tolist() for val in selectedObjectiveVals],  # Convert NumPy arrays to lists
        })

    with open(filepath, mode='w') as file:
        json.dump(serializable_iterationData, file, indent=4)


# Functions that read data from json files and recreate the original data structure

def getScheduleFromFile(filepath: str):
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
def getIterationData(filepath: str):
    """ Extract the algorithm data from the file and recreate iterationData list returned by the algorithm """
   
    try:
        # Load the algorithm data from the JSON file
        with open(filepath, mode='r') as file:
            serialized_data = json.load(file)

        # Reconstruct iterationData from the serialized data
        iterationData = []
        for entry in serialized_data:
            fronts = [np.array(front) for front in entry["fronts"]]  # Convert lists back to NumPy arrays
            objectiveSpace = [np.array(obj) for obj in entry["objectiveSpace"]]  # Convert lists back to NumPy arrays
            selectedObjectiveVals = [np.array(val) for val in entry["selectedObjectiveVals"]]  # Convert lists back to NumPy arrays
            iterationData.append((fronts, objectiveSpace, selectedObjectiveVals))

        # Reconstruct Kneepoints from the serialized data
        # kneePoints = [np.array(entry["kneePoint"]) for entry in serialized_data]

    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return iterationData
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
    



