import datetime
import data_postprocessing.algorithmData_api as algDataApi

from pathlib import Path

from datetime import timedelta
from data_preprocessing.parseTargetsFile import getTargetIdPriorityDictFromJson
from data_input.utility_functions import InputParameters


from scheduling_model import OH, OT, GT, BT, OH, DT




#### FUNCTIONS TO CREATE CAMPAIGN PLANNER COMMAND LINES ####

# Function that format schedule data into campaign planner commands
def createCaptureCmdLine(observationTask_dt: OT, hypsoNr: int, quaternions: dict): 
    """ Create the command line for capturing an observation task
    Output:
    - cmd_string: one command line string that Hypso can parse
    """
    if hypsoNr not in [1, 2]:
        print("Invalid hypsoNr")
        return None
    observationMiddleTime = algDataApi.getMiddleTime(observationTask_dt.start, observationTask_dt.end)
    row = {}
    # Unix time
    row['-u'] = algDataApi.convertToUnixTime(observationMiddleTime)
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
    row['-p'] = observationTask_dt.GT.captureMode
    # Target name
    row['-n'] = observationTask_dt.GT.id
    # Latitude
    row['-lat'] = float(observationTask_dt.GT.lat)
    # Longitude
    row['-lon'] = float(observationTask_dt.GT.long)
    # Elevation angle with sun
    row['--sunZenith'] = 45
    # Exposure time - get from targets.csv
    row['-e'] = float(observationTask_dt.GT.exposureTime)
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
    row['%'] = observationMiddleTime
    # Cloud cover 
    row['Predicted Cloud cover:'] = 0

    cmd_string = f'-u {row['-u']} -s -d {row['-d']:4d} -o {row['-o']:5} -hypso {row['-hypso']} -b {row['-b']} -a -p {row['-p']:11}{"":2}'\
                 f' -n {row['-n']:20} -lat {round(row['-lat'], 4):8.4f} -lon {round(row['-lon'], 4):9.4f} --sunZenith {round((row['--sunZenith']),2):8.4f} {"           "}'\
                 f' -e {row['-e']:6.2f} -r {row['-r']:20.17f}  -l {row['-l']:20.17f}  -j {row['-j']:20.17f}  -k {row['-k']:20.17f}'\
                 f' {"":24} {"--capture":9} {"":9}'\
                 f' % {observationMiddleTime} - Predicted Cloud cover: {row['Predicted Cloud cover:']:5.1f} % Estimated downlink complete: \n'

    return cmd_string
def createBufferCmdLine(bufferTask_dt: BT, downlinkTask_dt: DT, hypsoNr: int, quaternions: dict): 
    """ Create the command line for buffering an observation task
    Output:
    - cmd_string: one command line string that Hypso can parse
    """
    if hypsoNr not in [1, 2]:
        print("Invalid hypsoNr")
        return None
    bufferTaskMiddleTime = algDataApi.getMiddleTime(bufferTask_dt.start, bufferTask_dt.end)

    row = {}
    # Unix time
    row['-u'] = algDataApi.convertToUnixTime(bufferTaskMiddleTime)
    # DontKnow
    row['-s'] = None
    # DontKnow - Duration of buffering could be calculated based on image size
    row['-d'] = 2442 if hypsoNr == 1 else 1509
    # Radio band
    row['-o'] = 0 if hypsoNr == 1 else 'xband' 
    # Hypso number
    row['-hypso'] = hypsoNr
    # DontKnow, maby registernumber where it is buffered, should probably be sat otherwise then, blir endret senere
    row['-b'] = bufferTask_dt.fileID
    # DontKnow
    row['-a'] = None
    # Geometry of capture
    row['-p'] = bufferTask_dt.GT.captureMode
    # Target name
    row['-n'] = bufferTask_dt.GT.id
    # Latitude
    row['-lat'] = float(bufferTask_dt.GT.lat)
    # Longitude
    row['-lon'] = float(bufferTask_dt.GT.long)
    # Elevation angle with sun
    row['--sunZenith'] = 45
    # Exposure time - get from targets.csv
    row['-e'] = float(bufferTask_dt.GT.exposureTime)
    # Quaternion r
    row['-r'] = quaternions['r']
    # Quaternion l
    row['-l'] = quaternions['l']
    # Quaternion j
    row['-j'] = quaternions['j']
    # Quaternion k
    row['-k'] = quaternions['k']
    row['-t'] = bufferTaskMiddleTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Capture mode
    row['--capture'] = None
    # Comment
    row['%'] = bufferTaskMiddleTime
    # Cloud cover
    row['Predicted Cloud cover:'] = 0

    cmd_string = f'-u {row['-u']} -s -d {row['-d']:4d} -o {row['-o']:5} -hypso {row['-hypso']} -b {row['-b']} -a -p {row['-p']:11}{"":2}'\
                 f' -n {row['-n']:20} -lat {round(row['-lat'], 4):8.4f} -lon {round(row['-lon'], 4):9.4f} --sunZenith {round((row['--sunZenith']),2):8.4f} {"           "}'\
                 f' -e {row['-e']:6.2f} -r {row['-r']:20.17f}  -l {row['-l']:20.17f}  -j {row['-j']:20.17f}  -k {row['-k']:20.17f}'\
                 f' {" -t " + row['-t']:24} {"":9} {"--buffer":9}'\
                 f' % {bufferTaskMiddleTime} - Predicted Cloud cover: {row['Predicted Cloud cover:']:5.1f} % Estimated downlink complete: {downlinkTask_dt.end.strftime("%Y-%m-%d %H:%M:%S")} \n'

    return cmd_string 
def createCmdLinesForCaptureAndBuffering(observationSchedule: list, bufferSchedule: list, downlinkSchedule: list, inputParameters: InputParameters, oh: OH) -> list:
    """ Creates a list of command lines for capturing and buffering based on the observation and buffer schedules
    Output:
    - cmdLines: list of command lines that Hypso can parse
    """
    schedule_dt = algDataApi.convertOTListToDateTime(observationSchedule, oh)
    bufferschedule_dt = algDataApi.convertBTListToDateTime(bufferSchedule, oh)
    downlinkschedule_dt = algDataApi.convertDTListToDateTime(downlinkSchedule, oh)
    combinedSchedule = algDataApi.CombineCaptureAndBufferSchedules(schedule_dt, bufferschedule_dt)

    cmdLines = []
    scheduledOTs = {} 
    for task, taskType in combinedSchedule:
        if taskType == "Capture":
            groundTarget = task.GT
            quaternions = algDataApi.calculateQuaternions(int(inputParameters.hypsoNr), groundTarget, task.start)
            newCaptureCommandLine = createCaptureCmdLine(task, int(inputParameters.hypsoNr), quaternions)
            cmdLines.append(newCaptureCommandLine)
            scheduledOTs[task.GT.id] = [quaternions, task]  # Store quaternions and task for buffer use
        elif taskType == "Buffer":
            quaternions, ot = scheduledOTs.get(task.GT.id)
            downlinkTask = next((dt for dt in downlinkschedule_dt if dt.GT.id == task.GT.id), None)
            newBufferCommandLine = createBufferCmdLine(task, downlinkTask, int(inputParameters.hypsoNr), quaternions)
            cmdLines.append(newBufferCommandLine)
    return cmdLines
def createCmdFile(txtFilepath, cmdLines):
    """ Each element in the cmdLines list is written to the txt file as a command line """

    txtPath = Path(txtFilepath)
    # Create parent folder if it doesn't exist
    txtPath.parent.mkdir(parents=True, exist_ok=True)

    # Write lines to file
    with open(txtPath, 'w') as f:
        for line in cmdLines:
            f.write(line.rstrip() + "\n")


#### FUNCTIONS TO RECREATE SCHEDULE FROM CAMPAIGN PLANNER COMMAND FILE ####
# Function that reformats the campaign planner commands into schedule objects 
def getScheduleFromCmdLine(targetFilePath: str,cmdLine: str, oh: OH, bufferDurationSec: int, captureDurationSec: int = 60):
    """ Takes in a command line string and returns an OT object representing the same cmd and the type of command
    Output:
    - observationTask: OT object created from the command line
    - commandType: 'Capture', 'Buffer' or 'Unknown'
    """
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
    
    # Recreate target data object to find objectiveValue
    targetIdPriorityDict = getTargetIdPriorityDictFromJson(targetFilePath)
    gt = GT(
            id=cmdDict['-n'],
            lat=cmdDict['-lat'],
            long=cmdDict['-lon'],
            priority=targetIdPriorityDict.get(cmdDict['-n'], 0),
            cloudCoverage=0,
            exposureTime=cmdDict['-e'],
            captureMode=cmdDict['-p']
        )

    if '--capture' in cmdDict:
        # convert start and end time to relative time
        startDateTime = algDataApi.convertFromUnixTime(int(cmdDict['-u'])) - timedelta(seconds=captureDurationSec//2)
        endDateTime = algDataApi.convertFromUnixTime(int(cmdDict['-u'])) + timedelta(seconds=captureDurationSec//2)
        relativeStart = int((startDateTime - oh.utcStart).total_seconds())
        relativeEnd = int((endDateTime - oh.utcStart).total_seconds())

        
        observationTask = OT(
            GT = gt,
            start = relativeStart,
            end = relativeEnd
        )
        return observationTask, 'Capture'
    elif '--buffer' in cmdDict:
        startDateTime = algDataApi.convertFromUnixTime(int(cmdDict['-u'])) - timedelta(seconds=bufferDurationSec//2)
        endDateTime = algDataApi.convertFromUnixTime(int(cmdDict['-u'])) + timedelta(seconds=bufferDurationSec//2)
        relativeStart = int((startDateTime - oh.utcStart).total_seconds())
        relativeEnd = int((endDateTime - oh.utcStart).total_seconds())
        bufferTask = BT(
                    GT = gt,
                    fileID = int(cmdLine.split(" -b ")[1].split(" ")[0]),
                    start = relativeStart,
                    end = relativeEnd
                )
        return bufferTask, 'Buffer'
    else:
        return observationTask, 'Unknown'

def recreateOTListFromCmdFile(targetFilePath: str, cmdFilePath: str, oh: OH, bufferDurationSec: int, captureDurationSec: int = 60):
    """ Reads a command file and recreates the list of OT objects from the command lines
    Output:
    - otList: list of OT objects
    """
    otList = []
    with open(cmdFilePath, 'r') as f:
        cmdLines = f.readlines()
        for cmdLine in cmdLines:
            ot, commandType = getScheduleFromCmdLine(targetFilePath, cmdLine, oh, bufferDurationSec, captureDurationSec)
            if commandType == 'Capture':
                otList.append(ot)
    return otList
def recreateBTListFromCmdFile(targetFilePath: str, cmdFilePath: str, oh: OH, bufferDurationSec: int, captureDurationSec: int = 60):
    """ Reads a command file and recreates the list of BT objects from the command lines
    Output:
    - btList: list of BT objects
    """
    btList = []
    with open(cmdFilePath, 'r') as f:
        cmdLines = f.readlines()
        for cmdLine in cmdLines:
            bt, commandType = getScheduleFromCmdLine(targetFilePath, cmdLine, oh, bufferDurationSec, captureDurationSec)
            if commandType == 'Buffer':
                btList.append(bt)
    return btList
def recreateDTListFromCmdFile(targetFilePath: str, cmdFilePath: str, oh: OH, bufferDurationSec: int, captureDurationSec: int = 60):
    """ Reads a command file and recreates the list of DT objects from the command lines
    Output:
    - dtList: list of DT objects
    """
    dtList = []
    with open(cmdFilePath, 'r') as f:
        cmdLines = f.readlines()
        for cmdLine in cmdLines:
            bt, commandType = getScheduleFromCmdLine(targetFilePath, cmdLine, oh, bufferDurationSec, captureDurationSec)
            if commandType == 'Buffer':
                # Create corresponding DT object
                estimatedEndTime = cmdLine.split("Estimated downlink complete:")[1].strip()
                estimatedEndTime = datetime.datetime.strptime(estimatedEndTime, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)

                dt = DT(
                    GT = bt.GT,
                    GS = None,  # Ground station info not available in cmd line
                    start = estimatedEndTime - timedelta(seconds=bufferDurationSec),
                    end = estimatedEndTime
                )
                dtList.append(dt)
    return dtList

# Sorts the cmd file by capture time, not needed anymore, can remove..
def sortCmdFileByCaptureTime(inputCmdFilePath: str, outputCmdFilePath: str):
    """ Sorts the command lines in a command file by capture time and writes to a new file """

    with open(inputCmdFilePath, 'r') as f:
        cmdLines = f.readlines()
    
    # Extract capture times and pair with command lines
    cmdTimePairs = []
    for cmdLine in cmdLines:
        cmds = cmdLine.split(" ")
        cmds = [cmd for cmd in cmds if cmd != '']
        for i, cmd in enumerate(cmds[:-1]):
            if cmd == '-u':
                captureTimeUnix = int(cmds[i+1])
                cmdTimePairs.append((captureTimeUnix, cmdLine))
                break
    
    # Sort by capture time
    cmdTimePairs.sort(key=lambda x: x[0])

    # Write sorted command lines to output file
    with open(outputCmdFilePath, 'w') as f:
        for _, cmdLine in cmdTimePairs:
            f.write(cmdLine)
