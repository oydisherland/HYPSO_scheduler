import csv
import os
from dataclasses import dataclass, fields, MISSING


@dataclass
class TransmissionParams:
    """
    Data class for transmission scheduling parameters.

    Attributes:
        bufferingTime: Time required to buffer capture data before it can be transmitted in seconds.
        afterCaptureTime: Time required after a capture for processing in seconds.
        interTaskTime: Time after a general task in seconds.
        interDownlinkTime: Time required between downlink tasks in seconds.
        downlinkDuration: Time needed for downlinking a capture in seconds.
        transmissionStartTime: How far into a ground station pass transmission can start in seconds.
        maxGSTWAhead Maximum number of ground station time windows ahead of the capture to consider when scheduling a buffering task
        maxBufferOffset: # Maximum offset between a capture and its buffering in seconds
        slidingInsertIterations: Number of iterations for sliding insert algorithm
        minGSWindowTime: Minimum time a ground station window must have to be considered for scheduling in seconds
        ohDuration: Observation horizon duration in seconds
        hypsoNr: Hyperspectral satellite number (1 or 2)

    """
    bufferingTime: float = 0.0
    afterCaptureTime: float = 0.0
    interTaskTime: float = 0.0
    interDownlinkTime: float = 0.0
    downlinkDuration: float = 0.0
    transmissionStartTime: float = 0.0
    maxGSTWAhead: int = 0
    maxBufferOffset: float = 0.0
    slidingInsertIterations: int = 1
    minGSWindowTime: float = 0.0
    ohDuration: float = 0.0
    hypsoNr: int = 1

def getInputParams(relativeFilePath: str) -> TransmissionParams:
    """
    Retrieve the input parameters for the transmission scheduling from a CSV file.

    Args:
        relativeFilePath (str): Relative path to the CSV file containing the parameters.

    Returns:
        TransmissionParams: An instance of the dataclass TransmissionParams populated with values from the CSV file.
    """
    filePath_inputParameters = os.path.join(os.path.dirname(__file__), relativeFilePath)
    paramsDict = csvToDict(filePath_inputParameters)

    filtered = {}

    for f in fields(TransmissionParams):
        if f.name in paramsDict:
            try:
                filtered[f.name] = f.type(paramsDict[f.name])  # convert to field type
            except (TypeError, ValueError):
                filtered[f.name] = paramsDict[f.name]  # fallback if conversion fails
        elif f.default is not MISSING:
            filtered[f.name] = f.default
        elif f.default_factory is not MISSING:
            filtered[f.name] = f.default_factory()
        else:
            filtered[f.name] = None

    p = TransmissionParams(**filtered)

    p.minGSWindowTime = p.transmissionStartTime + 0.1 * p.downlinkDuration
    p.ohDuration = 24 * 3600 * float(paramsDict["durationInDaysOH"])
    return p

def csvToDict(filepath):
    """
    Reads a CSV file and returns a dictionary where each row's first column is the key and the second column is the value.
    Ignores rows starting with #.
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