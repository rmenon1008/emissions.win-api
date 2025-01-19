import json

from models import Aircraft, Airport, Engine, Person
from utils import ft_to_m


def setup_collections(app):
    # Create collections
    print("creating collections")
    collection_names = [
        "airports",
        "engines",
        "people",
        "aircraft",
        "locations",
        "trips",
    ]
    existing_collections = app.database.list_collection_names()
    for name in collection_names:
        if name in existing_collections:
            app.database.drop_collection(name)
        app.database.create_collection(name)

    # Populate airports
    print("populating airports")
    with open(f"{app.config['SETUP_DIR']}/airports.json", "r") as f:
        data = json.load(f).values()
        entries = (
            Airport(
                name=collection["name"],
                icao=collection["icao"],
                latitude=collection["lat"],
                longitude=collection["lon"],
                altitude_m=ft_to_m(collection["elevation"]),
            ).model_dump()
            for collection in data
        )
        app.database.airports.insert_many(entries)  # Batch insert

    # Populate engines
    print("populating engines")
    with open(f"{app.config['SETUP_DIR']}/engines.json", "r") as f:
        data = json.load(f)
        entries = (
            Engine(
                model=engine["model"],
                full_lto_kg=engine["full_lto_kg"],
                cruise_kg_s=engine["cruise_kg_s"],
            ).model_dump()
            for engine in data
        )
        app.database.engines.insert_many(entries)

    # Populate aircraft
    print("populating aircraft")
    with open(f"{app.config['SETUP_DIR']}/aircraft.json", "r") as f:
        data = json.load(f)
        entries = (
            Aircraft(
                registration=aircraft["registration"],
                name=aircraft["name"],
                engine_count=aircraft["engine_count"],
                engine_id=app.database.engines.find_one(
                    {"model": aircraft["engine_model"]}
                )["_id"],
            ).model_dump()
            for aircraft in data
        )
        app.database.aircraft.insert_many(entries)

    # Populate people
    print("populating people")
    with open(f"{app.config['SETUP_DIR']}/people.json", "r") as f:
        data = json.load(f)
        entries = (
            Person(
                name=person["name"],
                image_url=person["image_url"],
                description=person["description"],
                about_url=person["about_url"],
                aircraft_ids=[
                    app.database.aircraft.find_one({"registration": registration})[
                        "_id"
                    ]
                    for registration in person["aircraft_registrations"]
                ],
            ).model_dump()
            for person in data
        )
        app.database.people.insert_many(entries)

    print("setup complete")
