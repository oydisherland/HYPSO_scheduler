import os



from campaignPlanner_interaction.intergrate_campaign_planner import getScheduleFromCmdLine, getTargetIdPriorityDict, recreateOTListFromCmdFile

def getListOfTargetIdsFromScript(pathScript: str) -> list:
    """ Get a list of target IDs from a command line script """
    
    cmdLines = []

    with open(pathScript, 'r') as f:
            for line in f:
                cmdLines.append(line.rstrip())

    targetIds = []
    for cmdLine in cmdLines:
        observationTask, taskType = getScheduleFromCmdLine(cmdLine)
        if taskType == "Buffer" or taskType == "Unknown":
            continue

        targetId = observationTask.GT.id
        targetIds.append(targetId)

    return targetIds

def getSumPriorityOfScript(pathCaptureScript: str) -> int:
    """ Get the sum of priorities of all targets in a command line script """
    
    targetsFilePath = 'HYPSO_scheduler/data_input/HYPSO_data/targets.csv'
    targetIdPriorityDict = getTargetIdPriorityDict(targetsFilePath)

    targetIds = getListOfTargetIdsFromScript(pathCaptureScript)
    sumPriority = 0
    for targetId in targetIds:
        try:
            sumPriority += targetIdPriorityDict[targetId]
        except KeyError:
            print(f"Warning: Target ID {targetId} not found in targets.csv")
            continue

    return sumPriority


def compareScripts(pathScript1: str, pathScript2: str) -> tuple:
    """ Compare two command line scripts in terms of priority sum and unique targets """
    
    # Get the sum of priorities
    sumPriority1 = getSumPriorityOfScript(pathScript1)
    sumPriority2 = getSumPriorityOfScript(pathScript2)

    # Get the which captures are unique for each script 
    targetList1 = getListOfTargetIdsFromScript(pathScript1)
    targetList2 = getListOfTargetIdsFromScript(pathScript2)

    uniqueToScript1 = []
    uniqueToScript2 = []
    for targetId1 in targetList1:
        if targetId1 not in targetList2:
            uniqueToScript1.append(targetId1)
    
    for targetId2 in targetList2:
        if targetId2 not in targetList1:
            uniqueToScript2.append(targetId2)
    

    return (sumPriority1, sumPriority2), (uniqueToScript1, uniqueToScript2)

def captureScriptVsCampaignScript(pathCaptureScript, pathCampaignScript):



    cmdLines_capture = []
    cmdLines_campaign = []

    with open(pathCaptureScript, 'r') as f:
            for line in f:
                cmdLines_capture.append(line.rstrip())

    with open(pathCampaignScript, 'r') as f:
            for line in f:
                cmdLines_campaign.append(line.rstrip())
    print("Number of scheduled targets: ", len(cmdLines_campaign)//2)
    
    campaignAddedCmdLines = []
    campaignRemovedCmdLines = cmdLines_capture.copy()

    for i in range(len(cmdLines_campaign)):
        # For each campaign command line
        observationTask_camp, taskType_camp = getScheduleFromCmdLine(cmdLines_campaign[i])
        if taskType_camp == "Buffer" or taskType_camp == "Unknown":
            continue

        targetId_camp = observationTask_camp.GT.id
        cmdLineNotInCaptureScript = True


        for cmdLine_cap in cmdLines_capture:
            # For each capture command line
            observationTask_cap, taskType_cap = getScheduleFromCmdLine(cmdLine_cap)
            targetId_cap = observationTask_cap.GT.id

            # Compare command lines
            if targetId_camp == targetId_cap:
                # Lines represeting same command, look for changes 
                cmdLineNotInCaptureScript = False
                campaignRemovedCmdLines.remove(cmdLine_cap)
                
                if observationTask_camp.GT.exposureTime != observationTask_cap.GT.exposureTime:
                        print(f"Difference in exposure time found: {observationTask_camp.GT.exposureTime} vs {observationTask_cap.GT.exposureTime}")
                if observationTask_camp.start != observationTask_cap.start:
                    print(f"Different start times: {observationTask_camp.start} \n{observationTask_cap.start}\n")

        if cmdLineNotInCaptureScript:
            campaignAddedCmdLines.append(cmdLines_campaign[i])
    return campaignAddedCmdLines, campaignRemovedCmdLines


def testRecreateCPScript():
    """ Test the function recreateOTListFromCmdFile """
    pathScript = "HYPSO_scheduler/output_folder/CP_output/cp_test.txt"
    cmdLines = []

    with open(pathScript, 'r') as f:
            for line in f:
                cmdLines.append(line.rstrip())
    
    otList = recreateOTListFromCmdFile(cmdLines)
    for ot in otList:
        print(f"Target ID: {ot.GT.id}, Start: {ot.start}, End: {ot.end}, Priority: {ot.GT.priority}, Exposure time: {ot.GT.exposureTime}")
    print(f"Total number of observation tasks: {len(otList)}")

