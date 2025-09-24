import csv
import datetime
import pandas as pd

from data_input.extract_cloud_data import getCloudData
from data_input.satellite_positioning_calculations import findSatelliteTargetPasses
from scheduling_model import OH, GT, TW, TTW, GSTW, GS

   

def getAllTargetPasses(captureTimeSeconds: int, startTimeOH: datetime.datetime, endTimeOH: datetime.datetime, targetsFilePath: str, hypsoNr: int) -> list:# captureTimeSeconds: int, timewindow: int, startTimeDelay: int, targetsFilePath: str, hypsoNr: int) -> list:
    """ Get the timewindows for each time the satellte passes the targets
    Output:
    - List of all targetPasses, represend as dicts: [{GT, [startTimes], [EndTimes]}]
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
        if target[0] in [t['groundTarget'].id for t in allTargetPasses]:
            print(f"Target id {target[0]} is duplicated in target request list, only first entry is used")
            continue

        # Add the target priority as an element of the target data list
        priority = len(targets) - index
        target.append(priority)

        # Find the time windows when satellite is passing the targets. Each element in pass is a tuple : [utc_time, type('rise', 'culiminate', 'set')]
        passes = findSatelliteTargetPasses(float(latitude), float(longitude), float(elevation), startTimeOH, endTimeOH, hypsoNr)
        
        # Skip iteration if no passes are found
        if not passes:
            continue

        #For each target pass, find start time and end time of the time window
        startTimes = []
        endTimes = []
        twMaxSeconds = 500
        for i in range(len(passes) - 2):
            if passes[i][1] == 'rise' and passes[i + 1][1] == 'culminate' and passes[i + 2][1] == 'set':
                # The pass i -> i+2 corresponds to a time window

                time_diff = (passes[i + 2][0] - passes[i][0]).total_seconds()
                if time_diff < captureTimeSeconds or time_diff > twMaxSeconds:
                    # Time window too short or too long
                    continue

                # Add tw to start and end times
                startTimes.append(passes[i][0])
                endTimes.append(passes[i + 2][0])

    
        # Check that number of start times is equal number of end times
        if len(startTimes) != len(endTimes):
            print(f"len passes: {len(passes)}, firstpass: {passes[0][1]}, lastpass: {passes[-1][1]}, len startTimes: {len(startTimes)}, len endTimes: {len(endTimes)}")
            for p in passes:
                print(p)
            raise ValueError("The length of start times and end times are not equal")

        # Skip if no tw correspond to target, go next target
        if len(startTimes) == 0:
            continue

        # Create a Ground Target (GT) object
        groundTargetObject = GT(
            id = target[0],
            lat = latitude,
            long = longitude,
            priority = priority,
            cloudCoverage = target[4],
            exposureTime = target[5],
            captureMode = target[6]
        )

        # Create a target Pass object 
        targetPass = {}
        targetPass['groundTarget'] = groundTargetObject
        targetPass['startTimes'] = startTimes
        targetPass['endTimes'] = endTimes

        allTargetPasses.append(targetPass)

    return allTargetPasses


def getGroundStationTimeWindows(startTimeOH: datetime.datetime, endTimeOH: datetime.datetime, minWindowLength: float,
                                groundStationsFilePath: str, hypsoNr: int):
    """
    Get the time windows when the satellite passes over one of the ground stations.

    Args:
        startTimeOH (datetime): Start time of the observation horizon.
        endTimeOH (datetime): End time of the observation horizon.
        minWindowLength (float): Minimum length of a time window in seconds.
        groundStationsFilePath (str): Path to the ground stations file.
        hypsoNr (int): HYPSO satellite number.

    Returns:
        list[GSTW]: List of ground stations and their time windows.
    """

    # Read data from the provided csv
    try:
        with open(groundStationsFilePath, mode='r') as file:
            reader = csv.reader(file)
            # Read the data from the csv
            groundStations = [row for row in reader]
            # Remove the first row (header)
            groundStations.pop(0)

    except FileNotFoundError:
        print(f"File not found: {groundStationsFilePath}")
    except Exception as e:
        print(f"An error occurred: {e}")

    gstwList: list[GSTW] = []

    # Loop through the stations and calculate the earliest start time and latest start time for downlinking
    for index, groundStation in enumerate(groundStations):

        # Create Ground Station object
        groundStation = groundStation[0].split(';')
        gs = GS(
            id=groundStation[0],
            lat=groundStation[1],
            long=groundStation[2],
            minElevation=groundStation[3]
        )

        # Find the time windows when satellite is passing the ground station. Each element in pass is a tuple : [utc_time, type('rise', 'culiminate', 'set')]
        passes = findSatelliteTargetPasses(float(gs.lat), float(gs.long), float(gs.minElevation), startTimeOH, endTimeOH, hypsoNr)

        # Skip iteration if no passes are found
        if not passes:
            continue

        # For each target pass, find start time and end time of the time window
        twList: list[TW] = []
        for i in range(len(passes) - 2):
            if passes[i][1] == 'rise' and passes[i + 1][1] == 'culminate' and passes[i + 2][1] == 'set':
                # The pass i -> i+2 corresponds to a time window
                startTime = (passes[i][0] - startTimeOH).total_seconds()
                endTime = (passes[i + 2][0] - startTimeOH).total_seconds()
                if endTime - startTime >= minWindowLength:
                    twList.append(TW(startTime, endTime))

        gstwList.append(GSTW(gs, twList))

    if len(gstwList) == 0:
        raise ValueError("No ground station passes found")

    return gstwList


def removeCloudObscuredTargets(allTargetPasses: list, startTimeOH: int, endTimeOH: int) -> list:
    """ Remove targets that are obscured by clouds """

    targetPassesWithoutClouds = []

    for targetPass in allTargetPasses:

        gt = targetPass['groundTarget']

        latitude = float(gt.lat)
        longitude = float(gt.long)
        startTimes = targetPass['startTimes']
        endTimes = targetPass['endTimes']
        maxCloudCoverage = gt.cloudCoverage

        # Get the cloud data for the target in the given OH
        cloudData = getCloudData(latitude, longitude, startTimeOH, endTimeOH)
        assert cloudData != None

        # Remove observation windows when the cloud coverage is too high
        for key in cloudData:  #key is a datetime object
            if cloudData[key] > float(maxCloudCoverage):
                for st in startTimes:
                    # Check the weather forcast corresponding to the closest whole hour of st
                    if abs(key - st).total_seconds() <= 60 * 30:  #60s times 30min
                        index = startTimes.index(st)
                        startTimes.pop(index)
                        endTimes.pop(index)
                        break

        # If target has observation windows left, add it to the list of targets without clouds
        if(len(startTimes) > 0):
            targetPassesWithoutClouds.append(targetPass)

    return targetPassesWithoutClouds


def getModelInput(captureTime: int, ohDurationInDays: int, ohDelayInHours: int, hypsoNr: int, defineStartTime='now'):
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
    targetsFilePath = 'data_input/HYPSO_data/targets.csv'

    # Get the target passes
    allTargetPasses = getAllTargetPasses(captureTime, startTimeOH, endTimeOH, targetsFilePath, hypsoNr)
    

    # Remove targets that are obscured by clouds
    #cloudlessTargetpasses = removeCloudObscuredTargets(allTargetPasses, startTimeOH, endTimeOH)
    cloudlessTargetpasses = allTargetPasses

    # Create Optimalization Horizon object
    oh = OH(
        utcStart=startTimeOH,
        utcEnd=endTimeOH,
        durationInDays=ohDurationInDays,
        delayInHours=ohDelayInHours,
        hypsoNr=hypsoNr
    )

    # Create objects from the ground targets data
    ttwList = []
    for targetPass in cloudlessTargetpasses:
        twList = []

        # Create List of Time Window objects
        if len(targetPass['startTimes']) != len(targetPass['endTimes']):
            print("ERROR: The length of start times and end times are not equal")

        for i in range(len(targetPass['startTimes'])):
            tw = TW(
                start = (targetPass['startTimes'][i] - oh.utcStart).total_seconds(),
                end = (targetPass['endTimes'][i] - oh.utcStart).total_seconds() 
            )
            twList.append(tw)
        # Create Target Time Window object
        ttw = TTW(
            GT = targetPass['groundTarget'],
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
