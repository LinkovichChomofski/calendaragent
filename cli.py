#!/usr/bin/env python3
from src.nlp.processor import NLPProcessor
from src.integrations.google_calendar import GoogleCalendarClient
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import os

def format_parsed_result(result):
    """Format the NLP parsing result for display"""
    output = []
    output.append(f"\nIntent: {result['intent']}")
    
    if result['entities']['title']:
        output.append(f"Title: {result['entities']['title']}")
    
    if result['temporal']['start_time']:
        output.append(f"Start Time: {result['temporal']['start_time']}")
    if result['temporal']['end_time']:
        output.append(f"End Time: {result['temporal']['end_time']}")
    if result['temporal']['duration']:
        output.append(f"Duration: {result['temporal']['duration']}")
        
    if result['entities']['participants']:
        output.append(f"Participants: {', '.join(result['entities']['participants'])}")
    if result['entities']['location']:
        output.append(f"Location: {', '.join(result['entities']['location'])}")
        
    if result['recurrence']:
        output.append(f"Recurrence: {result['recurrence']['frequency']}")
        if 'days' in result['recurrence']:
            output.append(f"On days: {', '.join(result['recurrence']['days'])}")
            
    return '\n'.join(output)

def main():
    load_dotenv()
    
    # Initialize processors
    nlp = NLPProcessor()
    calendar = GoogleCalendarClient()
    
    print("\nWelcome to Calendar Agent!")
    print("Enter your commands in natural language.")
    print("Examples:")
    print("- Schedule a meeting with John tomorrow at 2pm")
    print("- Show me my meetings for next week")
    print("- Cancel my 3pm meeting")
    print("- Schedule weekly team standup every Monday at 10am")
    print("\nType 'quit' to exit.")
    
    while True:
        try:
            command = input("\nWhat would you like to do? ").strip()
            
            if command.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye!")
                break
                
            # Parse the command
            result = nlp.parse_command(command)
            
            # Show parsed understanding
            print(format_parsed_result(result))
            
            # TODO: Implement calendar operations based on parsed intent
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
