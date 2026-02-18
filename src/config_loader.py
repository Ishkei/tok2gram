import yaml
import os

def load_config(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing config.yaml: {e}")
            
    # Prioritize environment variable for bot token
    env_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if env_token:
        if 'telegram' not in config:
            config['telegram'] = {}
        config['telegram']['bot_token'] = env_token
        
    # Simple validation
    if 'telegram' not in config or 'bot_token' not in config['telegram'] or not config['telegram']['bot_token']:
        raise ValueError("Telegram bot token is missing. Set it in config.yaml or TELEGRAM_BOT_TOKEN environment variable.")
        
    return config

def load_creators(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Creators file not found: {file_path}")
        
    with open(file_path, 'r') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing creators.yaml: {e}")
            
    creators = data.get('creators', [])
    
    # Basic validation
    for entry in creators:
        if 'username' not in entry or 'chat_id' not in entry:
            raise ValueError(f"Invalid creator entry: {entry}")
            
    return creators
