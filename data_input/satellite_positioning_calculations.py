import skyfield.api as skf
from skyfield import almanac
import datetime 
import os
import requests

ts = skf.load.timescale()

def updateTLE (HYPSOnr: int):

    url = f'https://celestrak.com/NORAD/elements/gp.php?NAME=HYPSO-{HYPSOnr}&FORMAT=TLE'
    filename = os.path.join(os.path.dirname(__file__), f"HYPSO_data/HYPSO-{HYPSOnr}_TLE.txt")

    skf_hypso = skf.load.tle_file(url, filename=filename, reload=False)[0]
    ts = skf.load.timescale()
    TLE_age = ts.now().utc_datetime() - skf_hypso.epoch.utc_datetime()

    TLE_age_hours = TLE_age.days*24 + TLE_age.seconds/3600.0

    if TLE_age_hours > 34:
        print(f'current TLE is {TLE_age_hours:7.4f} hours old')
        try:
            tle = requests.get(url)
            with open(filename, 'w') as file:
                for line in tle.text.splitlines():
                    file.write(line+'\n')
                file.close()
                print('TLE update successful\n')
        except:
            print('Error. TLE Update not successful')
    else:
        # print(f'Skipping TLE update, current TLE is only {TLE_age_hours:7.4f} hours old')
        return

def createSatelliteObject(HYPSOnr: int) -> skf.EarthSatellite:
    """ Create a satellite object for a given HYPSO satellite number
    Input: 
    - 1 for HYPSO 1
    - 2 for HYPSO 2
    """

    # HYPSO 1 data
    hypsoTleUrl = f'https://celestrak.com/NORAD/elements/gp.php?NAME=HYPSO-{HYPSOnr}&FORMAT=TLE'
    hypsoTlePath = os.path.join(os.path.dirname(__file__), f"HYPSO_data/HYPSO-{HYPSOnr}_TLE.txt")

    if HYPSOnr == 1 or HYPSOnr == 2:
        # The skyfield API function to create an "EarthSatellite" object.
        skfH1 = skf.load.tle_file(hypsoTleUrl, filename=hypsoTlePath, reload=False)[0]
        return skfH1
    else:
        raise ValueError("The HYPSO number is not valid")
    

def findSatelliteTargetPasses(targetLat: float, targetLong: float, targetElevation: float, startTime: datetime.datetime, endTime: datetime.datetime, hypsoNr: int) -> list:
    """ Find the passes of a satellite over a target location within a given time window
    Output:
    - List of tuples: (datetime, 'rise'/'culminate'/'set')
    """
    
    # Create a skyfield "EarthSatellite" object..
    skfSat = createSatelliteObject(hypsoNr)

    # 'wgs84' refers to the system used to define latitude and longitude coordinates
    target_location = skf.wgs84.latlon(targetLat * skf.N, targetLong * skf.E, 100.0)

    # Timestamps also require a skyfield type
    ts = skf.load.timescale()
    t0 = ts.utc(startTime.year, startTime.month, startTime.day, startTime.hour, startTime.minute, startTime.second)
    t1 = ts.utc(endTime.year, endTime.month, endTime.day, endTime.hour, endTime.minute, endTime.second)

    # Find events where the satellite is within elevation of the target in the time window
    timestamps, events = skfSat.find_events(target_location, t0, t1, altitude_degrees=targetElevation)
    
    # Process the events
    passes = []
    for ti, event in zip(timestamps, events):
        name = ('rise', 'culminate', 'set')[event]
        passes.append((ti.utc_datetime(), name))

    return passes


def findSatelliteTargetElevation(targetLat: float, targetLong: float, time: datetime.datetime, hypsoNr: int) -> float:
    """ Find the elevation of the satellite at a target location at a given time
    Output:
    - Elevation in degrees
    """
    # Create a skyfield "EarthSatellite" object.
    skfSat = createSatelliteObject(hypsoNr)

    # 'wgs84' refers to the system used to define latitude and longitude coordinates
    target_location = skf.wgs84.latlon(targetLat * skf.N, targetLong * skf.E, 100.0)

    # Convert the utc time to skyfield time type
    t = ts.utc(time.year, time.month, time.day, time.hour, time.minute, time.second)

    # Find the elevation of the satellite at the target location at time t
    difference = skfSat - target_location
    topocentric = difference.at(t)
    elevation, _, _ = topocentric.altaz()

    return elevation.degrees

def findIllumminationPeriods(targetLat: float, targetLong: float, startTime: datetime.datetime, endTime: datetime.datetime) -> list:
    """ Find the periods where the target is illuminated by the sun within the timeinterval of startTime and endTime
    Output:
    - List of tuples (sunsetStartTime, sunsetEndTime)
    """

    # Load skyfield timescale 
    ts = skf.load.timescale()
    # Load planetary ephemeris
    eph = skf.load('de421.bsp')   
    # Define the location of the target
    location = skf.wgs84.latlon(targetLat, targetLong)

    # Define time range (today)
    t0 = ts.utc(startTime)
    t1 = ts.utc(endTime)

    # Build function for sunrise/sunset
    findSunriseSunset = almanac.sunrise_sunset(eph, location)

    # Find the times corresponding to event=0 (sunset) and event=1 (sunrise)
    times, events = almanac.find_discrete(t0, t1, findSunriseSunset)
    illuminatedPeriods = []

    if events.size == 0:
        return illuminatedPeriods

    if events[0] == 0:
        # first event is sunset, add a timestamp at start of OH
        illuminatedPeriods.append((t0.utc_datetime(), times[0].utc_datetime()))

    for time_curr, event_curr, time_next, event_next in zip(times[:-1], events[:-1], times[1:], events[1:]):

        if event_curr != 1 or event_next != 0:
            # The current event is not a sunrise, or the next event is not a sunset
            continue

        sunsetStartTime = time_curr.utc_datetime()
        sunsetEndTime = time_next.utc_datetime()
        illuminatedPeriods.append((sunsetStartTime, sunsetEndTime))

    if events[-1] == 1:
        # If last event is rise, add a timestamp at end of OH
        illuminatedPeriods.append((times[-1].utc_datetime(), t1.utc_datetime()))

    return illuminatedPeriods
