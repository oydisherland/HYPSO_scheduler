from scheduling_model import  OT, GT
from datetime import datetime, timedelta
import skyfield.api as skf 

""" Objective function repserenting the sum of the priority of the targets observed """
def objectiveFunctionPriority(otList: list):

    priority = 0
    for ot in otList:
        priority += ot.GT.priority
    return priority

""" Objective function representing the angle between satellite and target when capturing """
def objectiveFunctionImageQuality(otList:list, oh: OH):
    imageQualityScore = 0

    for ot in otList:
        target = ot.GT
        captureTimeMiddel = (ot.start + ot.end) / 2
        utcTime = oh.utcStart + timedelta(seconds=captureTimeMiddel)
        

    return imageQualityScore
