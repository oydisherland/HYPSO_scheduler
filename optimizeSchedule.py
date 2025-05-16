from scheduling_model import SP, OH, OT
# from runAlgFormatResults import evaluateBestSchedual, evaluateBSTTW, evaluateAlgorithmData
from objective_functions import objectiveFunctionImageQuality
from datetime import datetime
from operators import greedyPrioritySort
import matplotlib.pyplot as plt

import csv

            
            
def isTwFree(time, otList, buffertime):
    """
    Check schedule is free to capture at time
    """
    for ot in otList:
        if time > ot.start and time > ot.end + buffertime:
            return False
        if time < ot.start and time + buffertime < ot.start:
            return False
    return True


def extractTestDataCSV(testNumber, testName):
    """
    Extracts data from the file results/test{testNumber}/testData/TD_{testName}.csv.

    Args:
        testNumber (int): The test number.
        testName (str): The test name.

    Returns:
        list: A list of rows, where each row is a list of values from the CSV file.
    """
    # Construct the file path
    filepath = f"results/test{testNumber}/testData/TD_{testName}.csv"

    # Read and parse the CSV file
    try:
        with open(filepath, mode='r') as file:
            reader = csv.reader(file)
            data = [row for row in reader] 
            # Convert 'Observation Horizon (start/end)' to datetime objects
        observation_horizon = data[0][1:3]  # Extract the start and end times
        start_time = datetime.fromisoformat(observation_horizon[0])
        end_time = datetime.fromisoformat(observation_horizon[1])

        oh = OH(
            utcStart=start_time,
            utcEnd=end_time,
            durationInDays= 2,
            delayInHours=2,
            hypsoNr=1,
        )
        return oh
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return None
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return None
    

def checkFeasibility(schedule, captureDuration, transTime):
    isTrue = True
    counter = 0

    for ot1 in schedule:
        s1 = ot1.start
        e1 = ot1.end
        
        # Capture duration
        if e1 - s1 < captureDuration:
            print(f"Schedule is not feasible cause duration, OT: {ot.GT.id}, start: {s1}, end: {e1}, diff: {e1 - s1}")
            isTrue = False
            counter += 1
        
        # Buffer time
        for ot2 in schedule:
            if ot1.GT.id == ot2.GT.id:
                continue
            s2 = ot2.start
            e2 = ot2.end

            if abs(s1 - s2) < transTime + captureDuration or abs(e1 - e2) < transTime + captureDuration:
                # print(f"buffer 3, diff: {abs(s1 - s2)}, target1: {ot1.GT.id} target 2: {ot2.GT.id}")
                isTrue = False
                counter += 1
    return isTrue, counter//2
            

def improveIQ(otList, ttwList, oh, sp: SP):
    
    bufferTime = sp.transitionTime + sp.captureDuration
    maxIQSchedule = []
    OptimizedSchedule = []

    hasChanged = False

    for ot in otList:

        maxIQStart = ot.start
        maxIQEnd = ot.end
        maxIQValue = 0

        newStartTime = ot.start
        newEndTime = ot.end

        idMatch = False
        for ttw in ttwList:
            
            if ot.GT.id == ttw.GT.id:
                idMatch = True

                for tw in ttw.TWs:
                    # Chck is the ot is scheduled in the current tw
                    if ot.start < tw.start or ot.end > tw.end:
                        continue

                    # Check the peak IQ value of this TW
                    idealStart = tw.start + (tw.end - tw.start) / 2 - sp.captureDuration / 2
                    idealEnd = tw.start + (tw.end - tw.start) / 2 + sp.captureDuration / 2
                    checkOt = OT(ot.GT, idealStart, idealEnd)
                    iqValue = objectiveFunctionImageQuality([checkOt], oh)
                    if iqValue > maxIQValue:
                        # Update the st and et of ideal IQ
                        maxIQValue = iqValue
                        maxIQStart = idealStart
                        maxIQEnd = idealEnd

                    # Check if the time window is free to capture
                    idealCaptureTime = tw.start + (tw.end - tw.start) / 2 - sp.captureDuration / 2
                    if isTwFree(idealCaptureTime ,otList, bufferTime) and isTwFree(idealCaptureTime,OptimizedSchedule, bufferTime):
                        hasChanged = True
                        newStartTime = idealCaptureTime
                        newEndTime = idealCaptureTime + sp.captureDuration
                        break 
            if idMatch:
                break
        OptimizedSchedule.append(OT(ot.GT, newStartTime, newEndTime))
        maxIQSchedule.append(OT(ot.GT, maxIQStart, maxIQEnd))


    return OptimizedSchedule, maxIQSchedule, hasChanged


def findOptimalIQSolution(testNumber, runNr):
    
    captureDuration = 60
    transTime = 90
    testName = f"test{testNumber}-run{runNr}"
    filename_schedule = f"results/test{testNumber}/schedual/BS_{testName}.json"
    filename_ttw = f"results/test{testNumber}/schedual/TTWL_{testName}.json"

    schedule = evaluateBestSchedual(filename_schedule)
    ttwList = evaluateBSTTW(filename_ttw)

    oh = extractTestDataCSV(testNumber, testName)
    optSched, maxSched, hasChanged = improveIQ(schedule, ttwList, oh, SP(40, captureDuration, transTime))
    if optSched != maxSched:
        print("Optimized schedule is not the same as max schedule")
    else:
        print("Optimized schedule is the same as max schedule")
    # Extract the test data
    print(f"has changed {hasChanged}")
    objectiveIQ_original = objectiveFunctionImageQuality(schedule, oh)

    
        
    return objectiveIQ_original, schedule, optSched, maxSched, oh, ttwList

def findMaxPriority(ttwList, sp: SP):
    ttwListSorted = greedyPrioritySort(ttwList.copy())
    maxPriority = 0
    counter = 0
    for ttw in ttwListSorted:
        if counter == sp.maxCaptures:
            break
        maxPriority += ttw.GT.priority
        counter += 1
    return maxPriority


# testNumber = 222
# runNr = 0
# cd = 60
# tt = 90
# objectiveIQ_original, originalSchedule, OptimizedSchedule, maxIQSchedule, oh, ttwList = findOptimalIQSolution(testNumber, runNr)

# objectiveIQ_improved = objectiveFunctionImageQuality(OptimizedSchedule, oh)
# IQMax = objectiveFunctionImageQuality(maxIQSchedule, oh)
# PMax = findMaxPriority(ttwList, SP(40, cd, tt))
# # print(f"Objective function image quality original: {objectiveIQ_original}")
# # print(f"Objective function image quality improved: {objectiveIQ_improved}")
# # print(f"Objective function image quality max: {objectiveValeMax}")
# # print(f"Schedule is feasible original: {checkFeasibility(originalSchedule, cd, tt)}")
# # print(f"Schedule is feasible optimized: {checkFeasibility(OptimizedSchedule, cd, tt)}")
# # print(f"Schedule is feasible image quality max: {checkFeasibility(maxIQSchedule, cd, tt)}")

# fileName_algdata = f"results/test{testNumber}/algorithmData/AD_test{testNumber}-run{runNr}.json"
# algData = evaluateAlgorithmData(fileName_algdata)
# fronts, objectiveSpace, selectedObjectiveVals, kneePoints = algData[-1]
# plotParetoFrontWithMaxOV(objectiveSpace, [PMax, IQMax])





