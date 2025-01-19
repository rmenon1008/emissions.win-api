import datetime
from typing import List, Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class MongoBaseModel(BaseModel):
    """Base model that configures MongoDB field mapping"""

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class Person(MongoBaseModel):
    name: str = Field(...)
    image_url: str = Field(...)
    description: str = Field(...)
    about_url: str = Field(...)
    aircraft_ids: List[ObjectId] = Field(default_factory=list)


class Aircraft(MongoBaseModel):
    registration: str = Field(...)
    name: str = Field(...)
    engine_count: int = Field(...)
    engine_id: ObjectId = Field(...)


class Engine(MongoBaseModel):
    model: str = Field(...)
    full_lto_kg: float = Field(...)
    cruise_kg_s: float = Field(...)


class Airport(MongoBaseModel):
    name: str = Field(...)
    icao: str = Field(...)
    latitude: float = Field(...)
    longitude: float = Field(...)
    altitude_m: float = Field(...)


class Location(MongoBaseModel):
    aircraft_id: ObjectId = Field(...)
    latitude: float = Field(...)
    longitude: float = Field(...)
    altitude_m: float = Field(...)
    heading_deg: float = Field(...)
    ground_speed_mps: float = Field(...)
    status: Literal["ground", "flying"] = Field(...)
    airport_id: Optional[ObjectId] = Field(default=None)
    timestamp: datetime.datetime = Field(...)


class Trip(MongoBaseModel):
    aircraft_id: ObjectId = Field(...)
    origin_location_id: ObjectId = Field(...)
    destination_location_id: ObjectId = Field(...)
    timestamp: datetime.datetime = Field(...)
