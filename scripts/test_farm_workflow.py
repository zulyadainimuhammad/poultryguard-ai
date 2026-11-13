from app.database import (
    DailyRecord,
    DailyRecordRepository,
    Farm,
    FarmRepository,
    Flock,
    FlockRepository,
    initialise_database,
)


def main():
    # Make sure the database exists.
    initialise_database()

    farm_repo = FarmRepository()
    flock_repo = FlockRepository()
    record_repo = DailyRecordRepository()

    # 1. Create a farm
    farm_id = farm_repo.create(
        Farm(
            farm_name="TechGrow Demonstration Poultry Farm",
            farmer_name="Demo Farmer",
            location="Kano, Nigeria",
            production_type="Broiler",
        )
    )

    print(f"Farm created: {farm_id}")

    # 2. Create a flock
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Broiler Batch 001",
            species="Chicken",
            production_type="Broiler",
            breed="Cobb 500",
            initial_count=500,
            stocking_date="2026-11-10",
        )
    )

    print(f"Flock created: {flock_id}")

    # 3. Add a daily farm record
    record_id = record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-10",
            feed_kg=35.5,
            water_litres=70.0,
            mortality=2,
            average_weight_kg=0.65,
            temperature_c=28.5,
            humidity_percent=67.0,
            notes="Normal feeding activity.",
        )
    )

    print(f"Daily record created: {record_id}")

    # 4. Retrieve the farm
    farm = farm_repo.get_by_id(farm_id)

    print("\nFarm:")
    print(farm)

    # 5. Retrieve the flock
    flock = flock_repo.get_by_id(flock_id)

    print("\nFlock:")
    print(flock)

    # 6. Retrieve daily records
    records = record_repo.get_by_flock(flock_id)

    print("\nDaily records:")

    for record in records:
        print(record)


if __name__ == "__main__":
    main()