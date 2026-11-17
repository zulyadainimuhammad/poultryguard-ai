from dataclasses import dataclass


@dataclass
class Farm:
    farm_name: str
    farmer_name: str
    location: str | None = None
    phone: str | None = None
    email: str | None = None
    production_type: str | None = None


@dataclass
class Flock:
    farm_id: int
    flock_name: str
    species: str
    production_type: str | None = None
    breed: str | None = None
    initial_count: int = 0
    stocking_date: str | None = None
    status: str = "active"


@dataclass
class DailyRecord:
    flock_id: int
    record_date: str
    feed_kg: float | None = None
    water_litres: float | None = None
    mortality: int = 0
    average_weight_kg: float | None = None
    temperature_c: float | None = None
    humidity_percent: float | None = None
    notes: str | None = None