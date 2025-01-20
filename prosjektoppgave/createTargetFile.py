
import math as m
import numpy as np
import skyfield.api as skf
import pandas as pd
from datetime import timedelta
import pytz


#Calculate the difference in seconds between two utc_datetime objects.
def seconds_difference(utc_time1, utc_time2):
    difference = utc_time2 - utc_time1
    return difference.total_seconds()



def getTargetPasses(capture_time_seconds: int, timewindow: int, targets_file_path: str, tle_url: str, tle_file_path: str) -> list:
    """
    Find target information from the targets file and find capture events using satellite passes calculations
    Returns the target information as a list, including start times and end times of possible capturing of all targets
    """

    # The skyfield API function to create an "EarthSatellite" object.
    skf_h1 = skf.load.tle_file(tle_url, filename=tle_file_path, reload=False)[0]

    # Timestamps also require a skyfield type
    ts = skf.load.timescale()
    t0 = ts.now()

    # Read data from targets.csv into the array targets
    targets_df = pd.read_csv(targets_file_path)
    targets = targets_df.values.tolist()
    updated_targets = []

    #Loop through the targets and calculate earliest start time and latest start time for capturing
    for target in targets:

        target = target[0].split(';')
        longitude = target[1]
        latitude = target[2]
        elevation = target[3]

        # 'wgs84' refers to the system used to define latitude and longitude coordinates
        target_location = skf.wgs84.latlon(float(longitude) * skf.N, float(latitude) * skf.E, 100.0)

        #Find events where the satellite is within elevation of the target within the timewindow
        timestamps, types = skf_h1.find_events(target_location, t0, t0 + timewindow, altitude_degrees=float(elevation))

        target_startTimes = []
        target_endTimes = []

        #For each target find all start times and end times of capturing
        for i in range(len(timestamps)):
            if types[i] == 0:
                target_startTimes.append(timestamps[i].utc_datetime().replace(microsecond=0))
            if types[i] == 2:
                utc_endtime = timestamps[i].utc_datetime().replace(microsecond=0) - timedelta(seconds=capture_time_seconds)
                target_endTimes.append(utc_endtime)

        #Check if types of event occuring in the start_times and end_times lists are correlating to the same pass
        #One pass typically takes 50-150 seconds, thus bigger time differences than 300 second can be omitted
        for i in range(len(target_startTimes)):
            try: 
                time_diff = seconds_difference(target_startTimes[i], target_endTimes[i])
    
                if time_diff > 300:
                    print("Time difference between start and end time: ", time_diff, ", the times are omitted")
                    target_startTimes.remove(i)
                    target_endTimes.remove(i)
            except IndexError as e:
                print(f"IndexError: {e}")
                break

        #Add the list of start times and end times to the target info list
        target.append(target_startTimes)
        target.append(target_endTimes)
        updated_targets.append(target)

    # Determine the maximum length of the lists
    max_length = max(len(target[-2]) for target in updated_targets)

    #Check that the same length counts for start time and end time
    max_length_2 = max(len(target[-1]) for target in updated_targets)
    if(max_length_2 != max_length):
        print("ERROR: max length start time: ", max_length, ", max length end time: ", max_length_2)

    # Fill the smaller lists with empty elements to match the maximum length
    for target in updated_targets:
        start_times = target[-2]
        end_times = target[-1]
        while len(start_times) < max_length:
            start_times.append("")
        while len(end_times) < max_length:
            end_times.append("")
        # Update the target with the new start_times and end_times lists
        target[-2] = start_times
        target[-1] = end_times
   
    return updated_targets



### EXTRACT THE TARGET INFORMATION ###

# Parameters related to the scheduling
capture_time = 50 #seconds
timewindow_days = 2

# HYPSO data from TLE file
hypso_tle_url = 'https://celestrak.org/NORAD/elements/gp.php?CATNR=51053&FORMAT=TLE'
tle_path = 'HYPSO_scheduler/prosjektoppgave/HYPSO-1_TLE.txt'
targets_file_path = 'HYPSO_scheduler/prosjektoppgave/targets.csv'




updated_targets = getTargetPasses(capture_time, timewindow_days, targets_file_path, hypso_tle_url, tle_path)
 #Write the updated targets to a new csv file
updated_targets_hearder = ['name', 'latitude', 'longitude, 'minElevation', 
                        'maxCloudCover', 'priority', 'exposure', 'capture_mode', 
                        'default_capture_mode', 'start_times', 'end_times']
updated_targets_df = pd.DataFrame(updated_targets, columns=updated_targets_hearder)

# Write the DataFrame to a CSV file
updated_targets_df.to_csv('HYPSO_scheduler/prosjektoppgave/updated_targets.csv', index=False)
