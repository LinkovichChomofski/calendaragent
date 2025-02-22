from src.integrations.google_calendar import GoogleCalendarClient
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()

def test_calendar_operations():
    print("Starting calendar operations test...")
    client = GoogleCalendarClient()
    
    # Create test event
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=1)
    
    test_event = {
        'summary': 'Test Event - Calendar Agent',
        'description': 'This is a test event created by Calendar Agent',
        'start': {
            'dateTime': start_time.isoformat() + 'Z',
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_time.isoformat() + 'Z',
            'timeZone': 'UTC',
        }
    }
    
    print("\nCreating test event...")
    created_event = client.create_event('primary', test_event)
    print(f"Created event: {created_event.get('summary')} at {created_event.get('start', {}).get('dateTime')}")
    
    print("\nUpdating event description...")
    updated_event = created_event.copy()
    updated_event['description'] = 'Updated: This event was modified by Calendar Agent'
    updated = client.update_event('primary', created_event['id'], updated_event)
    print(f"Updated event description: {updated.get('description')}")
    
    input("\nPress Enter to delete the test event...")
    
    print("Deleting test event...")
    client.delete_event('primary', created_event['id'])
    print("Test event deleted successfully!")

if __name__ == '__main__':
    test_calendar_operations()
