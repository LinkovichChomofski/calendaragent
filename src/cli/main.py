import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo
import os

from ..config.manager import ConfigManager
from ..services.calendar_sync_service import CalendarSyncService
from ..database.connection import DatabaseManager
from ..nlp.processor import NLPProcessor
from ..services.holiday_service import HolidayService

console = Console()
config_manager = ConfigManager()

# Command completion
COMMANDS = [
    "schedule", "cancel", "update", "show", "sync", "list",
    "today", "tomorrow", "next week", "with", "at", "every",
    "meeting", "lunch", "call", "appointment"
]

def get_session():
    """Get prompt session with command completion"""
    completer = WordCompleter(COMMANDS, ignore_case=True)
    return PromptSession(completer=completer)

def check_configuration():
    """Check and validate configuration"""
    if not config_manager.validate():
        if click.confirm("Would you like to run the setup wizard?", default=True):
            config_manager.setup_wizard()
            config_manager.load_config()
            if not config_manager.validate():
                return False
        else:
            return False
    return True

def init_services():
    """Initialize services"""
    try:
        # Ensure required directories exist
        config_manager.ensure_directories()
        
        # Initialize services with configuration
        db = DatabaseManager(config_manager.get('app.database_path'))
        sync_service = CalendarSyncService(db)
        nlp = NLPProcessor(config_manager)
        
        # Only initialize holiday service if enabled
        holiday_service = None
        if config_manager.get('features.holiday_calendar'):
            holiday_service = HolidayService()
            
        return db, sync_service, nlp, holiday_service
    except Exception as e:
        console.print(f"[bold red]Error initializing services: {str(e)}[/bold red]")
        return None, None, None, None

@click.group()
@click.option('--config', '-c', help='Path to config file')
def cli(config):
    """Calendar Agent - Your AI-powered calendar assistant"""
    if config:
        global config_manager
        config_manager = ConfigManager(config)

@cli.command()
def setup():
    """Run the setup wizard"""
    config_manager.setup_wizard()
    console.print("\nTo start using Calendar Agent, try: calendaragent.py chat -i")

@cli.command()
@click.option('--interactive', '-i', is_flag=True, help='Start interactive mode')
def chat(interactive):
    """Chat with your calendar assistant"""
    if not check_configuration():
        return
        
    db, sync_service, nlp, holiday_service = init_services()
    if not all([db, sync_service, nlp]):  # holiday_service is optional
        return
        
    session = get_session()
    
    if interactive:
        console.print(Panel.fit(
            "🗓️  [bold blue]Calendar Agent[/bold blue] - Your AI Calendar Assistant\n"
            "Type 'help' for available commands or 'exit' to quit",
            title="Welcome"
        ))
        
        while True:
            try:
                command = session.prompt("\n[bold blue]Calendar>[/bold blue] ")
                
                if command.lower() in ['exit', 'quit']:
                    break
                elif command.lower() == 'help':
                    show_help()
                else:
                    process_command(command, db, sync_service, nlp)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
    else:
        # Single command mode
        command = click.prompt("How can I help you with your calendar?")
        process_command(command, db, sync_service, nlp)

@cli.command()
@click.argument('calendar_id', default='primary')
@click.option('--days', '-d', default=None, help='Number of days to sync')
def sync(calendar_id, days):
    """Sync your calendar"""
    if not check_configuration():
        return
        
    db, sync_service, _, _ = init_services()
    if not all([db, sync_service]):
        return
        
    # Use configured sync interval if not specified
    if days is None:
        days = config_manager.get('app.sync_interval')
        
    with Progress() as progress:
        task = progress.add_task("[cyan]Syncing calendar...", total=100)
        
        stats = sync_service.sync_calendar(calendar_id, days_to_sync=days)
        progress.update(task, advance=100)
    
    console.print("\n[bold green]Sync Complete![/bold green]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim")
    table.add_column("Count")
    
    table.add_row("New Events", str(stats['new_events']))
    table.add_row("Updated Events", str(stats['updated_events']))
    table.add_row("Deleted Events", str(stats['deleted_events']))
    
    console.print(table)
    
    if stats['errors']:
        console.print("\n[bold red]Errors:[/bold red]")
        for error in stats['errors']:
            console.print(f"- {error}")

@cli.command()
@click.argument('timeframe', default='today')
def show(timeframe):
    """Show calendar events"""
    if not check_configuration():
        return
        
    db, sync_service, _, _ = init_services()
    if not all([db, sync_service]):
        return
        
    tz = ZoneInfo('America/Los_Angeles')
    now = datetime.now(tz)
    
    if timeframe == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif timeframe == 'tomorrow':
        start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif timeframe == 'week':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
    else:
        console.print("[red]Invalid timeframe. Use 'today', 'tomorrow', or 'week'[/red]")
        return
    
    with db.get_session() as session:
        events = sync_service.get_events_between(session, start, end)
        
        if not events:
            console.print(f"[yellow]No events found for {timeframe}[/yellow]")
            return
            
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="dim")
        table.add_column("Event")
        table.add_column("Type")
        table.add_column("Location", style="dim")
        
        for event in events:
            start_time = event.start_time.strftime("%I:%M %p")
            table.add_row(
                start_time,
                event.title,
                event.event_type,
                event.location or ""
            )
            
        console.print(table)

def process_command(command: str, db, sync_service, nlp):
    """Process a natural language command"""
    try:
        # Parse command using NLP
        parsed = nlp.parse_command(command)
        
        if not parsed:
            console.print("[red]Sorry, I couldn't understand that command.[/red]")
            return
            
        intent = parsed['intent'].upper()
        
        if intent == 'SCHEDULE':
            schedule_event(parsed, db, sync_service)
        elif intent == 'CANCEL':
            cancel_event(parsed, db, sync_service)
        elif intent == 'UPDATE':
            update_event(parsed, db, sync_service)
        elif intent == 'QUERY':
            show_events(parsed, db, sync_service)
        else:
            console.print("[red]Unknown command type.[/red]")
            
    except Exception as e:
        console.print(f"[red]Error processing command: {str(e)}[/red]")

def schedule_event(parsed: dict, db, sync_service):
    """Schedule a new event"""
    with db.get_session() as session:
        event = sync_service.create_event(session, parsed)
        
        if event:
            console.print(f"\n[green]✓[/green] Scheduled: [bold]{event.title}[/bold]")
            console.print(f"   📅 {event.start_time.strftime('%A, %B %d at %I:%M %p')}")
            if event.location:
                console.print(f"   📍 {event.location}")
            if event.participants:
                console.print("   👥 With: " + ", ".join(p.name for p in event.participants))
        else:
            console.print("[red]Failed to schedule event[/red]")

def cancel_event(parsed: dict, db, sync_service):
    """Cancel an event"""
    with db.get_session() as session:
        if sync_service.cancel_event(session, parsed):
            console.print("[green]Event cancelled successfully[/green]")
        else:
            console.print("[red]Failed to cancel event[/red]")

def update_event(parsed: dict, db, sync_service):
    """Update an event"""
    with db.get_session() as session:
        if sync_service.update_event(session, parsed):
            console.print("[green]Event updated successfully[/green]")
        else:
            console.print("[red]Failed to update event[/red]")

def show_events(parsed: dict, db, sync_service):
    """Show events based on query"""
    with db.get_session() as session:
        events = sync_service.query_events(session, parsed)
        
        if not events:
            console.print("[yellow]No events found[/yellow]")
            return
            
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="dim")
        table.add_column("Time", style="dim")
        table.add_column("Event")
        table.add_column("Type")
        table.add_column("Location", style="dim")
        
        for event in events:
            date = event.start_time.strftime("%b %d")
            time = event.start_time.strftime("%I:%M %p")
            table.add_row(
                date,
                time,
                event.title,
                event.event_type,
                event.location or ""
            )
            
        console.print(table)

def show_help():
    """Show help information"""
    help_text = """
    [bold]Available Commands:[/bold]
    
    [cyan]Event Management:[/cyan]
    - Schedule a meeting/event
    - Cancel an event
    - Update an event
    - Show events for today/tomorrow/week
    
    [cyan]Calendar Management:[/cyan]
    - Sync calendar
    - List calendars
    - Show holidays
    
    [cyan]Examples:[/cyan]
    - "Schedule a team meeting tomorrow at 2pm"
    - "Show my events for today"
    - "Cancel my meeting with John"
    - "Sync my calendar"
    """
    console.print(Panel(help_text, title="Help"))

if __name__ == '__main__':
    cli()
