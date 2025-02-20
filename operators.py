import random
from enum import Enum
from rhga import RHGA
from get_target_passes import getModelInput
from scheduling_model import OH, GT, TW, TTW, OT ,SP

class DestroyType(Enum):
    RANDOM = 0
    GREEDY = 1
    ENERGY_SAVING = 2
    CONGESTION = 3

class RepairType(Enum):
    RANDOM = 0
    GREEDY = 1
    SMALL_TW = 2
    CONGESTION = 3


#### Sorting functions for different target prioritizing strategies

""" Sort target list randomly """
def randomSort(ttwList: list):
    ttwListSorted = []

    # Randomly select ttw from ttwList, remove from ttwList and add to ttwListSorted
    while ttwList:
        ttwListSorted.append(ttwList.pop(random.randint(0,len(ttwList)-1)))
    return ttwListSorted

""" Sort target list so hight priority gt are first"""
def greedySort(ttwList: list):
    ttwListSorted = []

    # Find element in ttwList with highest priority, remove from ttwList and add to ttwListSorted
    while ttwList:
        maxPriority = 0
        maxIndex = 0
        for j in range(len(ttwList)):
            if ttwList[j].GT.priority > maxPriority:
                maxPriority = ttwList[j].GT.priority
                maxIndex = j
        ttwListSorted.append(ttwList.pop(maxIndex))
    return ttwListSorted

""" Sort target list so gt with small tw are first"""
def smallTWSort(ttwList: list):
    ttwListSorted = []

    # Find element in ttwList with shortest tw, remove from ttwList and add to ttwListSorted
    while ttwList:
        minTW = ttwList[0].TWs[0].end - ttwList[0].TWs[0].start
        maxIndex = 0
        for j in range(len(ttwList)):
            for k in range(len(ttwList[j].TWs)):
                if ttwList[j].TWs[k].end - ttwList[j].TWs[k].start < minTW:
                    minTW = ttwList[j].TWs[k].end - ttwList[j].TWs[k].start
                    maxIndex = j
        ttwListSorted.append(ttwList.pop(maxIndex))

    return ttwListSorted

def energySavingSort(ttwList: list):
    energySavingList = []

    #Calculate
    return energySavingList

""" Sort target list so gt with little congestion are first"""
def congestionSort(ttwList: list):
    congestionLevelsList = []

    #Calculate the congestion level assosiated with each element in ttwList
    for i in range(len(ttwList)):
        congestionLevel = 0

        # Find the sum of the difference in time between all tw of this gt and all other gt.tw
        for tw_i in ttwList[i].TWs:
            twMiddelTime_i = tw_i.start + (tw_i.end - tw_i.start)/2
            for j in range(len(ttwList)):
                if i == j:
                    continue
                for tw_j in ttwList[j].TWs:
                    twMiddelTime_j = tw_j.start + (tw_j.end - tw_j.start)/2
                    congestionLevel += abs(twMiddelTime_i - twMiddelTime_j)

        congestionLevelsList.append(congestionLevel)

    ttwListSorted = []
    # Find element in ttwList with highest congestion level, remove from ttwList and add to ttwListSorted
    while ttwList:
        minCongestion = congestionLevelsList[0]
        maxIndex = 0
        for j in range(len(congestionLevelsList)):
            if congestionLevelsList[j] < minCongestion:
                minCongestion = congestionLevelsList[j]
                maxIndex = j
        ttwListSorted.append(ttwList.pop(maxIndex))
        congestionLevelsList.pop(maxIndex)
    
    return ttwListSorted


#### Destroy operator

def destroyOperator(ttwList: list, destroyNumber: int, destroyType: int):
    """
    destroyType:
    - 0 = random
    - 1 = greedy   
    - 2 = energySaving
    - 3 = congestion
    """
    ttwListDestroyed =  []

    #Sort list based on destroyType
    if destroyType == 0:
        ttwListDestroyed = randomSort(ttwList)
    elif destroyType == 1:
        ttwListDestroyed = greedySort(ttwList)
    elif destroyType == 2:
        ttwListDestroyed = energySavingSort(ttwList)
    elif destroyType == 3:
        ttwListDestroyed = congestionSort(ttwList)
    else:
        print("Destroy type not found")
        return 0
    
    #Remove elements at end of list 
    for _ in range(destroyNumber):
        ttwListDestroyed.pop(-1)
        
    return ttwListDestroyed

def repairOperator(ttwList: list, repairType: int, schedulingParameters: SP):
    """
    repairType:
    - 0 = random
    - 1 = greedy   
    - 2 = smallTW
    - 3 = congestion
    """
    ttwListRepaired =  []

    #Sort list based on repairType
    if repairType == 0:
        ttwListRepaired = randomSort(ttwList)
    elif repairType == 1:
        ttwListRepaired = greedySort(ttwList)
    elif repairType == 2:
        ttwListRepaired = smallTWSort(ttwList)
    elif repairType == 3:
        ttwListRepaired = congestionSort(ttwList)
    else:
        print("Repair type not found")
        return 0
    
    #Find an observation task schedule
    otList, objectiveValuesList = RHGA(ttwListRepaired, schedulingParameters)

    return ttwListRepaired, otList, objectiveValuesList



schedulingParameters = SP(20, 60, 90)

oh, ttws = getModelInput(50, 2, 2, 30)

otList, objectiveValuesList = RHGA(ttws, schedulingParameters)
for ov in objectiveValuesList:
    print("Objective value original: ", ov)

ttwsGreedy, _ , objectiveValuesList = repairOperator(ttws, 1, schedulingParameters)
for ov in objectiveValuesList:
    print("Objective value greedy: ", ov)

ttwsGreedy, _ , objectiveValuesList = repairOperator(ttwsGreedy, 1, schedulingParameters)
for ov in objectiveValuesList:
    print("Objective value greedy: ", ov)

ttwsRandom = destroyOperator(ttwsGreedy, 8, 0)

ttwsGreedy, _ , objectiveValuesList = repairOperator(ttwsRandom, 1, schedulingParameters)
for ov in objectiveValuesList:
    print("Objective value greedy: ", ov)



