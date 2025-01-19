def update_trip(app, aircraft_id):
    # get the unprocessed locations for this aircraft
    locations = app.db.location.find({"aircraft_id": aircraft_id, "processed": False})

    if not locations or len(locations) < 5:
        # not enough locations
        return
    
    state = "reset"
    previous_location = None

    origin_location_id = None
    destination_location_id = None
    timestamp = None

    for location in locations:
        if state == "reset":
            # make sure aircraft is on the ground
            if not location["status"] == "ground":
                print(f"aircraft {aircraft_id} did not start on the ground")
                break
            state = "to_depart"

        elif state == "to_depart":
            # check if the aircraft has departed
            if location["status"] == "flying":
                origin_location_id = previous_location["_id"]
                timestamp = previous_location["timestamp"]
                state = "in_flight"

        elif state == "in_flight":
            # check if the aircraft has landed
            if location["status"] == "ground":
                destination_location_id = location["_id"]
                state = "landed"

        previous_location = location

    if origin_location_id is None or destination_location_id is None:
        print(f"invalid flight for aircraft {aircraft_id}")
        return
    
    # add the trip
    app.db.trip.insert_one({
        "aircraft_id": aircraft_id,
        "origin_location_id": origin_location_id,
        "destination_location_id": destination_location_id,
        "timestamp": timestamp,
    })

    # mark the locations as processed
    app.db.location.update_many({"aircraft_id": aircraft_id, "processed": False}, {"$set": {"processed": True}})
