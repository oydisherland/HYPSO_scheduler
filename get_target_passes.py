import datetime 
import pandas as pd
import skyfield.api as skf

from extract_cloud_data import getCloudData
from scheduling_model import OH, GT, TW, TTW


""" Make sure that the indexing of startTime and endTime list correspond to the same time window """
def removeSingleTimePassElement(startTimes: list, endTimes: list, firstType: int, lastType: int):       
    adjustmentString = [
        "No adjustment needed", # adjustmentNr = 0
        "Last element of startTimes and first element of endTimes are removed", # adjustmentNr = 1
        "First element of endTimes is removed", # adjustmentNr = 2
        "Last element of startTimes is removed" # adjustmentNr = -1
    ]
    ajustmentNr = 0

    if lastType == 0 or lastType == 1:
        startTimes.pop(-1)
        ajustmentNr = -1
    if firstType == 2 or firstType == 1:
        endTimes.pop(0)
        ajustmentNr = ajustmentNr + 2 
    
    return startTimes, endTimes, ajustmentNr, adjustmentString[ajustmentNr]
        
""" Get a list of all ground targets with the corresponding time windows for capturing """
def getAllTargetPasses(captureTimeSeconds: int, timewindow: int, startTimeDelay: int, targetsFilePath: str, tleUrl: str, tleFilePath: str) -> list:

    # The skyfield API function to create an "EarthSatellite" object.
    skfH1 = skf.load.tle_file(tleUrl, filename=tleFilePath, reload=False)[0]

    # Timestamps also require a skyfield type
    ts = skf.load.timescale()
    t0 = ts.now() + datetime.timedelta(hours=startTimeDelay)

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

        # Add the target priority as an element of the target data list
        priotity = len(targets) - index
        target.append(priotity)

        # 'wgs84' refers to the system used to define latitude and longitude coordinates
        target_location = skf.wgs84.latlon(float(longitude) * skf.N, float(latitude) * skf.E, 100.0)

        #Find events where the satellite is within elevation of the target within the timewindow
        timestamps, types = skfH1.find_events(target_location, t0, t0 + timewindow, altitude_degrees=float(elevation))
        
        # Skip iteration if no timestamps are found
        if not timestamps:
            continue

        #For each target pass, find start time and end time
        startTimes = []
        endTimes = []
        for i in range(len(timestamps)):
            if types[i] == 0:
                startTimes.append(timestamps[i].utc_datetime().replace(microsecond=0))
            if types[i] == 2:
                utc_endtime = timestamps[i].utc_datetime().replace(microsecond=0)
                endTimes.append(utc_endtime)

        #Remove startTime or endTime if the corresponding pass is not complete
        startTimes, endTimes, ajustmentNeeded, message = removeSingleTimePassElement(startTimes, endTimes, types[0], types[-1])
        if ajustmentNeeded != 0:
            print(message)

        # Check if the time window is too short (not enough time to capture) or too long (likely not belonging to the same pass)
        #One pass typically takes 50-150 seconds, thus bigger time differences than 500 second can be omitted
        largeTimeDifferenc = []
        for i in range(len(startTimes)):
            
            try: 
                time_diff = (endTimes[i] - startTimes[i]).total_seconds()
                if time_diff < captureTimeSeconds and time_diff > 300:
                    startTimes.pop(i)
                    endTimes.pop(i)

                if time_diff > 500:
                    largeTimeDifferenc.append((startTimes[i], endTimes[i], target[0]))

            except IndexError as e:
                print(f"IndexError: {e}")
                break    

        if len(largeTimeDifferenc) > 0:
            for instance in largeTimeDifferenc:
                print("Time differences that are too long: ", instance)

        #Add the list of start times and end times to the target info list
        target.append(startTimes)
        target.append(endTimes)
        allTargetPasses.append(target)

    return allTargetPasses


""" Remove targets that are obscured by clouds """
def removeCloudObscuredTargets(allTargetPasses: list, ohDurationInDays: int, ohDelayInHours: int, delta_t: datetime.timedelta)-> list:

    targetPassesWithoutClouds = []

    for target in allTargetPasses:
        
        latitude = float(target[1])
        longitude = float(target[2])
        startTimes = target[-2]
        endTimes = target[-1]
        maxCloudCoverage = target[4]

        # Get the cloud data for the target in the given OH
        startOfOH = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=ohDelayInHours)
        endOfOH = startOfOH + datetime.timedelta(days=ohDurationInDays) + datetime.timedelta(hours=ohDelayInHours)
        cloudData = getCloudData(latitude,longitude, startOfOH, endOfOH)
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

""" Put the ground target passes data into objects defined in scheduling_model.py
    Example usage: oh, ttws = getModelInput(50, 2, 2, 30) """
def getModelInput( captureTime: int, ohDurationInDays: int, ohDelayInHours: int, delta_t: int):

    # HYPSO 1 data from TLE file
    hypsoTleUrl = 'https://celestrak.org/NORAD/elements/gp.php?CATNR=51053&FORMAT=TLE'
    tlePath = 'HYPSO_data/HYPSO-1_TLE.txt'
    targetsFilePath = 'HYPSO_data/targets.csv'

    # Get the target passes
    allTargetPasses = getAllTargetPasses(captureTime, ohDurationInDays, ohDelayInHours, targetsFilePath, hypsoTleUrl, tlePath)

    # Remove targets that are obscured by clouds
    cloudlessTargetpasses = removeCloudObscuredTargets(allTargetPasses, ohDurationInDays, ohDelayInHours, datetime.timedelta(seconds=delta_t))

    # Create Optimalization Horizon object
    oh = OH(
        utcStart = datetime.datetime.now(datetime.timezone.utc)+ datetime.timedelta(hours=ohDelayInHours),
        utcEnd = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=ohDurationInDays) + datetime.timedelta(hours=ohDelayInHours),
        durationInDays=ohDurationInDays,
        delayInHours=ohDelayInHours
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

""" Print the input data for the model """
def printModelInput():
    oh, ttws = getModelInput(50, 2, 2, 30)
    print("Observation Horizon:", oh.utcStart, oh.utcEnd, "\nDuration and delay:", oh.durationInDays, oh.delayInHours)
    for ttw in ttws:
        print(ttw.GT.id)
        for tw in ttw.TWs:
            print(tw.start, tw.end)

