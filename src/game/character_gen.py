"""
Character Generation Module

Generates game characters with AI-powered personalities based on
real message history. This is where contacts become game characters.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from src.core.models import Character, Relationship, RelationshipLevel
from src.core.llm import generate_character
from src.game.character_selector import ContactData


class CharacterGenerator:
    """
    Generates Character objects from contact data using AI personality generation.
    """
    
    def __init__(self, data_folder: str = "data"):
        """
        Initialize character generator.
        
        Args:
            data_folder: Path to exported contact data
        """
        self.data_folder = Path(data_folder)
    
    def _load_contact_data(self, contact: ContactData) -> Dict:
        """
        Load full contact data from disk.
        
        Args:
            contact: ContactData object with file paths
            
        Returns:
            Dict with full contact information
        """
        # Load the main conversation LLM file
        contact_folder = self.data_folder / contact.name
        conv_file = contact_folder / "conversation_llm.json"
        
        if not conv_file.exists():
            raise FileNotFoundError(f"Conversation file not found: {conv_file}")
        
        with open(conv_file, 'r', encoding='utf-8') as f:
            conv_data = json.load(f)
        
        # Also load recent interactions if available
        recent_file = contact_folder / "conversation_recent_interactions.json"
        recent_data = None
        if recent_file.exists():
            with open(recent_file, 'r', encoding='utf-8') as f:
                recent_data = json.load(f)
        
        return {
            'conversation': conv_data,
            'recent_interactions': recent_data,
            'folder_path': str(contact_folder),
            'conv_file_path': str(conv_file)
        }
    
    def _determine_initial_relationship(self, message_count: int) -> Relationship:
        """
        Determine initial relationship strength based on message history.
        
        Args:
            message_count: Total number of messages exchanged
            
        Returns:
            Relationship object with appropriate initial state
        """
        # More messages = stronger initial relationship
        if message_count >= 1000:
            strength = 75  # Best Friend range
        elif message_count >= 500:
            strength = 65  # Close Friend range
        elif message_count >= 200:
            strength = 50  # Friend range
        elif message_count >= 50:
            strength = 35  # Acquaintance range
        else:
            strength = 20  # Low acquaintance
        
        # Create relationship with history
        rel = Relationship(
            character_name="temp",  # Will be set later
            strength=strength,
            interactions_count=message_count
        )
        
        # Set the level based on strength
        rel._update_level()
        
        return rel
    
    def generate_character(
        self, 
        contact: ContactData,
        verbose: bool = True
    ) -> Character:
        """
        Generate a full Character object from a ContactData.
        
        Args:
            contact: ContactData from character selector
            verbose: Print progress messages
            
        Returns:
            Character object with AI-generated personality
        """
        if verbose:
            print(f"\n  🎭 Generating character: {contact.name}...")
            print(f"     Analyzing {contact.message_count} messages...")
        
        # Load full contact data
        try:
            data = self._load_contact_data(contact)
        except FileNotFoundError as e:
            print(f"  ⚠️  Error loading data for {contact.name}: {e}")
            # Return minimal character
            return self._create_fallback_character(contact)
        
        conv_data = data['conversation']
        messages = conv_data.get('messages', [])
        metadata = conv_data.get('conversation_metadata', {})
        
        if verbose:
            print(f"     Generating AI personality...")
        
        # Generate personality using LLM
        try:
            personality = generate_character(
                contact_name=contact.name,
                message_history=messages,
                metadata=metadata
            )
        except Exception as e:
            print(f"  ⚠️  Error generating personality: {e}")
            print(f"     Using fallback personality...")
            personality = self._create_fallback_personality(contact.name)
        
        # Extract personality components
        personality_summary = personality.get('personality_summary', f"{contact.name} is a friend.")
        communication_style = personality.get('communication_style', 'casual and friendly')
        interests = personality.get('interests', [])
        typical_topics = personality.get('typical_topics', [])
        favorite_phrases = personality.get('favorite_phrases', [])
        
        if verbose:
            print(f"     ✓ Personality: {personality_summary[:60]}...")
            print(f"     ✓ Style: {communication_style}")
            print(f"     ✓ Interests: {', '.join(interests[:3])}")
        
        # Determine initial relationship
        relationship = self._determine_initial_relationship(contact.message_count)
        relationship.character_name = contact.name
        
        if verbose:
            print(f"     ✓ Relationship: {relationship.level.value.replace('_', ' ').title()} ({relationship.strength}/100)")
        
        # Create Character object
        character = Character(
            name=contact.name,
            contact_id=contact.name,  # Using name as ID for now
            personality_summary=personality_summary,
            communication_style=communication_style,
            interests=interests,
            typical_topics=typical_topics,
            favorite_phrases=favorite_phrases,
            relationship=relationship,
            message_count=contact.message_count,
            conversation_llm_path=data['conv_file_path'],
            current_location="Home",  # Default location
            available_for_conversation=True
        )
        
        if verbose:
            print(f"  ✅ Character ready: {contact.name}\n")
        
        return character
    
    def _create_fallback_personality(self, contact_name: str) -> Dict:
        """Create a basic fallback personality when AI generation fails"""
        return {
            'personality_summary': f"{contact_name} is a friend who you've stayed in touch with.",
            'communication_style': 'casual and friendly',
            'interests': ['general topics', 'daily life'],
            'typical_topics': ['catching up', 'plans', 'life updates'],
            'favorite_phrases': []
        }
    
    def _create_fallback_character(self, contact: ContactData) -> Character:
        """Create a minimal fallback character when data is missing"""
        personality = self._create_fallback_personality(contact.name)
        relationship = self._determine_initial_relationship(contact.message_count)
        relationship.character_name = contact.name
        
        return Character(
            name=contact.name,
            contact_id=contact.name,
            personality_summary=personality['personality_summary'],
            communication_style=personality['communication_style'],
            interests=personality['interests'],
            typical_topics=personality['typical_topics'],
            relationship=relationship,
            message_count=contact.message_count,
            current_location="Home",
            available_for_conversation=True
        )
    
    def generate_characters_batch(
        self, 
        contacts: List[ContactData],
        verbose: bool = True
    ) -> List[Character]:
        """
        Generate multiple characters in batch.
        
        Args:
            contacts: List of ContactData objects
            verbose: Print progress messages
            
        Returns:
            List of Character objects
        """
        if verbose:
            print(f"\n{'='*70}")
            print(f"  GENERATING {len(contacts)} CHARACTERS")
            print(f"{'='*70}")
        
        characters = []
        
        for i, contact in enumerate(contacts, 1):
            if verbose:
                print(f"\n[{i}/{len(contacts)}]")
            
            character = self.generate_character(contact, verbose=verbose)
            characters.append(character)
            
            # Small delay to avoid rate limiting
            if i < len(contacts):
                import time
                time.sleep(0.5)
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"  ✅ ALL CHARACTERS GENERATED")
            print(f"{'='*70}\n")
        
        return characters


def generate_game_characters(
    contacts: List[ContactData],
    data_folder: str = "data",
    verbose: bool = True
) -> List[Character]:
    """
    Main entry point for character generation.
    
    Args:
        contacts: List of ContactData from character selector
        data_folder: Path to exported contact data
        verbose: Print progress messages
        
        
    Returns:
        List of Character objects ready for game
    """
    generator = CharacterGenerator(data_folder)
    return generator.generate_characters_batch(contacts, verbose=verbose)


if __name__ == "__main__":
    # Test character generation
    from src.game.character_selector import select_characters
    
    print("Testing character generation...")
    
    # Select some characters
    selected = select_characters(interactive=False)  # Auto-select top 3 for testing
    selected = selected[:3]  # Just test with 3
    
    # Generate characters
    characters = generate_game_characters(selected)
    
    print(f"\nGenerated {len(characters)} characters:")
    for char in characters:
        print(f"\n{char.name}:")
        print(f"  Personality: {char.personality_summary}")
        print(f"  Style: {char.communication_style}")
        print(f"  Relationship: {char.get_relationship_description()}")

