import csv
import datetime
import os

from data_input.extract_cloud_data import getCloudData
from data_input.satellite_positioning_calculations import findSatelliteTargetPasses, findIllumminationPeriods
from scheduling_model import OH, GT, TW, TTW, GSTW, GS
from data_preprocessing.parseTargetsFile import getTargetDataFromJsonFile
   

def getAllTargetPasses(captureTimeSeconds: int, startTimeOH: datetime.datetime, endTimeOH: datetime.datetime, targetsFilePath: str, hypsoNr: int) -> list:# captureTimeSeconds: int, timewindow: int, startTimeDelay: int, targetsFilePath: str, hypsoNr: int) -> list:
    """ Get the TTW for each time the satellite passes the every requested target
    Output:
    - allTargetPasses: list of TTWs for each target in the target request file
    """

    # Read data from targets.json into the array targets
    allTargetPasses = []
    targetData = getTargetDataFromJsonFile(targetsFilePath)

    #Loop through the targets and calculate earliest start time and latest start time for capturing
    for index, target in enumerate(targetData):

        targetId = target.name.rstrip()
        latitude = target.lat
        longitude = target.lon
        elevation = target.elev

        # Verify that the target is is not already in list of targets
        if targetId in [t['groundTarget'].id for t in allTargetPasses]:
            print(f"Target id {targetId} is duplicated in target request list, only first entry is used")
            continue

        # Add the target priority as an element of the target data list
        priority = len(targetData) - index
        #target.append(priority)

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


        # If all start times are removed by time constraints, go to next target
        if len(startTimes) == 0:
            continue

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
            id = targetId,
            lat = latitude,
            long = longitude,
            priority = priority,
            cloudCoverage = target.cc,
            exposureTime = target.exp,
            captureMode = target.mode
        )

        # Create a target Pass object 
        targetPass = {}
        targetPass['groundTarget'] = groundTargetObject
        targetPass['startTimes'] = startTimes
        targetPass['endTimes'] = endTimes

        allTargetPasses.append(targetPass)

    return allTargetPasses

def removeNonIlluminatedPasses(allTargetPasses: list, startTimeOH: datetime.datetime, endTimeOH: datetime.datetime)-> list:
    """ Remove time windows where the target is not illuminated by the sun
    Output:
    - targetPassesWithIllumination: list of TTWs that have sufficient illumination
    """
    targetPassesWithIllumination = []    
    
    for targetPass in allTargetPasses:
        gt = targetPass['groundTarget']
        latitude = float(gt.lat)
        longitude = float(gt.long)
        startTimes = targetPass['startTimes'].copy()

        illuminatedPeriods = findIllumminationPeriods(float(latitude), float(longitude), startTimeOH, endTimeOH)

        for st in startTimes:
            # Loop through all TWs of the target
            illuminated = False
            
            # Check that the TW is within an illuminated period
            for sunRise, sunSet in illuminatedPeriods:
                if sunRise <= st <= sunSet:
                    # This TW is illuminated, go next TW
                    illuminated = True
                    break

            if not illuminated:
                # TW is not illuminated, remove it
                index = targetPass['startTimes'].index(st)
                targetPass['startTimes'].pop(index)
                targetPass['endTimes'].pop(index)

        if len(targetPass['startTimes']) > 0:        
            targetPassesWithIllumination.append(targetPass)

    return targetPassesWithIllumination
  
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

def removeCloudObscuredPasses(allTargetPasses: list, startTimeOH: datetime.datetime, endTimeOH: datetime.datetime)-> list:
    """ Remove time windows where the target is obscured by clouds, based on weather forecast data
    Output:
    - targetPassesWithoutClouds: list of TTWs that are not obscured by clouds
    """

    targetPassesWithoutClouds = []

    for targetPass in allTargetPasses:

        gt = targetPass['groundTarget']

        latitude = float(gt.lat)
        longitude = float(gt.long)
        startTimes = targetPass['startTimes'].copy()
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
                        index = targetPass['startTimes'].index(st)
                        targetPass['startTimes'].pop(index)
                        targetPass['endTimes'].pop(index)
                        break

        # If target has observation windows left, add it to the list of targets without clouds
        if len(targetPass['startTimes']) > 0:
            targetPassesWithoutClouds.append(targetPass)

    return targetPassesWithoutClouds

def createOHObject(startTimeOH: datetime.datetime, ohDurationInDays: int) -> OH:
    """ Create optimalization horizon object form input parameters, and print the time interval. 
    Output:
     - oh: OH object
    """

    endTimeOH = startTimeOH + datetime.timedelta(days=ohDurationInDays)
    print("Start time OH:", startTimeOH.strftime('%Y-%m-%dT%H:%M:%SZ'), "End time OH:", endTimeOH.strftime('%Y-%m-%dT%H:%M:%SZ'))

    oh = OH(
        utcStart=startTimeOH,
        utcEnd=endTimeOH
    )

    return oh

def getDataObjects(captureDuration: int, oh: OH, hypsoNr: int, minGSWindowLength: float):
    """ Calculate the satellite passes and store in data objects defined in scheduling_model.py
    Output:
    - ttwList: list of TTW objects
    - gstwList: list of GSTW objects
    """

    # Path to the file containing the ground targets data
    targetsFilePath = os.path.join(os.path.dirname(__file__),"../data_input/HYPSO_data/targets.json")

    # Get the target passes
    allTargetPasses = getAllTargetPasses(captureDuration, oh.utcStart, oh.utcEnd, targetsFilePath, hypsoNr)
    print(f"Without filtering, targets: {len(allTargetPasses)}, captures: {howManyPasses(allTargetPasses)}")
    
    # Filter out night passes that are not illuminated by the sun
    illuminatedPasses = removeNonIlluminatedPasses(allTargetPasses, oh.utcStart, oh.utcEnd)
    print(f"After filtering out non-illuminated passes, targets: {len(illuminatedPasses)}, captures: {howManyPasses(illuminatedPasses)}")
    
    # Fileter out targets that are obscured by clouds
    cloudlessTargetpasses = removeCloudObscuredPasses(illuminatedPasses, oh.utcStart, oh.utcEnd)
    print(f"After filtering out cloud-obscured passes, targets: {len(cloudlessTargetpasses)}, captures: {howManyPasses(cloudlessTargetpasses)}")

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

    # Get the passes over the ground stations
    groundStationFilePath = os.path.join(os.path.dirname(__file__),"../data_input/HYPSO_data/ground_stations.csv")
    gstwList = getGroundStationTimeWindows(oh.utcStart, oh.utcEnd, minGSWindowLength, groundStationFilePath, hypsoNr)

    return ttwList, gstwList

def howManyPasses(targetPassList: list) -> int:
    """ Return the total number of target passes in the OH """
    count = 0
    for targetDict in targetPassList:
        count += len(targetDict['startTimes'])
    return count, len(targetPassList)

