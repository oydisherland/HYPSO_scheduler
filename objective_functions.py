from scheduling_model import  OT, GT, OH
import datetime 

from satellite_positioning_calculations import findSatelliteTargetElevation


""" Objective function repserenting the sum of the priority of the targets observed """
def objectiveFunctionPriority(otList: list):

    priority = 0
    for ot in otList:
        priority += ot.GT.priority
    return priority


def objectiveFunctionImageQuality(otList:list, oh: OH) -> int:
    """ Objective function representing the angle between satellite and target when capturing 
    Output: 
    - Image quality score (0 = min, 100 = max)
    """
    elevationAverage = 0
    maxElivation = 90
    
    # For each observation task, calculate the image quality score based on the elevation of the satellite
    for ot in otList:
        captureTimeMiddel = (ot.start + ot.end) / 2
        utcTime = oh.utcStart + datetime.timedelta(seconds=captureTimeMiddel)
        
        elevation = findSatelliteTargetElevation(ot.GT.lat, ot.GT.long, utcTime, oh.hypsoNr)
        elevationAverage += elevation/len(otList)

    # Make sure the angle is within the limits of 0 to 90 degrees
    if elevationAverage < 0:
        elevationAverage = 0
    elif elevationAverage > maxElivation:
        elevationAverage = maxElivation
    
    # Normalize the image quality score to be between 0 and 100
    imageQualityScore = (elevationAverage / maxElivation) * 100

    return imageQualityScore
