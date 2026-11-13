from dataclasses import dataclass
from typing import Optional


@dataclass
class Farm:
    farm_name: str
    farmer_name: str
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    production_type: Optional[str] = None


@dataclass
class Flock:
    farm_id: int
    flock_name: str
    species: str
    production_type: Optional[str] = None
    breed: Optional[str] = None
    initial_count: int = 0
    stocking_date: Optional[str] = None
    status: str = "active"


@dataclass
class DailyRecord:
    flock_id: int
    record_date: str
    feed_kg: Optional[float] = None
    water_litres: Optional[float] = None
    mortality: int = 0
    average_weight_kg: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    notes: Optional[str] = None