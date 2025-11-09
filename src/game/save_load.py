"""
Save/Load System

Handles game state persistence using JSON serialization.
"""

import json
import os
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime

from src.core.models import GameState


SAVES_DIR = Path("saves")
AUTOSAVE_NAME = "autosave.json"


def ensure_saves_dir() -> Path:
    """Ensure saves directory exists"""
    SAVES_DIR.mkdir(exist_ok=True)
    return SAVES_DIR


def save_game(game_state: GameState, save_name: Optional[str] = None) -> str:
    """
    Save game state to JSON file.
    
    Args:
        game_state: GameState to save
        save_name: Optional custom save name (defaults to autosave)
        
    Returns:
        Path to saved file
    """
    ensure_saves_dir()
    
    # Generate save filename
    if not save_name:
        save_name = AUTOSAVE_NAME
    elif not save_name.endswith('.json'):
        save_name = f"{save_name}.json"
    
    save_path = SAVES_DIR / save_name
    
    # Serialize to JSON
    try:
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(
                game_state.model_dump(mode='json'),
                f,
                indent=2,
                ensure_ascii=False,
                default=str  # Handle datetime objects
            )
        return str(save_path)
    except Exception as e:
        raise Exception(f"Failed to save game: {e}")


def load_game(save_path: Optional[str] = None) -> GameState:
    """
    Load game state from JSON file.
    
    Args:
        save_path: Path to save file (defaults to autosave)
        
    Returns:
        Loaded GameState
    """
    if not save_path:
        save_path = SAVES_DIR / AUTOSAVE_NAME
    else:
        save_path = Path(save_path)
    
    if not save_path.exists():
        raise FileNotFoundError(f"Save file not found: {save_path}")
    
    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Deserialize from JSON
        game_state = GameState.model_validate(data)
        return game_state
        
    except Exception as e:
        raise Exception(f"Failed to load game: {e}")


def list_saves() -> List[Tuple[str, str]]:
    """
    List all available save files.
    
    Returns:
        List of tuples (display_name, file_path)
    """
    ensure_saves_dir()
    
    saves = []
    for save_file in SAVES_DIR.glob("*.json"):
        # Get file modification time
        mtime = save_file.stat().st_mtime
        mod_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        
        # Create display name
        name = save_file.stem
        display = f"{name} ({mod_date})"
        
        saves.append((display, str(save_file)))
    
    # Sort by modification time (most recent first)
    saves.sort(key=lambda x: Path(x[1]).stat().st_mtime, reverse=True)
    
    return saves


def delete_save(save_path: str) -> bool:
    """
    Delete a save file.
    
    Args:
        save_path: Path to save file
        
    Returns:
        True if deleted successfully
    """
    try:
        Path(save_path).unlink()
        return True
    except Exception:
        return False


def export_save(game_state: GameState, export_name: str) -> str:
    """
    Export game state to a named save file.
    
    Args:
        game_state: GameState to export
        export_name: Name for the export
        
    Returns:
        Path to exported file
    """
    # Clean filename
    safe_name = "".join(c for c in export_name if c.isalnum() or c in (' ', '-', '_')).strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_name}_{timestamp}.json"
    
    return save_game(game_state, filename)

