import calendar

from scheduling_model import  OH
import datetime 

from data_input.satellite_positioning_calculations import findSatelliteTargetElevation

imageQualityDict = {}

def objectiveFunctionPriority(otList: list) -> int:
    """ Calculates the sum of the priority objective for a list of observation tasks
    Output:
    - priority: sum of priorities
    """
    priority = 0
    for ot in otList:
        priority += ot.GT.priority
    return priority

def getIQFromOT(ot, oh: OH, hypsoNr: int) -> float:
    """ Given an OT, calculate the image quality based on the elevation of the satellite at capture time"""
    
    captureTimeMiddel = ot.start + (ot.end - ot.start) / 2
    utcTime = oh.utcStart + datetime.timedelta(seconds=captureTimeMiddel)



    elevation = findSatelliteTargetElevation(float(ot.GT.lat), float(ot.GT.long), utcTime, hypsoNr)

    if elevation < 0:
        # This should not happen
        print(f"Elevation value: {elevation} for {ot.GT.id} at {utcTime}")
        elevation = 0
    
    return elevation

def objectiveFunctionImageQuality(otList:list, oh: OH, hypsoNr: int) -> float:
    """ Objective function representing the angle between satellite and target when capturing 
    Output: 
    - Image quality score (0 = min, 90 = max)
    """
    elevationAverage = 0
    maxElevation = 90

    # For each observation task, calculate the image quality score based on the elevation of the satellite
    for ot in otList:
        captureTimeMiddel = ot.start + (ot.end - ot.start) / 2
        utcTime = oh.utcStart + datetime.timedelta(seconds=captureTimeMiddel)
        # Round the utcTime down to 10 seconds to estimate the elevation more efficiently
        if utcTime.tzinfo is None:
            unixTime = calendar.timegm(utcTime.utctimetuple()) + utcTime.microsecond / 1e6
        else:
            unixTime = utcTime.timestamp()
        # round down to nearest 10 seconds deterministically
        unixTimeRounded = (int(unixTime) // 10) * 10

        # quantize latitude/longitude to 0.1 degrees, giving about 10 km resolution
        latRounded = int(float(ot.GT.lat) * 10) / 10.0
        longRounded = int(float(ot.GT.long) * 10) / 10.0

        # Image quality key
        iqKey = (latRounded, longRounded, unixTimeRounded, hypsoNr)

        if iqKey not in imageQualityDict:
            imageQualityDict[iqKey] = findSatelliteTargetElevation(
                float(ot.GT.lat),
                float(ot.GT.long),
                utcTime,
                hypsoNr
            )

        elevation = imageQualityDict[iqKey]

        if elevation < 0:
            # This should not happen
            print(f"Elevation value: {elevation} for {ot.GT.id} at {utcTime}")
            elevation = 0
    
        elevationAverage += elevation

    elevationAverage = elevationAverage / len(otList)
    # Make sure the angle is within the limits of 0 to 90 degrees
    if elevationAverage < 0:
        elevationAverage = 0
    elif elevationAverage > maxElevation:
        elevationAverage = maxElevation

    return float(elevationAverage)
