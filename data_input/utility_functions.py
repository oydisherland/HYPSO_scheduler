import csv
import json
from dataclasses import dataclass, asdict

def csvToDict(filepath) -> dict:
    """
    Reads a CSV file and returns a dictionary where each row's first column is the key and the second column is the value.
    Ignores rows starting with #.
    Output:
    - dict: dictionary with key-value pairs ( the first and second element of each row) from the CSV file
    """
    dict= {}
    with open(filepath, mode='r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
            if len(row) >= 2:
                key = row[0].strip()
                value = row[1].strip()
                dict[key] = value
    return dict

@dataclass
class InputParameters:
    testName: str
    maxCaptures: int
    captureDuration: int
    transitionTime: int
    startTimeOH: str
    durationInDaysOH: int
    delayInHoursOH: int
    hypsoNr: int
    populationSize: int
    isTabooBankFIFO: bool
    iqNonLinear: bool
    nsga2Runs: int
    alnsRuns: int
    maxTabBank: int
    desNumber: int

    @classmethod
    def from_csv(cls, filepath: str):
        """Create InputParameters from CSV file"""
        params_dict = csvToDict(filepath)
        return cls(
            testName=params_dict['testName'],
            maxCaptures=int(params_dict['maxCaptures']),
            captureDuration=int(params_dict['captureDuration']),
            transitionTime=int(params_dict['transitionTime']),
            startTimeOH=params_dict['startTimeOH'],
            durationInDaysOH=int(params_dict['durationInDaysOH']),
            delayInHoursOH=int(params_dict['delayInHoursOH']),
            hypsoNr=int(params_dict['hypsoNr']),
            populationSize=int(params_dict['populationSize']),
            isTabooBankFIFO=params_dict['isTabooBankFIFO'].lower() == 'true',
            iqNonLinear=params_dict['iqNonLinear'].lower() == 'true',
            nsga2Runs=int(params_dict['NSGA2Runs']),
            alnsRuns=int(params_dict['ALNSRuns']),
            maxTabBank=int(params_dict['maxTabBank']),
            desNumber=int(params_dict['desNumber'])
        )
    
    def to_json(self) -> str:
        """Convert InputParameters instance to JSON string"""
        return json.dumps(asdict(self), indent=4)

