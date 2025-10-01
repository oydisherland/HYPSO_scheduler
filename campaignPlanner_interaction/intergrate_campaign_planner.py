import datetime
import pandas as pd
import skyfield.api as skf
from datetime import timedelta

from scheduling_model import OH, OT, GT, BT


# Functions to reformat the schedule data
def convertToUnixTime(timestamp: str) -> int:
    """Convert a timestamp string to Unix time"""
    dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f%z")
    return int(dt.timestamp())
def convertScheduleToDateTime(scheduleWithRelativeTime: list, oh: OH) -> list:
    """ Convert the time representation in the schedule to the absolute datetime representation, 
    instead of relative to the start of optimization horizon"""

    scheduleWithDatetimeObj = []
    for ot in scheduleWithRelativeTime:
        # Convert the start and end times of each OT to datetime objects
        captureStart = oh.utcStart + timedelta(seconds=ot.start)
        captureEnd = oh.utcStart + timedelta(seconds=ot.end)

        otWithDatetime = OT(
            GT=ot.GT,
            start=captureStart,
            end=captureEnd
        )
        scheduleWithDatetimeObj.append(otWithDatetime)
    return scheduleWithDatetimeObj
def getMiddleTime(startTime: datetime.datetime, endTime: datetime.datetime) -> datetime.datetime:
    """ Get the middle time of the capture window for a given observation target """
    middleTime = startTime + (endTime - startTime) / 2
    return middleTime

# Function that format schedule data into campaign planner commands
def createCmdFile(txtFilepath, cmdLines):
    """ Each element in the cmdLines list is written to the txt file as a command line """

    with open(txtFilepath, 'w') as f:
        for line in cmdLines:
            f.write(line.rstrip() + "\n")

def createCaptureCmdLine(observationTask: OT, hypsoNr: int, quaternions: dict): 
    if hypsoNr not in [1, 2]:
        print("Invalid hypsoNr")
        return None
    
    row = {}
    # Unix time
    row['-u'] = convertToUnixTime(getMiddleTime(observationTask.start, observationTask.end))
    # DontKnow
    row['-s'] = None
    # DontKnow - Duration of buffering could be calculated based on image size
    row['-d'] = 2442 if hypsoNr == 1 else 1509
    # Radio band
    row['-o'] = 0 if hypsoNr == 1 else 'xband' 
    # Hypso number
    row['-hypso'] = hypsoNr
    # DontKnow, maby registernumber where it is buffered, should probably be sat otherwise then, blir endret senere
    row['-b'] = 19
    # DontKnow
    row['-a'] = None
    # Geometry of capture
    row['-p'] = observationTask.GT.captureMode
    # Target name
    row['-n'] = observationTask.GT.id
    # Latitude
    row['-lat'] = float(observationTask.GT.lat)
    # Longitude
    row['-lon'] = float(observationTask.GT.long)
    # Elevation angle with sun
    row['--sunZenith'] = 45
    # Exposure time - get from targets.csv
    row['-e'] = float(observationTask.GT.exposureTime)
    # Quaternion r
    row['-r'] = quaternions['r']
    # Quaternion l
    row['-l'] = quaternions['l']
    # Quaternion j
    row['-j'] = quaternions['j']
    # Quaternion k
    row['-k'] = quaternions['k']
    # Capture mode
    row['--capture'] = None
    # Comment
    row['%'] = captureTime
    # Cloud cover 
    row['Predicted Cloud cover:'] = 0

    cmd_string = f'-u {row['-u']} -s -d {row['-d']:4d} -o {row['-o']:5} -hypso {row['-hypso']} -b {row['-b']} -a -p {row['-p']:11}{"":2}'\
                 f' -n {row['-n']:20} -lat {round(row['-lat'], 4):8.4f} -lon {round(row['-lon'], 4):9.4f} --sunZenith {round((row['--sunZenith']),2):8.4f} {"           "}'\
                 f' -e {row['-e']:6.2f} -r {row['-r']:20.17f}  -l {row['-l']:20.17f}  -j {row['-j']:20.17f}  -k {row['-k']:20.17f}'\
                 f' {"":24} {"--capture":9}'\
                 f' % {captureTime} - Predicted Cloud cover: {row['Predicted Cloud cover:']:5.1f} % Estimated downlink complete: \n'

    return cmd_string

def createBufferCmdLine( bufferTask: BT, hypsoNr: int, quaternions: dict, captureTimeMiddle: datetime.datetime,): 
    if hypsoNr not in [1, 2]:
        print("Invalid hypsoNr")
        return None
    row = {}
    # Unix time
    row['-u'] = convertToUnixTime(captureTimeMiddle)
    # DontKnow
    row['-s'] = None
    # DontKnow - Duration of buffering could be calculated based on image size
    row['-d'] = 2442 if hypsoNr == 1 else 1509
    # Radio band
    row['-o'] = 0 if hypsoNr == 1 else 'xband' 
    # Hypso number
    row['-hypso'] = hypsoNr
    # DontKnow, maby registernumber where it is buffered, should probably be sat otherwise then, blir endret senere
    row['-b'] = bufferTask.fileID
    # DontKnow
    row['-a'] = None
    # Geometry of capture
    row['-p'] = bufferTask.GT.captureMode
    # Target name
    row['-n'] = bufferTask.GT.id
    # Latitude
    row['-lat'] = float(bufferTask.GT.lat)
    # Longitude
    row['-lon'] = float(bufferTask.GT.long)
    # Elevation angle with sun
    row['--sunZenith'] = 45
    # Exposure time - get from targets.csv
    row['-e'] = float(bufferTask.GT.exposureTime)
    # Quaternion r
    row['-r'] = quaternions['r']
    # Quaternion l
    row['-l'] = quaternions['l']
    # Quaternion j
    row['-j'] = quaternions['j']
    # Quaternion k
    row['-k'] = quaternions['k']
    row['-t'] = getMiddleTime(bufferTask.start, bufferTask.end).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Capture mode
    row['--capture'] = None
    # Comment
    row['%'] = captureTimeMiddle
    # Cloud cover 
    row['Predicted Cloud cover:'] = 0

    cmd_string = f'-u {row['-u']} -s -d {row['-d']:4d} -o {row['-o']:5} -hypso {row['-hypso']} -b {row['-b']} -a -p {row['-p']:11}{"":2}'\
                 f' -n {row['-n']:20} -lat {round(row['-lat'], 4):8.4f} -lon {round(row['-lon'], 4):9.4f} --sunZenith {round((row['--sunZenith']),2):8.4f} {"           "}'\
                 f' -e {row['-e']:6.2f} -r {row['-r']:20.17f}  -l {row['-l']:20.17f}  -j {row['-j']:20.17f}  -k {row['-k']:20.17f}'\
                 f' -t {row['-t']:24} {"--capture":9}'\
                 f' % {captureTimeMiddle} - Predicted Cloud cover: {row['Predicted Cloud cover:']:5.1f} % Estimated downlink complete: \n'

    return cmd_string

# Function that reformats the campaign planner commands into schedule objects 
def getScheduleFromCmdLine(cmdLine: str, captureDurationSec: int = 60):
    
    cmds = cmdLine.split(" ")
    cmds = [cmd for cmd in cmds if cmd != '']

    cmdDict = {}
    for i, cmd in enumerate(cmds[:-1]):

        cmdNext = cmds[i+1]
        
        # If cmd is a flag it starts with "-"
        if cmd.startswith("-"):

            if cmdNext.startswith("-"):
                try:
                    float(cmdNext)
                except ValueError:
                    # If the next command is not a number, skip it
                    continue

            cmdDict[cmd] = cmdNext


    observationTask = OT(
        GT=GT(
            id=cmdDict['-n'],
            lat=cmdDict['-lat'],
            long=cmdDict['-lon'],
            priority=None,
            cloudCoverage=0,
            exposureTime=cmdDict['-e'],
            captureMode=cmdDict['-p']
        ),
        start = int(cmdDict['-u']) - captureDurationSec//2,
        end = int(cmdDict['-u']) + captureDurationSec//2
    )

    try: 
        cmdDict['--capture']
    except KeyError:
        return observationTask, 'Buffer'
    
    try:
        cmdDict['--buffer']
    except KeyError:
        return observationTask, 'Capture'
    
    return observationTask, 'Unknown'

# Function that creates a map between id of a target and its corresponding priority
def getTargetIdPriorityDict(targetsFilePath: str) -> dict:
    """ Get the priority of a list of target IDs from the targets.csv file """

    priorityIdDict = {}
    targets_df = pd.read_csv(targetsFilePath)
    targets = targets_df.values.tolist()

    for index, target in enumerate(targets):
        target = target[0].split(';')
        targetId = target[0]
        targetPriority = len(targets) - index

        priorityIdDict[targetId] = targetPriority

    return priorityIdDict