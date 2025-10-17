import random
from enum import Enum

from algorithm.rhga import RHGA
from scheduling_model import OH, SP, GSTW, TTW, BT, DT, OT
from transmission_scheduling.input_parameters import TransmissionParams
from transmission_scheduling.two_stage_transmission_insert import twoStageTransmissionScheduling
from data_preprocessing.objective_functions import objectiveFunctionPriority, objectiveFunctionImageQuality


class DestroyType(Enum):
    RANDOM = 0
    GREEDY_P = 1
    GREEDY_IQ = 2
    CONGESTION = 3

class RepairType(Enum):
    RANDOM = 0
    GREEDY = 1
    SMALL_TW = 2
    CONGESTION = 3


#### Sorting functions for different target prioritizing strategies


def randomSort(ttwListOriginal: list):
    """ Sort TTW list randomly """
    ttwList = ttwListOriginal.copy()
    ttwListSorted = []

    # Randomly select ttw from ttwList, remove from ttwList and add to ttwListSorted
    while ttwList:
        ttwListSorted.append(ttwList.pop(random.randint(0,len(ttwList)-1)))
    return ttwListSorted


def greedyPrioritySort(ttwListOriginal: list):
    """ Sort TTW list so high priority GT are first"""
    ttwList = ttwListOriginal.copy()
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

def greedyImageQualitySort(otListOriginal: list, oh: OH, hypsoNr):
    """ Sort OT list so GT with the highest image quality are first"""
    otList = otListOriginal.copy()
    otListSorted = []

    while otList:
        maxImageQuality = 0
        maxIndex = 0
        for j in range(len(otList)):
            imageQuality = objectiveFunctionImageQuality([otList[j]], oh, hypsoNr)
            if imageQuality > maxImageQuality:
                maxImageQuality = imageQuality
                maxIndex = j
        otListSorted.append(otList.pop(maxIndex))
    return otListSorted


def smallTWSort(ttwListOriginal: list):
    """ Sort TTW list so GT with small TWs are first"""
    ttwList = ttwListOriginal.copy()
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



def congestionSort(ttwListOriginal: list):
    """ Sort TTW list so GT with little congestion are first"""
    ttwList = ttwListOriginal.copy()
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

def destroyOperator(otList: list, ttwList: list, destroyNumber: int, destroyType: DestroyType, oh: OH, hypsoNr: int):
    """ Takes in a list of OT and removes destroyNumber of them. Selects which ones to remove based on destroyType.
    destroyTypes: random, greedy_priority, greedy_imageQuality, congestion. \n
    Output:
    - otList: list of OTs with destroyNumber less elements
    """
    removedTargetsIdList = []

    #Ceck if otList is empty
    if not otList:
        return otList, removedTargetsIdList

    if len(ttwList) == 0:
        print("ttwList is empty")

    #Sort list based on destroyType
    if destroyType == DestroyType.RANDOM:
        otListSorted = randomSort(otList)
    elif destroyType == DestroyType.GREEDY_P:
        otListSorted = greedyPrioritySort(otList)
    elif destroyType == DestroyType.GREEDY_IQ:
        otListSorted = greedyImageQualitySort(otList, oh, hypsoNr)
    elif destroyType == DestroyType.CONGESTION:
        ttwListSorted = congestionSort(ttwList)
        otListSorted = []
        for ttw in ttwListSorted:         
            for ot in otList:   
                if ot.GT.id == ttw.GT.id:
                    otListSorted.append(ot)
                    break

    else:
        print("Destroy type not found")
        return 0

    #Remove elements at end of list 
    for _ in range(destroyNumber):
        removedTargetsIdList.append(otListSorted.pop(-1).GT.id)
        
    return otListSorted, removedTargetsIdList

def repairOperator(ttwList: list, otList: list, gstwList: list[GSTW], unfeasibleTargetsIdList: list,
                   repairType: RepairType, schedulingParameters: SP, transmissionParams: TransmissionParams, oh: OH,
                   fullReinsert = False) -> tuple[list[TTW], list[OT], list[BT], list[DT], list]:
    """ Takes in a list of OTs and inserts new OTs until no more feasible insertions can be performed. Selects which ones to insert based on repairType.
    After inserting all new OTs, the scheduled is adjusted to fulfill downlink/buffering requirements.
    repairType: random, greedy, smallTW, congestion.\n
    Output:
    - otList: list of OTs with new OTs inserted
    """

    otListCopy = otList.copy()

    # This is set to greedy mode for HYPSO-2, because inserting OT in the middle of time windows works well enough for HYPSO-2
    # This is because agile capturing of two overlaying targets is almost not possible for HYPSO-2
    greedyMode = True
    randomMode = False

    #Sort list based on repairType
    if repairType == RepairType.RANDOM:
        ttwListSorted = randomSort(ttwList)
    elif repairType == RepairType.GREEDY:
        ttwListSorted = greedyPrioritySort(ttwList)
    elif repairType == RepairType.SMALL_TW:
        ttwListSorted = smallTWSort(ttwList)
    elif repairType == RepairType.CONGESTION:
        ttwListSorted = congestionSort(ttwList)
    else:
        raise Exception("The repair operator type could not be found")

    #Find an observation task schedule
    otListRepaired = RHGA(ttwListSorted, otListCopy, unfeasibleTargetsIdList, schedulingParameters, oh, greedyMode, randomMode)

    ### Downlink/buffer scheduling
    # Adjust the imaging schedule such that the buffer and downlink tasks fit
    btList, dtList, otListAdjusted = twoStageTransmissionScheduling(otListRepaired, ttwList, gstwList, transmissionParams,
                                                             True, fullReinsert)
    # Calculate the objective values of the adjusted schedule
    objectiveValuesList = [objectiveFunctionPriority(otListAdjusted),
                           objectiveFunctionImageQuality(otListAdjusted, oh, schedulingParameters.hypsoNr)]
    
    return ttwListSorted, otListAdjusted, btList, dtList, objectiveValuesList

