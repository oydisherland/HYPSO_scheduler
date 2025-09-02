import skyfield.api as skf
import datetime 


def createSatelliteObject(HYPSOnr: int) -> skf.EarthSatellite:
    """ Create a satellite object for a given HYPSO satellite number
    Input: 
    - 1 for HYPSO 1
    - 2 for HYPSO 2
    """
    # HYPSO 1 data
    hypso1TleUrl = 'https://celestrak.org/NORAD/elements/gp.php?CATNR=51053&FORMAT=TLE'
    hypso1TlePath = 'HYPSO_scheduler/data_input/HYPSO_data/HYPSO-1_TLE.txt'

    if HYPSOnr == 1:
        # The skyfield API function to create an "EarthSatellite" object.
        skfH1 = skf.load.tle_file(hypso1TleUrl, filename=hypso1TlePath, reload=False)[0]
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
    target_location = skf.wgs84.latlon(targetLong * skf.N, targetLat * skf.E, 100.0)

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
    target_location = skf.wgs84.latlon(targetLong * skf.N, targetLat * skf.E, 100.0)

    # Convert the utc time to skyfield time type
    ts = skf.load.timescale()
    t = ts.utc(time.year, time.month, time.day, time.hour, time.minute, time.second)

    # Find the elevation of the satellite at the target location at time t
    difference = skfSat - target_location
    topocentric = difference.at(t)
    elevation, _, _ = topocentric.altaz()

    return elevation.degrees
