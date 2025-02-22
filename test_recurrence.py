from src.nlp.processor import NLPProcessor
from dotenv import load_dotenv
import json
load_dotenv()

def test_recurrence_patterns():
    nlp = NLPProcessor()
    
    # Test cases for complex recurrence patterns
    commands = [
        "Schedule team standup every other Tuesday at 10am",
        "Set up monthly budget review on the first Monday of each month at 2pm",
        "Schedule daily scrum at 9am on weekdays",
        "Create team workout sessions every Monday and Wednesday at 5pm for the next 10 weeks",
        "Schedule monthly team lunch on the 15th until the end of the year",
        "Set up weekly project sync every Monday at 11am except on holidays"
    ]
    
    for command in commands:
        print("\nCommand:", command)
        result = nlp.parse_command(command)
        print("\nParsed Result:")
        print(json.dumps(result, indent=2))
        print("\nNatural Summary:")
        print(nlp.get_event_summary(result))
        print("\n" + "="*50)

if __name__ == "__main__":
    test_recurrence_patterns()
