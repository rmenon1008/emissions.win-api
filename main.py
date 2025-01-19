from contextlib import asynccontextmanager
from datetime import datetime

import dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from pymongo import MongoClient

from setup import setup_collections
from update_location import update_all_locations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup scheduler and database
    app.config = dotenv.dotenv_values(".env")
    app.scheduler = BackgroundScheduler()
    app.scheduler.start()
    app.mongodb_client = MongoClient(
        app.config["DB_URI"], uuidRepresentation="standard"
    )
    app.database = app.mongodb_client[app.config["DB_NAME"]]

    # First run initialization
    if app.config["FIRST_RUN"] == "true":
        setup_collections(app)
        dotenv.set_key(".env", "FIRST_RUN", "false")

    # Schedule initial location updates for now
    # After this, they schedule themselves
    # Location updates also schedule trip updates
    app.scheduler.add_job(update_all_locations, "date", [app], run_date=datetime.now())

    # Yield to main loop
    yield

    # Shutdown
    app.mongodb_client.close()
    app.scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
