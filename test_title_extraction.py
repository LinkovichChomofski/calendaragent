from src.nlp.processor import NLPProcessor
from dotenv import load_dotenv
import json
load_dotenv()

def test_title_extraction():
    nlp = NLPProcessor()
    
    # Test cases for title extraction
    commands = [
        "Schedule project kickoff meeting with the design team tomorrow at 2pm",
        "Set up a quick sync with marketing about Q1 campaign next Monday",
        "Book a dentist appointment for teeth cleaning next week",
        "Schedule weekly team standup every Tuesday at 10am",
        "Lunch with Sarah at Cafe Luna tomorrow at noon",
        "Set up 1:1 with John to discuss performance review",
        "Create sprint planning meeting for next release",
        "Schedule quarterly business review with leadership team",
        "Book conference room for brainstorming session with product team",
        "Set reminder for gym class at 5pm"
    ]
    
    for command in commands:
        print("\nCommand:", command)
        result = nlp.parse_command(command)
        
        # Show event details
        print("\nEvent Details:")
        print(f"Title: {result['entities']['title']}")
        print(f"Type: {result['entities']['type']}")
        print(f"Category: {result['entities']['category']}")
        print(f"Description: {result['entities']['description']}")
        
        # Show natural summary
        print("\nNatural Summary:")
        print(nlp.get_event_summary(result))
        print("\n" + "="*50)

if __name__ == "__main__":
    test_title_extraction()
