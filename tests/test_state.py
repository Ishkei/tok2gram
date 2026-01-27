import pytest
import sqlite3
import os
from state import StateStore

@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "state.db"
    return StateStore(str(db_path))

def test_is_processed_not_found(store):
    assert store.is_processed("none") is False

def test_is_processed_found_not_uploaded(store):
    # Manually insert a post without uploaded_at
    conn = sqlite3.connect(store.db_path)
    conn.execute("INSERT INTO posts (post_id, creator, kind, source_url) VALUES (?, ?, ?, ?)",
                 ("id1", "creator1", "video", "url1"))
    conn.commit()
    conn.close()
    
    assert store.is_processed("id1") is False

def test_is_processed_found_uploaded(store):
    # Manually insert a post with uploaded_at
    conn = sqlite3.connect(store.db_path)
    conn.execute("INSERT INTO posts (post_id, creator, kind, source_url, uploaded_at) VALUES (?, ?, ?, ?, ?)",
                 ("id2", "creator1", "video", "url2", 1600000000))
    conn.commit()
    conn.close()
    
    assert store.is_processed("id2") is True
