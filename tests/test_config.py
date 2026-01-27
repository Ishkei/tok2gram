import pytest
import yaml
import os
from config_loader import load_config, load_creators

def test_load_config_valid(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_data = {
        'telegram': {'bot_token': 'test_token'},
        'settings': {
            'fetch_depth': 10,
            'download_workers': 3,
            'yt_concurrent_fragments': 2,
            'retry_uploads': 1,
            'delay_between_creators_seconds_min': 10,
            'delay_between_creators_seconds_max': 30
        }
    }
    config_file.write_text(yaml.dump(config_data))
    
    loaded = load_config(str(config_file))
    assert loaded['telegram']['bot_token'] == 'test_token'
    assert loaded['settings']['fetch_depth'] == 10

def test_load_creators_valid(tmp_path):
    creators_file = tmp_path / "creators.yaml"
    creators_data = {
        'creators': [
            {'username': 'user1', 'chat_id': 'chat1'},
            {'username': 'user2', 'chat_id': 'chat2', 'topic_id': 123}
        ]
    }
    creators_file.write_text(yaml.dump(creators_data))
    
    loaded = load_creators(str(creators_file))
    assert len(loaded) == 2
    assert loaded[0]['username'] == 'user1'
    assert loaded[1]['topic_id'] == 123

def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("non_existent.yaml")
