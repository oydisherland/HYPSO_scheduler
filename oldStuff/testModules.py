import datetime
from HYPSO_scheduler.oldStuff.extractCloudData import get_cloudData


def test_get_cloudData():
    
    time_now = datetime.datetime.now(datetime.timezone.utc) 
    end_of_time_horizon = time_now + datetime.timedelta(hours=50) #time horizon is 48h starting 2h from now
    cloud_data = get_cloudData(63.50,10.39, time_now, end_of_time_horizon)
    assert cloud_data != None
    for key in cloud_data:
        print(key, cloud_data[key])
    
test_get_cloudData()

"""
What works:
I can retrive cloud coverage data for the time period of the optimization horizon,
given the longitude and the latitude of the target. 

NB: I had to change the longitude and latidue column in the updated_targets file because it was wrongly named

TODO:
- Rewrite the createTargetFile so it includes more functions for better code quality. 
See if some of the functios can be used to create a test function in this file. 

- Incorporate the coud coverage filter when the target file is created and eliminate the targets with cloud obstruction. 

"""