"""
Life AI - Main Game Entry Point

Terminal-based life simulation game built from your real message history.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.models import GameState, Character, Place
from src.core.llm import get_llm_client
from src.game.character_selector import select_characters
from src.game.character_gen import generate_game_characters


class LifeAIGame:
    """
    Main game class that manages the REPL and game state.
    """
    
    def __init__(self):
        """Initialize the game"""
        self.game_state: Optional[GameState] = None
        self.running = False
        self.commands = self._init_commands()
    
    def _init_commands(self) -> dict:
        """Initialize command handlers"""
        return {
            'help': self.cmd_help,
            'h': self.cmd_help,
            '?': self.cmd_help,
            
            'talk': self.cmd_talk,
            't': self.cmd_talk,
            
            'status': self.cmd_status,
            'stats': self.cmd_status,
            
            'characters': self.cmd_list_characters,
            'chars': self.cmd_list_characters,
            'c': self.cmd_list_characters,
            
            'quests': self.cmd_list_quests,
            'q': self.cmd_list_quests,
            
            'travel': self.cmd_travel,
            'go': self.cmd_travel,
            
            'save': self.cmd_save,
            'load': self.cmd_load,
            
            'quit': self.cmd_quit,
            'exit': self.cmd_quit,
        }
    
    # ========================================================================
    # GAME INITIALIZATION
    # ========================================================================
    
    def new_game(self, player_name: Optional[str] = None, auto_select: bool = False):
        """
        Start a new game.
        
        Args:
            player_name: Player's name (prompts if not provided)
            auto_select: If True, auto-select top characters; if False, interactive
        """
        print("\n" + "🌟 " * 25)
        print("\n  LIFE AI - Your Life as a Game")
        print("\n  A simulation built from your real relationships\n")
        print("🌟 " * 25 + "\n")
        
        # Get player name
        if not player_name:
            player_name = input("  What's your name? ").strip()
            if not player_name:
                player_name = "Player"
        
        print(f"\n  Welcome, {player_name}!\n")
        
        # Character selection
        print("  First, let's choose which contacts become characters in your game...\n")
        
        selected_contacts = select_characters(interactive=not auto_select)
        
        if not selected_contacts:
            print("\n  No characters selected. Exiting...")
            return False
        
        print(f"\n  Generating characters from your message history...")
        print(f"  This may take a minute...\n")
        
        # Generate characters with AI personalities
        characters = generate_game_characters(selected_contacts, verbose=True)
        
        # Create game state
        self.game_state = GameState(player_name=player_name)
        
        # Add characters to game
        for character in characters:
            self.game_state.add_character(character)
        
        # Add initial places
        self._add_initial_places()
        
        # Save initial state
        self.cmd_save(auto=True)
        
        print("\n" + "="*70)
        print("  ✅ GAME INITIALIZED")
        print("="*70)
        print(self.game_state.get_summary())
        print("\n  Type 'help' to see available commands.")
        print("  Type 'talk [name]' to start a conversation.")
        print("\n" + "="*70 + "\n")
        
        return True
    
    def _add_initial_places(self):
        """Add initial places to the game"""
        # Add home
        home = Place(
            name="Home",
            description="Your home. A place of comfort and reflection.",
            distance_from_home=0.0,
            travel_time=0,
            travel_cost=0.0,
            discovered=True,
            place_type="home"
        )
        self.game_state.add_place(home)
        
        # Add a few common places (can be expanded later)
        coffee_shop = Place(
            name="Coffee Shop",
            description="A cozy coffee shop. Good for meeting friends.",
            distance_from_home=2.5,
            travel_time=15,
            travel_cost=3.0,
            discovered=True,
            place_type="coffee_shop"
        )
        self.game_state.add_place(coffee_shop)
    
    # ========================================================================
    # MAIN GAME LOOP
    # ========================================================================
    
    def run(self):
        """Main game loop (REPL)"""
        self.running = True
        
        while self.running:
            try:
                # Update last played
                if self.game_state:
                    self.game_state.update_last_played()
                
                # Get input
                user_input = input(f"\n[{self.game_state.current_location}] > ").strip()
                
                if not user_input:
                    continue
                
                # Parse command
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                # Execute command
                if command in self.commands:
                    self.commands[command](args)
                else:
                    print(f"  Unknown command: '{command}'. Type 'help' for available commands.")
                
            except KeyboardInterrupt:
                print("\n")
                self.cmd_quit("")
            except EOFError:
                print("\n")
                self.cmd_quit("")
            except Exception as e:
                print(f"\n  ⚠️  Error: {str(e)}")
                print("  Type 'help' for available commands.\n")
    
    # ========================================================================
    # COMMAND HANDLERS
    # ========================================================================
    
    def cmd_help(self, args: str):
        """Show help message"""
        print("\n" + "="*70)
        print("  LIFE AI - COMMANDS")
        print("="*70)
        print("\n  CONVERSATION:")
        print("    talk [name], t [name]   - Start a conversation with a character")
        print("\n  INFORMATION:")
        print("    status, stats           - Show your current status")
        print("    characters, chars, c    - List all characters and relationships")
        print("    quests, q               - List active quests")
        print("\n  MOVEMENT:")
        print("    travel [place], go [place] - Travel to a location")
        print("\n  GAME:")
        print("    save                    - Save your game")
        print("    load                    - Load a saved game")
        print("    help, h, ?              - Show this help message")
        print("    quit, exit              - Exit the game")
        print("\n" + "="*70 + "\n")
    
    def cmd_talk(self, args: str):
        """Start a conversation with a character"""
        if not args:
            print("\n  Who do you want to talk to? Use: talk [name]")
            self.cmd_list_characters("")
            return
        
        # Find character (case-insensitive partial match)
        query = args.lower()
        matches = [c for c in self.game_state.characters.values() if query in c.name.lower()]
        
        if not matches:
            print(f"\n  ⚠️  No character found matching '{args}'")
            print("  Available characters:")
            self.cmd_list_characters("")
            return
        
        if len(matches) > 1:
            print(f"\n  Multiple matches found. Please be more specific:")
            for char in matches:
                print(f"    - {char.name}")
            return
        
        character = matches[0]
        
        # Check if character is available
        if not character.available_for_conversation:
            print(f"\n  ⚠️  {character.name} is not available right now.")
            return
        
        # Import here to avoid circular imports
        from src.game.conversation import have_conversation
        
        # Start conversation
        have_conversation(self.game_state, character)
    
    def cmd_status(self, args: str):
        """Show current status"""
        print(self.game_state.get_summary())
    
    def cmd_list_characters(self, args: str):
        """List all characters and their relationships"""
        print("\n" + "="*70)
        print("  YOUR CHARACTERS")
        print("="*70 + "\n")
        
        # Sort by relationship strength
        chars = sorted(
            self.game_state.characters.values(),
            key=lambda c: c.relationship.strength,
            reverse=True
        )
        
        for char in chars:
            rel = char.relationship
            bar_length = 20
            filled = int((rel.strength / 100) * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            print(f"  {char.name}")
            print(f"    {bar} {rel.strength}/100 ({rel.level.value.replace('_', ' ').title()})")
            print(f"    {char.personality_summary[:60]}...")
            print()
        
        print("="*70 + "\n")
    
    def cmd_list_quests(self, args: str):
        """List active quests"""
        active = self.game_state.get_active_quests()
        available = self.game_state.get_available_quests()
        
        print("\n" + "="*70)
        print("  YOUR QUESTS")
        print("="*70 + "\n")
        
        if active:
            print("  ACTIVE:")
            for quest in active:
                print(f"    ⚡ {quest.title}")
                print(f"       {quest.description}")
                print()
        
        if available:
            print("  AVAILABLE:")
            for quest in available:
                print(f"    ○ {quest.title}")
                print(f"       {quest.description}")
                print()
        
        if not active and not available:
            print("  No quests available yet.")
            print("  Quests will appear as you interact with characters!\n")
        
        print("="*70 + "\n")
    
    def cmd_travel(self, args: str):
        """Travel to a location"""
        print("\n  ⚠️  Travel system not yet implemented.")
        print("  This will be added in a future update!\n")
    
    def cmd_save(self, args: str = "", auto: bool = False):
        """Save the game"""
        # Import here to avoid issues during initialization
        from src.game.save_load import save_game
        
        if not auto:
            print("\n  💾 Saving game...")
        
        try:
            save_path = save_game(self.game_state)
            if not auto:
                print(f"  ✅ Game saved to: {save_path}\n")
        except Exception as e:
            print(f"  ⚠️  Error saving game: {e}\n")
    
    def cmd_load(self, args: str):
        """Load a saved game"""
        from src.game.save_load import load_game, list_saves
        
        print("\n  📂 Available saves:")
        saves = list_saves()
        
        if not saves:
            print("  No saved games found.\n")
            return
        
        for i, (name, path) in enumerate(saves, 1):
            print(f"    {i}. {name}")
        
        choice = input("\n  Enter save number to load (or 'cancel'): ").strip()
        
        if choice.lower() in ['cancel', 'c', '']:
            print("  Cancelled.\n")
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(saves):
                _, save_path = saves[idx]
                self.game_state = load_game(save_path)
                print(f"\n  ✅ Game loaded!\n")
                print(self.game_state.get_summary())
            else:
                print("  Invalid selection.\n")
        except ValueError:
            print("  Invalid input.\n")
    
    def cmd_quit(self, args: str):
        """Quit the game"""
        print("\n  Thanks for playing Life AI!")
        
        # Auto-save before quitting
        if self.game_state:
            self.cmd_save(auto=True)
            print("  Game auto-saved.")
        
        print("\n  See you next time! 🌟\n")
        self.running = False


def main():
    """Main entry point"""
    game = LifeAIGame()
    
    # Check for .env file
    if not os.path.exists('.env'):
        print("\n⚠️  Warning: No .env file found!")
        print("   Please create a .env file with your OPENAI_API_KEY")
        print("   Example: OPENAI_API_KEY=sk-...")
        print()
        return
    
    # New game
    success = game.new_game()
    
    if success:
        # Run game loop
        game.run()


if __name__ == "__main__":
    main()

