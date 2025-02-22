from src.nlp.processor import NLPProcessor
from dotenv import load_dotenv
import json
from datetime import datetime
from zoneinfo import ZoneInfo

def test_recurrence_with_holidays():
    load_dotenv()
    nlp = NLPProcessor()
    
    # Test cases for recurrence with holiday handling
    commands = [
        "Schedule weekly team meeting every Tuesday at 10am except holidays",
        "Set up daily standup at 9am on business days",
        "Create monthly review on the first Monday of each month at 2pm unless it's a holiday",
        "Schedule team lunch every Friday at noon except on holidays and weekends"
    ]
    
    for command in commands:
        print("\nCommand:", command)
        result = nlp.parse_command(command)
        
        # Show parsed result
        print("\nParsed Result:")
        print(json.dumps(result, indent=2))
        
        # Show natural summary
        print("\nNatural Summary:")
        print(nlp.get_event_summary(result))
        
        # Show next occurrence
        if result["temporal"]["start_time"]:
            start_time = datetime.fromisoformat(result["temporal"]["start_time"])
            print(f"\nFirst occurrence: {start_time.strftime('%A, %B %d, %Y at %I:%M %p')}")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    test_recurrence_with_holidays()
