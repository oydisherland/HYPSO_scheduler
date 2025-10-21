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

# Functions to convert dictionaries back to namedtuples
def dict_toGT(gt_dict):
    """Convert dictionary to GT namedtuple"""
    return GT(
        id=gt_dict['id'],
        lat=gt_dict['lat'],
        long=gt_dict['long'],
        priority=gt_dict['priority'],
        cloudCoverage=gt_dict['cloudCoverage'],
        exposureTime=gt_dict['exposureTime'],
        captureMode=gt_dict['captureMode']
    )

def dict_toTW(tw_dict):
    """Convert dictionary to TW namedtuple"""
    return TW(
        start=tw_dict['start'],
        end=tw_dict['end']
    )

def dict_toTTW(ttw_dict):
    """Convert dictionary to TTW namedtuple"""
    gt = dict_toGT(ttw_dict['GT'])
    tws = [dict_toTW(tw_dict) for tw_dict in ttw_dict['TWs']]
    return TTW(GT=gt, TWs=tws)

def dict_toOT(ot_dict):
    """Convert dictionary to OT namedtuple"""
    gt = dict_toGT(ot_dict['GT'])
    return OT(GT=gt, start=ot_dict['start'], end=ot_dict['end'])

def dict_toBT(bt_dict):
    """Convert dictionary to BT namedtuple"""
    gt = dict_toGT(bt_dict['GT'])
    return BT(GT=gt, fileID=bt_dict['fileID'], start=bt_dict['start'], end=bt_dict['end'])

def dict_toGS(gs_dict):
    """Convert dictionary to GS namedtuple"""
    return GS(
        id=gs_dict['id'],
        lat=gs_dict['lat'],
        long=gs_dict['long'],
        minElevation=gs_dict['minElevation']
    )

def dict_toGSTW(gstw_dict):
    """Convert dictionary to GSTW namedtuple"""
    gs = dict_toGS(gstw_dict['GS'])
    tws = [dict_toTW(tw_dict) for tw_dict in gstw_dict['TWs']]
    return GSTW(GS=gs, TWs=tws)

def dict_toDT(dt_dict):
    """Convert dictionary to DT namedtuple"""
    gt = dict_toGT(dt_dict['GT'])
    gs = dict_toGS(dt_dict['GS'])
    return DT(GT=gt, GS=gs, start=dt_dict['start'], end=dt_dict['end'])

