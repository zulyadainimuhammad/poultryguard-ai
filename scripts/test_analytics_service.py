from app.database import initialise_database
from app.services.analytics_service import AnalyticsService


def main() -> None:
    initialise_database()

    service = AnalyticsService()

    # Flock ID 3 was created during the FarmService test.
    flock_id = 3

    summary = service.get_flock_summary(flock_id)

    print("\n=== FLOCK SUMMARY ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    daily_metrics = service.get_daily_metrics(flock_id)

    print("\n=== DAILY METRICS ===")
    for record in daily_metrics:
        print(record)


if __name__ == "__main__":
    main()