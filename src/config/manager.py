from typing import Optional, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from rich.console import Console
from rich.prompt import Prompt
import keyring
import logging

logger = logging.getLogger(__name__)

console = Console()

class ConfigManager:
    """Manage application configuration and environment variables"""
    
    def __init__(self, env_file: str = None):
        """Initialize config manager"""
        if env_file:
            self.env_file = env_file
        else:
            # Get the project root directory (two levels up from this file)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.env_file = os.path.join(project_root, '.env')
            logger.info(f"Looking for .env file at: {self.env_file}")
        
        self.config = {}
        self.load_config()
        
    def load_config(self):
        """Load configuration from environment and .env file"""
        # Load .env file if it exists
        if os.path.exists(self.env_file):
            logger.info(f"Loading environment variables from {self.env_file}")
            load_dotenv(self.env_file, override=True)  # Force reload of environment variables
            
        # Load all environment variables
        self.config['app'] = self._load_app_config()
        self.config['openai'] = self._load_openai_config()
        self.config['google'] = self._load_google_config()
        self.config['features'] = self._load_feature_config()
        self.config['development'] = self._load_dev_config()
        
    def _load_openai_config(self) -> Dict[str, Any]:
        """Load OpenAI configuration"""
        return {
            'api_key': os.getenv('OPENAI_API_KEY') or self._get_secret('openai_api_key'),
            'model': os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
        }
        
    def _load_google_config(self) -> Dict[str, Any]:
        """Load Google-specific configuration."""
        # Try to load service account key from JSON file
        service_account_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'service-account.json')
        if os.path.exists(service_account_path):
            try:
                with open(service_account_path, 'r') as f:
                    service_account_info = json.load(f)
                logger.info("Successfully loaded service account JSON file")
            except Exception as e:
                logger.error(f"Failed to load service account JSON: {e}")
                raise
        else:
            raise ValueError(f"Service account JSON file not found at {service_account_path}")

        # Add calendar IDs
        calendar_ids = os.getenv('GOOGLE_CALENDAR_IDS', '').split(',')
        service_account_info['calendar_ids'] = [cid.strip() for cid in calendar_ids if cid.strip()]

        # Log loaded configuration (excluding private key)
        safe_config = service_account_info.copy()
        if 'private_key' in safe_config:
            safe_config['private_key'] = '***REDACTED***'
        logger.info(f"Loaded Google service account config: {safe_config}")
        
        return service_account_info
        
    def _load_app_config(self) -> Dict[str, Any]:
        """Load application settings"""
        return {
            'timezone': os.getenv('TIMEZONE', 'America/Los_Angeles'),
            'default_calendar_id': os.getenv('DEFAULT_CALENDAR_ID', 'primary'),
            'sync_interval': int(os.getenv('SYNC_INTERVAL', 30)),
            'database_path': os.path.expanduser(os.getenv('DATABASE_PATH', '~/.calendaragent/calendar.db'))
        }
        
    def _load_feature_config(self) -> Dict[str, Any]:
        """Load feature flags"""
        return {
            'enable_holiday_calendar': os.getenv('ENABLE_HOLIDAY_CALENDAR', 'true').lower() == 'true',
            'enable_conflict_detection': os.getenv('ENABLE_CONFLICT_DETECTION', 'true').lower() == 'true',
            'enable_smart_scheduling': os.getenv('ENABLE_SMART_SCHEDULING', 'true').lower() == 'true'
        }
        
    def _load_dev_config(self) -> Dict[str, Any]:
        """Load development settings"""
        return {
            'debug': os.getenv('DEBUG', 'false').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO')
        }
        
    def _expand_path(self, path: str) -> str:
        """Expand user and environment variables in path"""
        if not path:
            return path
        return os.path.expandvars(os.path.expanduser(path))
        
    def _parse_bool(self, value: str) -> bool:
        """Parse string boolean value"""
        return str(value).lower() in ('true', '1', 'yes', 'on')
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        parts = key.split('.')
        value = self.config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
        return value if value is not None else default
        
    def validate(self) -> bool:
        """Validate required configuration"""
        required = {
            'openai.api_key': 'OpenAI API key is required for natural language processing',
            'google.client_id': 'Google Calendar client ID is required for authentication',
            'google.client_secret': 'Google Calendar client secret is required for authentication'
        }
        
        # Reload config to ensure we have the latest values
        self.load_config()
        
        missing = []
        for key, message in required.items():
            if not self.get(key):
                missing.append(f"- {key}: {message}")
                
        if missing:
            console.print("[bold red]Missing Required Configuration:[/bold red]")
            for msg in missing:
                console.print(msg)
            return False
            
        return True
        
    def setup_wizard(self):
        """Interactive setup wizard for configuration"""
        console.print("[bold blue]Calendar Agent Setup Wizard[/bold blue]")
        console.print("This wizard will help you set up your Calendar Agent configuration.\n")
        
        # OpenAI setup
        console.print("\n[bold cyan]OpenAI Configuration[/bold cyan]")
        api_key = Prompt.ask("Enter your OpenAI API key", password=True)
        if api_key:
            self._save_secret('openai_api_key', api_key)
        
        # Google Calendar setup
        console.print("\n[bold cyan]Google Calendar Configuration[/bold cyan]")
        client_id = Prompt.ask("Enter your Google Client ID")
        client_secret = Prompt.ask("Enter your Google Client Secret", password=True)
        if client_id and client_secret:
            self._save_secret('google_client_id', client_id)
            self._save_secret('google_client_secret', client_secret)
        
        # Create .env file with non-sensitive settings
        self._create_env_file()
        
        # Reload configuration
        self.load_config()
        
        console.print("\n[bold green]Setup complete! Configuration has been saved.[/bold green]")
        
    def _save_secret(self, key: str, value: str):
        """Save secret to system keyring"""
        if value:  # Only save if value is not empty
            keyring.set_password('calendaragent', key, value)
        
    def _get_secret(self, key: str) -> Optional[str]:
        """Get secret from system keyring"""
        try:
            return keyring.get_password('calendaragent', key)
        except Exception:
            return None
        
    def _create_env_file(self):
        """Create .env file with non-sensitive settings"""
        env_content = """# Application Settings
TIMEZONE=America/Los_Angeles
DEFAULT_CALENDAR_ID=primary
SYNC_INTERVAL=30
DATABASE_PATH=~/.calendaragent/calendar.db

# Optional Features
ENABLE_HOLIDAY_CALENDAR=true
ENABLE_CONFLICT_DETECTION=true
ENABLE_SMART_SCHEDULING=true

# Development Settings
DEBUG=false
LOG_LEVEL=INFO"""
        
        with open(self.env_file, 'w') as f:
            f.write(env_content)
            
    def ensure_directories(self):
        """Ensure required directories exist"""
        paths = [
            os.path.dirname(self.get('google.token_path')),
            os.path.dirname(self.get('app.database_path'))
        ]
        
        for path in paths:
            if path:
                os.makedirs(self._expand_path(path), exist_ok=True)
                
    def get_openai_key(self) -> Optional[str]:
        """Get OpenAI API key"""
        return self.get('openai.api_key')
        
    def get_google_credentials(self) -> Dict[str, str]:
        """Get Google Calendar credentials"""
        return {
            'client_id': self.get('google.client_id'),
            'client_secret': self.get('google.client_secret')
        }
