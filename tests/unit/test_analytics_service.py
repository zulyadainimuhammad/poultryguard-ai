from datetime import date

from app.database import (
    DailyRecord,
    DailyRecordRepository,
    Farm,
    FarmRepository,
    Flock,
    FlockRepository,
    initialise_database,
)
from app.services.analytics_service import AnalyticsService


def create_test_farm() -> int:
    repository = FarmRepository()

    farm = Farm(
        farm_name="Analytics Test Farm",
        farmer_name="Test Farmer",
        location="Kano, Nigeria",
        production_type="Broiler",
    )

    return repository.create(farm)


def create_test_flock(farm_id: int) -> int:
    repository = FlockRepository()

    flock = Flock(
        farm_id=farm_id,
        flock_name="Analytics Test Batch",
        species="Chicken",
        production_type="Broiler",
        breed="Cobb 500",
        initial_count=500,
        stocking_date="2026-11-01",
        status="active",
    )

    return repository.create(flock)


def create_daily_records(flock_id: int) -> None:
    repository = DailyRecordRepository()

    records = [
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            feed_kg=30.0,
            water_litres=60.0,
            mortality=2,
            average_weight_kg=0.50,
            temperature_c=28.0,
            humidity_percent=65.0,
            notes="First test record.",
        ),
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-02",
            feed_kg=32.0,
            water_litres=64.0,
            mortality=1,
            average_weight_kg=0.60,
            temperature_c=29.0,
            humidity_percent=66.0,
            notes="Second test record.",
        ),
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-03",
            feed_kg=35.0,
            water_litres=70.0,
            mortality=3,
            average_weight_kg=0.70,
            temperature_c=28.5,
            humidity_percent=67.0,
            notes="Third test record.",
        ),
    ]

    for record in records:
        repository.create(record)


def test_flock_summary() -> None:
    initialise_database()

    farm_id = create_test_farm()
    flock_id = create_test_flock(farm_id)
    create_daily_records(flock_id)

    service = AnalyticsService()

    summary = service.get_flock_summary(flock_id)

    assert summary["initial_count"] == 500
    assert summary["current_flock_size"] == 494.0
    assert summary["total_mortality"] == 6.0
    assert summary["mortality_rate_percent"] == 1.2

    assert summary["total_feed_kg"] == 97.0
    assert summary["total_water_litres"] == 194.0

    assert summary["average_weight_kg"] == 0.6
    assert summary["average_temperature_c"] == 28.5
    assert summary["average_humidity_percent"] == 66.0

    assert summary["record_count"] == 3


def test_daily_metrics() -> None:
    initialise_database()

    farm_id = create_test_farm()
    flock_id = create_test_flock(farm_id)
    create_daily_records(flock_id)

    service = AnalyticsService()

    metrics = service.get_daily_metrics(flock_id)

    assert len(metrics) == 3

    # Repository returns records in descending date order.
    first = metrics[0]
    second = metrics[1]
    third = metrics[2]

    assert first["record_date"] == "2026-11-03"
    assert first["mortality"] == 3.0
    assert first["cumulative_mortality"] == 3.0
    assert first["current_flock_size"] == 497.0

    assert second["record_date"] == "2026-11-02"
    assert second["mortality"] == 1.0
    assert second["cumulative_mortality"] == 4.0
    assert second["current_flock_size"] == 496.0

    assert third["record_date"] == "2026-11-01"
    assert third["mortality"] == 2.0
    assert third["cumulative_mortality"] == 6.0
    assert third["current_flock_size"] == 494.0


def test_metrics_by_date_range() -> None:
    initialise_database()

    farm_id = create_test_farm()
    flock_id = create_test_flock(farm_id)
    create_daily_records(flock_id)

    service = AnalyticsService()

    metrics = service.get_metrics_by_date_range(
        flock_id=flock_id,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
    )

    assert len(metrics) == 2

    assert metrics[0]["record_date"] == "2026-11-02"
    assert metrics[0]["mortality"] == 1.0

    assert metrics[1]["record_date"] == "2026-11-03"
    assert metrics[1]["mortality"] == 3.0


def test_missing_flock_raises_error() -> None:
    initialise_database()

    service = AnalyticsService()

    try:
        service.get_flock_summary(999999)
        assert False, "Expected ValueError for missing flock."
    except ValueError as error:
        assert "was not found" in str(error)


def test_empty_flock_records() -> None:
    initialise_database()

    farm_id = create_test_farm()
    flock_id = create_test_flock(farm_id)

    service = AnalyticsService()

    summary = service.get_flock_summary(flock_id)

    assert summary["initial_count"] == 500
    assert summary["current_flock_size"] == 500
    assert summary["total_mortality"] == 0.0
    assert summary["mortality_rate_percent"] == 0.0
    assert summary["total_feed_kg"] == 0.0
    assert summary["total_water_litres"] == 0.0
    assert summary["average_weight_kg"] is None
    assert summary["average_temperature_c"] is None
    assert summary["average_humidity_percent"] is None
    assert summary["record_count"] == 0