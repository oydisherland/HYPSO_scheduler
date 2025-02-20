from scheduling_model import  OT, GT

""" Objective function repserenting the sum of the priority of the targets observed """
def objectiveFunctionPriority(otList: list):

    priority = 0
    for ot in otList:
        priority += ot.GT.priority
    return priority

""" Objective function representing the angle between satellite and target when capturing """
def objectiveFunctionImageQuality(otList:list):

    return 0
