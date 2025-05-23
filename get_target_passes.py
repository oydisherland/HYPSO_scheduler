import datetime 
import pandas as pd

from extract_cloud_data import getCloudData
from satellite_positioning_calculations import findSatelliteTargetPasses
from scheduling_model import OH, GT, TW, TTW

   

def getAllTargetPasses(captureTimeSeconds: int, startTimeOH: datetime.datetime, endTimeOH: datetime.datetime, targetsFilePath: str, hypsoNr: int) -> list:# captureTimeSeconds: int, timewindow: int, startTimeDelay: int, targetsFilePath: str, hypsoNr: int) -> list:
    """ Get the timewindows for each time the satellte passes the targets
    Output:
    - List of targetPassesData: [id, lat, long, elevation, priority, [startTimes], [endTimes]]
    """

    # Read data from targets.csv into the array targets
    targets_df = pd.read_csv(targetsFilePath)
    targets = targets_df.values.tolist()
    allTargetPasses = []

    #Loop through the targets and calculate earliest start time and latest start time for capturing
    for index, target in enumerate(targets):

        target = target[0].split(';')
        latitude = target[1]
        longitude = target[2]
        elevation = target[3]

        # Verify that the target is is not already in list of targets
        if target[0] in [t[0] for t in allTargetPasses]:
            print(f"Target id {target[0]} is duplicated in target request list, only first entry is used")
            continue

        # Add the target priority as an element of the target data list
        priotity = len(targets) - index
        target.append(priotity)
   
        # Find the time windows when satellite is passing the targets. Each element in pass is a tuple : [utc_time, type('rise', 'culiminate', 'set')]
        passes = findSatelliteTargetPasses(float(latitude), float(longitude), float(elevation), startTimeOH, endTimeOH, hypsoNr)
        
        # Skip iteration if no passes are found
        if not passes:
            continue

        #For each target pass, find start time and end time of the time window
        startTimes = []
        endTimes = []
        twMaxSeconds = 500
        for i in range(len(passes)-2):
            if passes[i][1] == 'rise' and passes[i+1][1] == 'culminate' and passes[i+2][1] == 'set':
                # The pass i -> i+2 corresponds to a time window
                
                time_diff = (passes[i+2][0] - passes[i][0]).total_seconds()
                if time_diff < captureTimeSeconds or time_diff > twMaxSeconds: 
                    # Time window too short or too long
                    continue
                
                # Add tw to start and end times
                startTimes.append(passes[i][0])
                endTimes.append(passes[i+2][0])

    
        # Check that number of start times is equal number of end times
        if len(startTimes) != len(endTimes):
            print(f"len passes: {len(passes)}, firstpass: {passes[0][1]}, lastpass: {passes[-1][1]}, len startTimes: {len(startTimes)}, len endTimes: {len(endTimes)}")
            for p in passes:
                print(p)
            raise ValueError("The length of start times and end times are not equal")
        
        # Skip if no tw correspond to target, go next target
        if len(startTimes) == 0:
            continue

        #Add the list of start times and end times to the target info list
        target.append(startTimes)
        target.append(endTimes)
        allTargetPasses.append(target)

    return allTargetPasses


def removeCloudObscuredTargets(allTargetPasses: list, startTimeOH: int, endTimeOH: int)-> list:
    """ Remove targets that are obscured by clouds """

    targetPassesWithoutClouds = []

    for target in allTargetPasses:
        
        latitude = float(target[1])
        longitude = float(target[2])
        startTimes = target[-2]
        endTimes = target[-1]
        maxCloudCoverage = target[4]

        # Get the cloud data for the target in the given OH
        cloudData = getCloudData(latitude,longitude, startTimeOH, endTimeOH)
        assert cloudData != None

        # Remove observation windows when the cloud coverage is too high
        for key in cloudData: #key is a datetime object
            if cloudData[key] > float(maxCloudCoverage):
                for st in startTimes:
                    # Check the weather forcast corresponding to the closest whole hour of st
                    if abs(key - st).total_seconds() <= 60*30:  #60s times 30min
                        index = startTimes.index(st)
                        startTimes.pop(index)
                        endTimes.pop(index)
                        break
        
        # If target has observation windows left, add it to the list of targets without clouds
        if(len(startTimes) > 0):
            targetPassesWithoutClouds.append(target)      
    
    return targetPassesWithoutClouds


def getModelInput( captureTime: int, ohDurationInDays: int, ohDelayInHours: int, hypsoNr: int, defineStartTime= 'now'):
    """ Put the targetpasses-data into objects defined in scheduling_model.py
    Output:
    - oh: OH object
    - ttwList: list of TTW objects
    """

    #Define the OH - Optimalization Horizon
    if defineStartTime == 'now':
        startTimeOH = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=ohDelayInHours)
    else:
        startTimeOH = datetime.datetime.strptime(defineStartTime, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=datetime.timezone.utc)
    endTimeOH = startTimeOH + datetime.timedelta(days=ohDurationInDays)
    print("Start time OH:", startTimeOH, "End time OH:", endTimeOH)
    # Path to the file containing the ground targets data
    targetsFilePath = 'HYPSO_scheduler/HYPSO_data/targets.csv'

    # Get the target passes
    allTargetPasses = getAllTargetPasses(captureTime, startTimeOH, endTimeOH, targetsFilePath, hypsoNr)
    

    # Remove targets that are obscured by clouds
    #cloudlessTargetpasses = removeCloudObscuredTargets(allTargetPasses, startTimeOH, endTimeOH)
    cloudlessTargetpasses = allTargetPasses

    # Create Optimalization Horizon object
    oh = OH(
        utcStart = startTimeOH,
        utcEnd = endTimeOH,
        durationInDays=ohDurationInDays,
        delayInHours=ohDelayInHours,
        hypsoNr = hypsoNr
    )
    
    # Create objects from the ground targets data
    ttwList = []
    for groundTarget in cloudlessTargetpasses:
        twList = []
        # Create Ground Target object
        gt = GT(
            id = groundTarget[0],
            lat = groundTarget[1],
            long = groundTarget[2],
            priority = groundTarget[-3],
            idealIllumination = 1
        )
        # Create List of Time Window objects
        if len(groundTarget[-2]) != len(groundTarget[-1]):
            print("ERROR: The length of start times and end times are not equal")

        for i in range(len(groundTarget[-2])):
            tw = TW(
                start = (groundTarget[-2][i] - oh.utcStart).total_seconds(),
                end = (groundTarget[-1][i] - oh.utcStart).total_seconds() 
            )
            twList.append(tw)
        # Create Target Time Window object
        ttw = TTW(
            GT = gt,
            TWs = twList
        )
        ttwList.append(ttw)
    
    return oh, ttwList


def printModelInput():
    """ Print the input data for the model """

    oh, ttws = getModelInput(50, 2, 2, 1)
    print("Observation Horizon:", oh.utcStart, oh.utcEnd, "\nDuration and delay:", oh.durationInDays, oh.delayInHours)
    for ttw in ttws:
        print(ttw.GT.id)
        for tw in ttw.TWs:
            print(tw.start, tw.end)
