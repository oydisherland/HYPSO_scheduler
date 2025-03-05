import datetime
import pandas as pd

from HYPSO_scheduler.oldStuff.extractCloudData import get_cloudData
from HYPSO_scheduler.oldStuff.calculatePasses import getTargetPasses


# Parameters related to the scheduling
capture_time = 50 #seconds
timewindow_days = 2

# HYPSO data from TLE file
hypso_tle_url = 'https://celestrak.org/NORAD/elements/gp.php?CATNR=51053&FORMAT=TLE'
tle_path = 'HYPSO_scheduler/HYPSO-1_TLE.txt'
targets_file_path = 'HYPSO_scheduler/targets.csv'


### EXTRACT THE TARGET INFORMATION ###
updated_targets = getTargetPasses(capture_time, timewindow_days, targets_file_path, hypso_tle_url, tle_path)

targets_without_clouds = []

for target in updated_targets:
    # Extract the latitude and longitude of the target
    latitude = float(target[1])
    longitude = float(target[2])
    # Extract the start times and end times of the target
    start_times = target[-2]
    end_times = target[-1]
    
    #Extract the maximum cloud coverage of the target
    maxCloudCoverage = target[4]

    # Extract the cloud data for the target
    time_now = datetime.datetime.now(datetime.timezone.utc) 
    end_of_time_horizon = time_now + datetime.timedelta(hours=50) #time horizon is 48h starting 2h from now
    cloud_data = get_cloudData(63.50,10.39, time_now, end_of_time_horizon)
    assert cloud_data != None

    if target[0] == 'trondheim':

        for key in cloud_data:
            timeStr = '2025-01-23 09:00:00+00:00'
            storeThisKey = datetime.datetime.fromisoformat(timeStr)
            print( key, cloud_data[key])
            print(cloud_data[storeThisKey])
            if cloud_data[key] > maxCloudCoverage:
                print("Cloud coverage too high")
                targets_without_clouds.append(target)
                break
    
    

        
    
# Fill the smaller lists with empty elements to match the maximum length
# for target in updated_targets:
#     start_times = target[-2]
#     end_times = target[-1]
#     while len(start_times) < max_length:
#         start_times.append("")
#     while len(end_times) < max_length:
#         end_times.append("")
#     Update the target with the new start_times and end_times lists
#     target[-2] = start_times
#     target[-1] = end_times
#Write the updated targets to a new csv file
updated_targets_hearder = ['name', 'latitude', 'longitude', 'minElevation', 
                        'maxCloudCover', 'priority', 'exposure', 'capture_mode', 
                        'default_capture_mode', 'start_times', 'end_times']
updated_targets_df = pd.DataFrame(updated_targets, columns=updated_targets_hearder)

# Write the DataFrame to a CSV file
updated_targets_df.to_csv('HYPSO_scheduler/updated_targets.csv', index=False)