from collections import namedtuple
"""
namedtuple is immutable, meaning that once it is created, it cannot be changed
dataclass could be used if flexibility is needed
"""

#Observation Horizon
OH = namedtuple("OH", ["utcStart", "utcEnd"])

#Ground target
GT = namedtuple("GT", ["id", "lat", "long", "priority", "cloudCoverage" ,"exposureTime", "captureMode"])

#Time Window
TW = namedtuple("TW", ["start", "end"])

#Target Time Window
TTW = namedtuple("TTW", ["GT", "TWs"])

#Observation Task
OT = namedtuple("OT", [ "GT", "start", "end"])

#Scheduling Parameters for the model
SP = namedtuple("SP", ["maxCaptures", "captureDuration", "transitionTime", "hypsoNr"])

#Buffering Task
BT = namedtuple("BT", ["GT", "fileID", "start", "end"])

#Ground Station
GS = namedtuple("GS", ["id", "lat", "long", "minElevation"])

#Ground Station Time Windows
GSTW = namedtuple("GSTW", ["GS", "TWs"])

#Downlink Task
DT = namedtuple("DT", ["GT", "GS", "start", "end"])


## Functions to convert these nametuples to dictionaries for JSON serialization
def OH_toDict(oh):
    """Convert OH namedtuple to dictionary, and convert datetime objects to strings"""
    oh_dict = oh._asdict()
    oh_dict['utcStart'] = oh.utcStart.strftime("%Y-%m-%dT%H:%M:%SZ")
    oh_dict['utcEnd'] = oh.utcEnd.strftime("%Y-%m-%dT%H:%M:%SZ")
    return oh_dict

def GT_toDict(gt):
    """Convert GT namedtuple to dictionary"""
    return gt._asdict()

def TW_toDict(tw):
    """Convert TW namedtuple to dictionary"""
    return tw._asdict()

def TTW_toDict(ttw):
    """Convert TTW namedtuple to dictionary, handling nested namedtuples"""
    ttw_dict = ttw._asdict()
    ttw_dict['GT'] = GT_toDict(ttw.GT)
    ttw_dict['TWs'] = [TW_toDict(tw) for tw in ttw.TWs]
    return ttw_dict

def OT_toDict(ot):
    """Convert OT namedtuple to dictionary, handling nested namedtuples"""
    ot_dict = ot._asdict()
    ot_dict['GT'] = GT_toDict(ot.GT)
    return ot_dict

def SP_toDict(sp):
    """Convert SP namedtuple to dictionary"""
    return sp._asdict()

def BT_toDict(bt):
    """Convert BT namedtuple to dictionary, handling nested namedtuples"""
    bt_dict = bt._asdict()
    bt_dict['GT'] = GT_toDict(bt.GT)
    return bt_dict

def GS_toDict(gs):
    """Convert GS namedtuple to dictionary"""
    return gs._asdict()

def GSTW_toDict(gstw):
    """Convert GSTW namedtuple to dictionary, handling nested namedtuples"""
    gstw_dict = gstw._asdict()
    gstw_dict['GS'] = GS_toDict(gstw.GS)
    gstw_dict['TWs'] = [TW_toDict(tw) for tw in gstw.TWs]
    return gstw_dict

def DT_toDict(dt):
    """Convert DT namedtuple to dictionary, handling nested namedtuples"""
    dt_dict = dt._asdict()
    dt_dict['GT'] = GT_toDict(dt.GT)
    dt_dict['GS'] = GS_toDict(dt.GS)
    return dt_dict

def list_toDict(namedtuple_list, converter_func):
    """Convert a list of namedtuples to a list of dictionaries"""
    return [converter_func(item) for item in namedtuple_list]