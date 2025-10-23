import csv
import json
import os
import warnings
from dataclasses import dataclass, fields, MISSING


@dataclass
class TransmissionParams:
    """
    Data class for transmission scheduling parameters.

    Attributes:
        bufferingTime: Time required to buffer capture data before it can be transmitted in seconds.
        afterCaptureTime: Time required after a capture for processing in seconds.
        interTaskTime: Time after a general task in seconds.
        downlinkDuration: Time needed for downlinking a capture in seconds.
        transmissionStartTime: How far into a ground station pass transmission can start in seconds.
        maxLatency: Maximum number of seconds between a capture and its downlink
        slidingInsertIterations: Number of iterations for sliding insert algorithm
        reInsertIterations: Number of iterations for re-insertion algorithm
        minDownlinkFraction: Minimum fraction of a capture that must be able to be downlinked in a GS pass
        minGSWindowTime: Minimum time a ground station window must have to be considered for scheduling in seconds
        ohDuration: Observation horizon duration in seconds
        hypsoNr: Hyperspectral satellite number (1 or 2)
        captureDuration: Duration of a capture in seconds
        maxBufferFiles: Maximum number of captures that can be stored in the buffer.
        bufferStartID: File ID of the highest priority buffer, all other files will have incremented IDs.
        overLappingWithCaptureSetback: The number of seconds that should be taken off the available downlink time
            during a ground station pass if an observation task is scheduled during that pass
    """
    bufferingTime: float = 0.0
    afterCaptureTime: float = 0.0
    interTaskTime: float = 0.0
    downlinkDuration: float = 0.0
    transmissionStartTime: float = 0.0
    maxLatency: float = 0.0
    slidingInsertIterations: int = 1
    reInsertIterations: int = 1
    minDownlinkFraction: float = 0.0
    minGSWindowTime: float = 0.0
    ohDuration: float = 0.0
    hypsoNr: int = 1
    captureDuration: float = 0.0
    maxBufferFiles: int = 1
    bufferStartID: int = 1
    overLappingWithCaptureSetback: float = 0.0

    # Warning should be thrown because these parameters should not be changed after initialization
    def __setattr__(self, name, value):
        if name in self.__dict__:
            warnings.warn(
                f"Transmission Parameter field '{name}' has been modified after initialization. This is not recommended.",
                UserWarning,
                stacklevel=2
            )
        super().__setattr__(name, value)

def getTransmissionInputParams(relativeFilePath: str) -> TransmissionParams:
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

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        # Convert units
        p.ohDuration = 24 * 3600 * float(paramsDict["durationInDaysOH"])
        p.maxLatency = 3600 * float(paramsDict["maxLatencyHours"])
        # Evaluate dependent parameters
        p.minGSWindowTime = p.transmissionStartTime + p.minDownlinkFraction * p.downlinkDuration
        p.maxBufferFiles = int(paramsDict["maxBufferFilesH2"]) if p.hypsoNr == 2 else int(paramsDict["maxBufferFilesH1"])
        p.bufferStartID = int(paramsDict["bufferStartIDH2"]) if p.hypsoNr == 2 else int(paramsDict["bufferStartIDH1"])

    return p

def csvToDict(filepath):
    """
    Reads a CSV file and returns a dictionary where each row's first column is the key and the second column is the value.
    Ignores rows starting with #.
    """
    dic = {}
    with open(filepath, mode='r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
            if len(row) >= 2:
                key = row[0].strip()
                value = row[1].strip()
                dic[key] = value
    return dic

def getTransmissionInputParamsFromJsonFile(jsonFilePath: str) -> TransmissionParams:
    """
    Retrieve the input parameters for the transmission scheduling from a JSON file.

    Args:
        jsonFilePath (str): Path to the JSON file containing the parameters.

    Returns:
        TransmissionParams: An instance of the dataclass TransmissionParams populated with values from the JSON file.
    """
    with open(jsonFilePath, "r") as f:
        paramsDict = json.load(f)

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

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        # Convert units
        p.ohDuration = 24 * 3600 * float(paramsDict["durationInDaysOH"])
        p.maxLatency = 3600 * float(paramsDict["maxLatencyHours"])
        # Evaluate dependent parameters
        p.minGSWindowTime = p.transmissionStartTime + p.minDownlinkFraction * p.downlinkDuration
        p.maxBufferFiles = int(paramsDict["maxBufferFilesH2"]) if p.hypsoNr == 2 else int(paramsDict["maxBufferFilesH1"])
        p.bufferStartID = int(paramsDict["bufferStartIDH2"]) if p.hypsoNr == 2 else int(paramsDict["bufferStartIDH1"])

    return p
