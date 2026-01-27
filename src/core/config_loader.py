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
            
    # Simple validation
    if 'telegram' not in config or 'bot_token' not in config['telegram']:
        raise ValueError("config.yaml is missing telegram.bot_token")
        
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