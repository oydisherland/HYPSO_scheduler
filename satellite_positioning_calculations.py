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
    hypso1TlePath = 'HYPSO_scheduler/HYPSO_data/HYPSO-1_TLE.txt'

    if HYPSOnr == 1:
        # The skyfield API function to create an "EarthSatellite" object.
        skfH1 = skf.load.tle_file(hypso1TleUrl, filename=hypso1TlePath, reload=False)[0]
        return skfH1
    else:
        raise ValueError("The HYPSO number is not valid")
    

def findSatelliteTaregtPasses(targetLat: float, targetLong: float, targetElevation: float, startTime: datetime.datetime, endTime: datetime.datetime, hypsoNr: int) -> list:
    # The skyfield API function to create an "EarthSatellite" object.
    skfH1 = createSatelliteObject(hypsoNr)

    # 'wgs84' refers to the system used to define latitude and longitude coordinates
    target_location = skf.wgs84.latlon(float(targetLong) * skf.N, float(targetLat) * skf.E, 100.0)

    # Timestamps also require a skyfield type
    ts = skf.load.timescale()
    t0 = ts.utc(startTime.year, startTime.month, startTime.day, startTime.hour, startTime.minute, startTime.second)
    t1 = ts.utc(endTime.year, endTime.month, endTime.day, endTime.hour, endTime.minute, endTime.second)

    # Find events where the satellite is within elevation of the target within the time window
    timestamps, events = skfH1.find_events(target_location, t0, t1, altitude_degrees=targetElevation)

    # Process the events
    passes = []
    for ti, event in zip(timestamps, events):
        name = ('rise', 'culminate', 'set')[event]
        passes.append((ti.utc_datetime(), name))

    return passes

startTimeDelay = 0
long = 10.39
lat = 63.50
elevation = 10

# The skyfield API function to create an "EarthSatellite" object.
skfH1 = createSatelliteObject(1)

# 'wgs84' refers to the system used to define latitude and longitude coordinates
target_location = skf.wgs84.latlon(float(long) * skf.N, float(lat) * skf.E, 100.0)


# Timestamps also require a skyfield type
ts = skf.load.timescale()
t0 = ts.now() + datetime.timedelta(hours=startTimeDelay)
timewindow = datetime.timedelta(hours=10)
time = t0 + timewindow

difference = skfH1 - target_location


#Find events where the satellite is within elevation of the target within the timewindow
timestamps, types = skfH1.find_events(target_location, t0, t0 + timewindow, altitude_degrees=float(elevation))
print(len(timestamps))

# Check elevation at different times 
t = timestamps[0]
topocentric = difference.at(t)
alt, az, distance = topocentric.altaz()
print(alt.degrees)
t = timestamps[1]
topocentric = difference.at(t)
alt, az, distance = topocentric.altaz()
print(alt.degrees)
t = timestamps[2]
topocentric = difference.at(t)
alt, az, distance = topocentric.altaz()
# print(alt.degrees)
# print(timestamps[0].utc_datetime())
# print(timestamps[1].utc_datetime())
# print(timestamps[2].utc_datetime())

# startTime = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=startTimeDelay)

# passes = findSatelliteTaregtPasses(lat, long, elevation, startTime, startTime + timewindow, hypsoNr=1)
# print(len(passes))
        
        
