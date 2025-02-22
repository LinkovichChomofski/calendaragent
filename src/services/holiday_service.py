from typing import List, Optional, Dict
from datetime import datetime, date, timedelta
import holidays
from zoneinfo import ZoneInfo

class HolidayService:
    """Service for handling holiday detection and validation"""
    
    def __init__(self):
        self.timezone = ZoneInfo('America/Los_Angeles')
        self._init_holiday_calendars()
        
    def _init_holiday_calendars(self):
        """Initialize holiday calendars"""
        # US Federal holidays
        self.us_holidays = holidays.US()
        
        # Add custom observances
        self.custom_holidays = {
            # Add common observances that aren't federal holidays
            "Valentine's Day": [(2, 14)],
            "Halloween": [(10, 31)],
            "Black Friday": self._calculate_black_friday,
            "Cyber Monday": self._calculate_cyber_monday,
            "Christmas Eve": [(12, 24)],
            "New Year's Eve": [(12, 31)]
        }
    
    def is_holiday(self, check_date: datetime) -> bool:
        """Check if a given date is a holiday"""
        date_obj = check_date.date() if isinstance(check_date, datetime) else check_date
        
        # Check federal holidays
        if date_obj in self.us_holidays:
            return True
            
        # Check custom holidays
        for holiday_dates in self.custom_holidays.values():
            if callable(holiday_dates):
                if holiday_dates(date_obj.year) == date_obj:
                    return True
            else:
                for month, day in holiday_dates:
                    if date_obj.month == month and date_obj.day == day:
                        return True
        
        return False
    
    def get_holiday_name(self, check_date: datetime) -> Optional[str]:
        """Get the name of the holiday for a given date"""
        date_obj = check_date.date() if isinstance(check_date, datetime) else check_date
        
        # Check federal holidays
        if date_obj in self.us_holidays:
            return self.us_holidays.get(date_obj)
            
        # Check custom holidays
        for name, holiday_dates in self.custom_holidays.items():
            if callable(holiday_dates):
                if holiday_dates(date_obj.year) == date_obj:
                    return name
            else:
                for month, day in holiday_dates:
                    if date_obj.month == month and date_obj.day == day:
                        return name
        
        return None
    
    def get_holidays_between(self, start_date: datetime, end_date: datetime) -> Dict[date, str]:
        """Get all holidays between two dates"""
        holidays_dict = {}
        current = start_date
        
        while current <= end_date:
            if self.is_holiday(current):
                holidays_dict[current.date()] = self.get_holiday_name(current)
            current = current + timedelta(days=1)
            
        return holidays_dict
    
    def _calculate_black_friday(self, year: int) -> date:
        """Calculate Black Friday for a given year (day after Thanksgiving)"""
        # Get Thanksgiving (4th Thursday of November)
        thanksgiving = datetime.strptime(f'{year}-11-01', '%Y-%m-%d')
        while thanksgiving.weekday() != 3:  # 3 is Thursday
            thanksgiving = thanksgiving + timedelta(days=1)
        thanksgiving = thanksgiving + timedelta(weeks=3)  # Move to 4th Thursday
        
        # Black Friday is the next day
        return thanksgiving.date() + timedelta(days=1)
    
    def _calculate_cyber_monday(self, year: int) -> date:
        """Calculate Cyber Monday for a given year (Monday after Thanksgiving)"""
        # Get Black Friday first
        black_friday = self._calculate_black_friday(year)
        # Cyber Monday is 3 days after Black Friday
        return black_friday + timedelta(days=3)
    
    def get_next_business_day(self, start_date: datetime) -> datetime:
        """Get the next business day after start_date"""
        next_day = start_date + timedelta(days=1)
        while self.is_holiday(next_day) or next_day.weekday() >= 5:  # 5 is Saturday
            next_day = next_day + timedelta(days=1)
        return next_day
    
    def is_business_day(self, check_date: datetime) -> bool:
        """Check if a given date is a business day"""
        return not (self.is_holiday(check_date) or check_date.weekday() >= 5)
