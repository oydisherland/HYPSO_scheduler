from collections import namedtuple
"""
namedtuple is immutable, meaning that once it is created, it cannot be changed
dataclass could be used if flexibility is needed
"""

#Observation Horizon
OH = namedtuple("OH", ["utcStart", "utcEnd", "durationInDays", "delayInHours", "hypsoNr"])

#Ground target
GT = namedtuple("GT", ["id", "lat", "long", "priority", "idealIllumination"])

#Time Window
TW = namedtuple("TW", ["start", "end"])

#Target Time Window
TTW = namedtuple("TTW", ["GT", "TWs"])

#Observation Task
OT = namedtuple("OT", [ "GT", "start", "end"])

#Scheduling Parameters for the model
SP = namedtuple("SP", ["maxCaptures", "captureDuration", "transitionTime"])

#Buffering Task
BT = namedtuple("BT", ["GT", "start", "end"])

#Ground Station
GS = namedtuple("GS", ["id", "lat", "long", "minElevation"])

#Ground Station Time Windows
GSTW = namedtuple("GSTW", ["GS", "TWs"])

