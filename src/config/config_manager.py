from src.config.manager import ConfigManager as BaseConfigManager

class ConfigManager(BaseConfigManager):
    def load_google_config(self):
        config = self.load_config()
        return config.get('google', {})
