import random
from enum import Enum

from rhga import RHGA
from get_target_passes import getModelInput
from scheduling_model import OH,SP, OT


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

def destroyOperator(otList: list, ttwList: list, destroyNumber: int, destroyType: DestroyType):
    """
    destroyType:
    - random
    - greedy   
    - energySaving
    - congestion
    """
    removedTargetsIdList = []

    #Ceck if otList is empty
    if not otList:
        return otList, removedTargetsIdList

    if len(ttwList) == 0:
        print("ttwList is empty")

    #Sort list based on destroyType
    if destroyType == DestroyType.RANDOM:
        otListsorted = randomSort(otList)
    elif destroyType == DestroyType.GREEDY:
        otListsorted = greedySort(otList)
    elif destroyType == DestroyType.ENERGY_SAVING:
        otListsorted = energySavingSort(otList)
    elif destroyType == DestroyType.CONGESTION:
        ttwList = congestionSort(ttwList.copy())
        otListsorted = []
        for ttw in ttwList:         
            for ot in otList:   
                if ot.GT.id == ttw.GT.id:
                    otListsorted.append(ot)
                    break

    else:
        print("Destroy type not found")
        return 0

    #Remove elements at end of list 
    for _ in range(destroyNumber):
        removedTargetsIdList.append(otListsorted.pop(-1).GT.id)
        
    return otListsorted, removedTargetsIdList

def repairOperator(ttwList: list, otList: list, unfeasibleTargetsIdList: list, repairType: RepairType, schedulingParameters: SP, oh: OH):
    """
    repairType:
    - random
    - greedy   
    - smallTW
    - congestion
    """
    ttwListRepaired =  []

    #Sort list based on repairType
    if repairType == RepairType.RANDOM:
        ttwListRepaired = randomSort(ttwList)
    elif repairType == RepairType.GREEDY:
        ttwListRepaired = greedySort(ttwList)
    elif repairType == RepairType.SMALL_TW:
        ttwListRepaired = smallTWSort(ttwList)
    elif repairType == RepairType.CONGESTION:
        ttwListRepaired = congestionSort(ttwList)
    else:
        print("Repair type not found")
        return 0
    
    #Find an observation task schedule
    otList, objectiveValuesList = RHGA(ttwListRepaired, otList, unfeasibleTargetsIdList, schedulingParameters, oh)

    return ttwListRepaired, otList, objectiveValuesList


# Test the functions
# oh, ttwList = getModelInput(50, 2, 2, 1)
# otList = []
# sp = SP(40,50,60)
# ttwList, otList, objectiveVals = repairOperator(ttwList, otList, [], RepairType.RANDOM, sp, oh)
# print(objectiveVals)
 
# otList, unfesaibleTargs = destroyOperator(otList, ttwList, 7, DestroyType.CONGESTION)
# print(len(otList))

# ttwList, otList, objectiveVals = repairOperator(ttwList, otList, unfesaibleTargs, RepairType.CONGESTION, sp, oh)
# print(objectiveVals)
# print(len(otList))