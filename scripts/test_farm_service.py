from datetime import date

from app.database import initialise_database
from app.services.farm_service import FarmService


def main() -> None:
    initialise_database()

    service = FarmService()

    farm_id = service.create_farm(
        farm_name="TechGrow Demo Farm",
        farmer_name="Demo Farmer",
        location="Kano, Nigeria",
        production_type="Broiler",
    )

    flock_id = service.create_flock(
        farm_id=farm_id,
        flock_name="Broiler Batch 001",
        species="Chicken",
        production_type="Broiler",
        breed="Cobb 500",
        initial_count=500,
        stocking_date=date.today(),
    )

    record_id = service.create_daily_record(
        flock_id=flock_id,
        record_date=date.today(),
        feed_kg=35.5,
        water_litres=70.0,
        mortality=2,
        average_weight_kg=0.65,
        temperature_c=28.5,
        humidity_percent=67.0,
        notes="Normal feeding activity.",
    )

    print(f"Farm created through service: {farm_id}")
    print(f"Flock created through service: {flock_id}")
    print(f"Daily record created through service: {record_id}")

    print("\nFarm:")
    print(service.get_farm(farm_id))

    print("\nFlock:")
    print(service.get_flock(flock_id))

    print("\nDaily records:")
    print(service.get_daily_records(flock_id))


if __name__ == "__main__":
    main()