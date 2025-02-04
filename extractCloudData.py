from datetime import datetime, timedelta, timezone
import requests



def get_forecast(lat: float, lon: float) -> dict:
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
        raise BadResponse("Error: " + str(r.status_code))

    return r.json()

def get_cloudData(lat: float, lon: float, start_time, end_time) -> dict:
    """ Get the cloud data for at target for every hour within the time horizon

    :param lat: Latitude of the location
    :param lon: Longitude of the location
    :param start_time: Start time of the time horizon
    :param end_time: End time of the time horizon
    :return: Cloud data as a dict
    """

    data = get_forecast(63.50,10.39)
    # Navigate to the timeseries data
    timeseries = data["properties"]["timeseries"]

    # Dictionary to store time and cloud area fraction
    cloud_data = {}

    # Process the timeseries data
    for entry in timeseries:
        time_str = entry["time"]  # Extract the timestamp as a string
        time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))  # Convert to datetime object
        cloud_area_fraction = entry["data"]["instant"]["details"]["cloud_area_fraction"]
        
        # Extract the data within start_time and end_time
        if time <= end_time and time >= start_time:
            # Store the extracted details in the dictionary
            cloud_data[time] = cloud_area_fraction

    return cloud_data


