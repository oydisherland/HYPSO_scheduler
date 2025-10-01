import json
from dataclasses import dataclass

@dataclass
class TargetData:
    name: str
    lat: float
    lon: float
    elev: float
    cc: float
    exp: float
    mode: str
    night: int
    t0: str
    t1: str


def parse_target_json(json_obj):
    """
    Parse a JSON object into a TargetData object
    Only include keys that are defined in the TargetData dataclass
    """
    valid_keys = {field.name for field in TargetData.__dataclass_fields__.values()}
    filtered = {k: v for k, v in json_obj.items() if k in valid_keys}
    return TargetData(**filtered)



def getTargetDataFromJsonFile(targetsJsonFile: str):
    """ 
    Get the target data from a JSON file
    Input: path to the JSON file
    Output: List of TargetData objects 
    """

    with open(targetsJsonFile, 'r') as f:
        targets_json = json.load(f)
    targets = [parse_target_json(target) for target in targets_json]
    return targets


# targetData = testJsonParsing('HYPSO_scheduler/data_input/HYPSO_data/targets.json')

# for target in targetData:
#     id = target.name
#     latitude = target.lat
#     longitude = target.lon
#     elevation = target.elev
#     cloudCover = target.cc
#     exposure = target.exp
#     imagingMode = target.mode
#     nightOnly = target.night
#     timeWindowStart = target.t0
#     timeWindowEnd = target.t1
#     print(f"ID: {id}, Lat: {latitude}, Lon: {longitude}")


# It works!
