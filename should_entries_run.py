from datetime import datetime
import sys


def should_run_for_day_of_year(day_of_year: int) -> bool:
    return day_of_year % 3 == 0


def main() -> int:
    day_of_year = datetime.now().timetuple().tm_yday
    if should_run_for_day_of_year(day_of_year):
        print(f"Entries automation allowed for day {day_of_year}.")
        return 0

    print(f"Entries automation skipped for day {day_of_year}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
