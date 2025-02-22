from src.nlp.processor import NLPProcessor
from dotenv import load_dotenv
import json
load_dotenv()

def test_nlp():
    nlp = NLPProcessor()
    
    # Test cases
    commands = [
        "Schedule a weekly team standup meeting with John and Sarah every Tuesday at 10am in the conference room",
        "Cancel my meeting with John tomorrow",
        "Show me all my meetings for next week",
        "Schedule lunch with Sarah at 12:30pm today at Cafe Luna"
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
    test_nlp()
