from src.services.holiday_service import HolidayService
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def test_holiday_service():
    service = HolidayService()
    tz = ZoneInfo('America/Los_Angeles')
    
    # Test dates
    christmas_2025 = datetime(2025, 12, 25, tzinfo=tz)
    black_friday_2025 = datetime(2025, 11, 28, tzinfo=tz)
    regular_day = datetime(2025, 3, 12, tzinfo=tz)  # Regular Wednesday
    
    print("\nTesting Holiday Detection:")
    print(f"Is Christmas 2025 a holiday? {service.is_holiday(christmas_2025)}")
    print(f"Holiday name: {service.get_holiday_name(christmas_2025)}")
    
    print(f"\nIs Black Friday 2025 a holiday? {service.is_holiday(black_friday_2025)}")
    print(f"Holiday name: {service.get_holiday_name(black_friday_2025)}")
    
    print(f"\nIs March 12, 2025 a holiday? {service.is_holiday(regular_day)}")
    print(f"Holiday name: {service.get_holiday_name(regular_day)}")
    
    # Test holiday range
    print("\nHolidays in December 2025:")
    start = datetime(2025, 12, 1, tzinfo=tz)
    end = datetime(2025, 12, 31, tzinfo=tz)
    december_holidays = service.get_holidays_between(start, end)
    for date, name in december_holidays.items():
        print(f"- {date}: {name}")
    
    # Test business day logic
    print("\nBusiness Day Tests:")
    print(f"Is Christmas 2025 a business day? {service.is_business_day(christmas_2025)}")
    print(f"Next business day after Christmas 2025: {service.get_next_business_day(christmas_2025).strftime('%Y-%m-%d')}")
    
    # Test upcoming holidays
    print("\nUpcoming Holidays (next 30 days):")
    today = datetime.now(tz)
    next_month = today + timedelta(days=30)
    upcoming = service.get_holidays_between(today, next_month)
    for date, name in upcoming.items():
        print(f"- {date}: {name}")

if __name__ == "__main__":
    test_holiday_service()
