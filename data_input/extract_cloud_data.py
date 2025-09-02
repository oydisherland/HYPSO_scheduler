from datetime import datetime, timedelta, timezone
import requests


def getForecast(lat: float, lon: float) -> dict:
    """ Get the forecast for a specific location

    :param lat: Latitude of the location
    :param lon: Longitude of the location
    :return: Forecast data as a dict
    """
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}

    r = requests.get(url.strip(), headers=headers, timeout=10)
    if r.status_code != 200:
        raise print("Error: " + str(r.status_code))

    return r.json()

def getCloudData(lat: float, lon: float, startTime, endTime) -> dict:
    """ Get the cloud data for at target for every hour within the time horizon

    :param lat: Latitude of the location
    :param lon: Longitude of the location
    :param start_time: Start time of the time horizon
    :param end_time: End time of the time horizon

    :return: Cloud data as a dict, 
    to extract a given datetime object from the dict, write:
            timeStr = '2025-02-13 09:00:00+00:00'
            storeThisKey = datetime.datetime.fromisoformat(timeStr)
            print(cloud_data[storeThisKey])
    """

    data = getForecast(63.50,10.39)
    # Navigate to the timeseries data
    timeseries = data["properties"]["timeseries"]

    # Dictionary to store time and cloud area fraction
    cloudData = {}

    # Process the timeseries data
    for entry in timeseries:
        time_str = entry["time"]  # Extract the timestamp as a string
        time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))  # Convert to datetime object
        cloudAreaFraction = entry["data"]["instant"]["details"]["cloud_area_fraction"]
        
        # Extract the data within start_time and end_time
        if time <= endTime and time >= startTime:
            # Store the extracted details in the dictionary
            cloudData[time] = cloudAreaFraction

    return cloudData


