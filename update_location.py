from datetime import datetime, timedelta

import requests

from models import Location
from update_trip import update_trip
from utils import distance_m, ft_to_m, kts_to_mps

DELAY_NO_LOCATION_MIN = 10
DELAY_FOUND_LOCATION_MIN = 2

AIRPORT_MAX_DISTANCE_KM = 50
AIRPORT_MAX_ALTITUDE_M = 1000


def determine_nearest_airport(app, latitude, longitude, altitude_m):
    nearest_airport = None
    nearest_distance = float("inf")

    # Search within roughly 1 degree (about 110km at the equator)
    # This creates a square bounding box for initial filtering
    airports = app.database.airport.find(
        {
            "latitude": {"$gte": latitude - 1, "$lte": latitude + 1},
            "longitude": {"$gte": longitude - 1, "$lte": longitude + 1},
        }
    )

    for airport in airports:
        d = distance_m(latitude, longitude, airport["latitude"], airport["longitude"])
        if d < nearest_distance:
            nearest_distance = d
            nearest_airport = airport

    # make sure it's close enough and not too high
    if not nearest_airport or nearest_distance > AIRPORT_MAX_DISTANCE_KM * 1000:
        return None
    if altitude_m > nearest_airport["altitude_m"] + AIRPORT_MAX_ALTITUDE_M:
        return None

    return nearest_airport["_id"]


def determine_status(ground_speed_mps):
    # just uses ground speed to determine status
    return "flying" if ground_speed_mps > 50 else "ground"


def update_all_locations(app):
    # get all aircraft once to start periodic updates
    print("updating all locations")
    aircraft_list = app.database.aircraft.find()
    for aircraft in aircraft_list:
        app.scheduler.add_job(
            update_location,
            "date",
            [app, aircraft["_id"]],
            run_date=datetime.now(),
        )


def update_location(app, aircraft_id):
    def schedule_next(minutes):
        next_update = datetime.now() + timedelta(minutes=minutes)
        app.scheduler.add_job(
            update_location,
            "date",
            [app, aircraft_id],
            run_date=next_update,
        )

    print(f"updating location for aircraft {aircraft_id}")
    aircraft = app.database.aircraft.find_one({"_id": aircraft_id})
    last_location = app.database.location.find_one(
        {"aircraft_id": aircraft_id}, sort=[("timestamp", -1)]
    )
    last_location_timestamp = last_location["timestamp"] if last_location else None

    # get location from ADS-B Exchange
    response = requests.get(
        f"https://{app.config['ADSB_HOST']}/v2/reg/{aircraft['registration']}",
    )
    if response.status_code != 200:
        print(f"HTTP Error: {response.status_code}")
        return

    data = response.json()

    if len(data["ac"]) == 0:
        print(f"no location data for aircraft {aircraft_id}")
        schedule_next(DELAY_NO_LOCATION_MIN)
        return

    try:
        # get location from response
        location_timestamp = data["now"] - (last_pos["seen_pos"] * 1000)

        # if the location timestamp is within 1 second, skip it
        if last_location_timestamp and abs(location_timestamp - last_location_timestamp) < 1000:
            print(f"duplicate location found for aircraft {aircraft_id}")
            schedule_next(DELAY_FOUND_LOCATION_MIN)
            return

        ac = data["ac"][0]
        last_pos = ac["lastPosition"]
        latitude = last_pos["lat"]
        longitude = last_pos["lon"]
        altitude_m = ft_to_m(ac["alt_baro"]) if ac["alt_baro"] != "ground" else 0
        heading_deg = ac["true_heading"] if "true_heading" in ac else ac["track"]
        ground_speed_m_s = kts_to_mps(ac["gs"])

        # get status and airport
        status = determine_status(ground_speed_m_s)
        airport = (
            determine_nearest_airport(app, latitude, longitude, altitude_m)
            if status == "ground"
            else None
        )

        location = Location(
            aircraft_id=aircraft_id,
            latitude=latitude,
            longitude=longitude,
            altitude_m=altitude_m,
            heading_deg=heading_deg,
            ground_speed_mps=ground_speed_m_s,
            status=status,
            airport_id=airport,
            timestamp=location_timestamp,
        )
        app.database.location.insert_one(location.model_dump())

    except Exception as e:
        print(f"error updating location for aircraft {aircraft_id}: {e}")

    # schedule next update
    schedule_next(DELAY_FOUND_LOCATION_MIN)

    # if it's on the ground, we should also update the trip
    if status == "ground":
        app.scheduler.add_job(
            update_trip,
            "date",
            [app, aircraft_id],
            run_date=datetime.now(),
        )
