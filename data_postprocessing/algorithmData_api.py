import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import csv
import numpy as np 
import datetime
import json

import pandas as pd
from datetime import timedelta
from data_postprocessing.quaternions import generate_quaternions
from data_input.satellite_positioning_calculations import createSatelliteObject, findSatelliteTargetElevation
from scheduling_model import OH, OT, GT, BT, OH, DT, TW, TTW



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
            "Ground Target": ttw.GT,
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
                cloudCoverage=groundTarget[4],
                exposureTime=groundTarget[5],
                captureMode=groundTarget[6]
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
def getTTWListFromFile(filepath: str):
    """ Extract JSON object from file and recreate ttwList object of best schedule """
    ttwList = None
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
                lat = groundTarget[1],
                long = groundTarget[2],
                priority = groundTarget[3],
                cloudCoverage = groundTarget[4],
                exposureTime = groundTarget[5],
                captureMode = groundTarget[6]
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
    



#### UTILITY FUNCTIONS ####
# function to calcuate quaternions for a given target at a given time
def calculateQuaternions(hypsoNr: int, groundTarget: GT, timestamp: datetime.datetime):
    """ Calculate the quaternions for a given target at a given time
    Output:
    - quaternions: dictionary with keys 'r', 'l', 'j', 'k'
    """
    quaternions = {}

    satellite_skf = createSatelliteObject(hypsoNr)
    elevation = findSatelliteTargetElevation(float(groundTarget.lat), float(groundTarget.long), timestamp, hypsoNr)
    q = generate_quaternions(satellite_skf, timestamp, float(groundTarget.lat), float(groundTarget.long), elevation)

    quaternions['r'] = q[0]
    quaternions['l'] = q[1]
    quaternions['j'] = q[2]
    quaternions['k'] = q[3]

    return quaternions
# Function that creates a map between id of a target and its corresponding priority
def getTargetIdPriorityDictFromCsv(targetsCsvFilePath: str) -> dict:
    """ Get the priority of a list of target IDs from the targets.csv file 
    Output:
    - priorityIdDict: dictionary with target ID as key and priority as value
    """

    priorityIdDict = {}
    targets_df = pd.read_csv(targetsCsvFilePath)
    targets = targets_df.values.tolist()

    for index, target in enumerate(targets):
        target = target[0].split(';')
        targetId = target[0]
        targetPriority = len(targets) - index

        priorityIdDict[targetId] = targetPriority

    return priorityIdDict
def getTargetIdPriorityDictFromJson(targetsJsonFilePath: str) -> dict:
    """ Get the priority of a list of target IDs from a targets.json file 
    Output:
    - priorityIdDict: dictionary with target ID as key and priority as value
    """
    
    priorityIdDict = {}
    
    with open(targetsJsonFilePath, 'r') as f:
        targets = json.load(f)
    
    for index, target in enumerate(targets):
        targetId = target['name'].strip()  # Remove any whitespace
        targetPriority = len(targets) - index
        
        priorityIdDict[targetId] = targetPriority
    
    return priorityIdDict
# Function to convert relative time to datetime objects
def relativeTimeToDateTime(relativeTime: float, oh: OH) -> datetime.datetime:
    """ Convert relative time (in seconds) to datetime object based on the start of the optimization horizon
    Output:
    - datetime object
    """
    dateTimeObj = oh.utcStart + timedelta(seconds=relativeTime)
    return dateTimeObj
# Functions to reformat the schedule data
def convertToUnixTime(dateTime: datetime.datetime) -> int:
    """Convert a timestamp string to Unix time"""
    return int(dateTime.timestamp())
def convertFromUnixTime(unixTime: int) -> datetime.datetime:
    """Convert Unix time to a timezone-aware datetime object (UTC)"""
    return datetime.datetime.fromtimestamp(unixTime, tz=datetime.timezone.utc)
def convertBTListToDateTime(bufferScheduleWithRelativeTime: list, oh: OH) -> list:
    """ Convert the time representation in the buffer schedule to the absolute datetime representation, 
    instead of relative to the start of optimization horizon"""

    bufferScheduleWithDatetimeObj = []
    for bt in bufferScheduleWithRelativeTime:
        # Convert the start and end times of each BT to datetime objects
        bufferStart = oh.utcStart + timedelta(seconds=bt.start)
        bufferEnd = oh.utcStart + timedelta(seconds=bt.end)

        btWithDatetime = BT(
            GT=bt.GT,
            fileID=bt.fileID,
            start=bufferStart,
            end=bufferEnd
        )
        bufferScheduleWithDatetimeObj.append(btWithDatetime)
    return bufferScheduleWithDatetimeObj
def convertOTListToDateTime(scheduleWithRelativeTime: list, oh: OH) -> list:
    """ Convert the time representation in the schedule to the absolute datetime representation, 
    instead of relative to the start of optimization horizon"""

    scheduleWithDatetimeObj = []
    for ot in scheduleWithRelativeTime:
        # Convert the start and end times of each OT to datetime objects
        captureStart = relativeTimeToDateTime(ot.start, oh)
        captureEnd = relativeTimeToDateTime(ot.end, oh)

        otWithDatetime = OT(
            GT=ot.GT,
            start=captureStart,
            end=captureEnd
        )
        scheduleWithDatetimeObj.append(otWithDatetime)
    return scheduleWithDatetimeObj
def convertDTListToDateTime(downlinkScheduleWithRelativeTime: list, oh: OH) -> list:
    """ Convert the time representation in the downlink schedule to the absolute datetime representation, 
    instead of relative to the start of optimization horizon"""

    downlinkScheduleWithDatetimeObj = []
    for dt in downlinkScheduleWithRelativeTime:
        # Convert the start and end times of each DT to datetime objects
        downlinkStart = relativeTimeToDateTime(dt.start, oh)
        downlinkEnd = relativeTimeToDateTime(dt.end, oh)

        dtWithDatetime = DT(
            GT=dt.GT,
            GS=dt.GS,
            start=downlinkStart,
            end=downlinkEnd
        )
        downlinkScheduleWithDatetimeObj.append(dtWithDatetime)
    return downlinkScheduleWithDatetimeObj
def getMiddleTime(startTime: datetime.datetime, endTime: datetime.datetime) -> datetime.datetime:
    """ Get the middle time of the capture window for a given observation target """
    middleTime = startTime + timedelta(seconds=(endTime - startTime).seconds / 2)
    return middleTime

def CombineCaptureAndBufferSchedules(captureSchedule: list, bufferSchedule: list) -> list:
    """ Combine the capture schedule and buffer schedule into one schedule, in order of start time """
    # Sort the two list after start time
    captureScheduleSorted = sorted(captureSchedule, key=lambda ot: getMiddleTime(ot.start, ot.end))
    bufferScheduleSorted = sorted(bufferSchedule, key=lambda bt: getMiddleTime(bt.start, bt.end))

    # Combine the two schedules into one list
    combinedSchedule = []
    i, j = 0, 0
    while i < len(captureScheduleSorted) and j < len(bufferScheduleSorted):
        if captureScheduleSorted[i].start < bufferScheduleSorted[j].start:
            combinedSchedule.append([captureScheduleSorted[i], "Capture"])
            i += 1
        else:
            combinedSchedule.append([bufferScheduleSorted[j], "Buffer"])
            j += 1
    # Append any remaining tasks from either schedule
    combinedSchedule.extend([[task, "Capture"] for task in captureScheduleSorted[i:]])
    combinedSchedule.extend([[task, "Buffer"] for task in bufferScheduleSorted[j:]])
    return combinedSchedule
