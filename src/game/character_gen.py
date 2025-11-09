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
from src.core.llm import get_llm_client
from src.game.character_selector import ContactData
from src.game.message_sampler import sample_character_messages


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
        Generate a Character with message-grounded personality.
        
        Args:
            contact: ContactData from character selector
            verbose: Print progress messages
            
        Returns:
            Character object with actual message examples
        """
        if verbose:
            print(f"\n  🎭 Creating character: {contact.name}...")
            print(f"     Sampling from {contact.message_count} messages...")
        
        # Load full contact data
        try:
            data = self._load_contact_data(contact)
        except FileNotFoundError as e:
            print(f"  ⚠️  Error loading data for {contact.name}: {e}")
            return self._create_fallback_character(contact)
        
        conv_data = data['conversation']
        messages = conv_data.get('messages', [])
        metadata = conv_data.get('conversation_metadata', {})
        
        # Use full message history (no sampling)
        if verbose:
            print(f"     Loading full message history...")
        
        sample_data = sample_character_messages(messages, use_full_history=True)
        message_samples = sample_data['samples']
        
        if verbose:
            print(f"     ✓ Loaded {len(message_samples)} messages (full history)")
        
        # Generate brief personality and context (ONE quick LLM call)
        if verbose:
            print(f"     Generating brief personality context...")
        
        try:
            profile_text = self._generate_brief_profile(
                contact.name, 
                message_samples,
                metadata
            )
        except Exception as e:
            print(f"  ⚠️  Error generating profile: {e}")
            profile_text = self._create_fallback_profile_text(contact.name)
        
        # Determine initial relationship
        relationship = self._determine_initial_relationship(contact.message_count)
        relationship.character_name = contact.name
        
        if verbose:
            print(f"     ✓ Profile: {len(profile_text['personality'])} chars")
            print(f"     ✓ Context: {len(profile_text['context'])} chars")
            print(f"     ✓ Relationship: {relationship.level.value.replace('_', ' ').title()} ({relationship.strength}/100)")
        
        # Create Character object
        character = Character(
            name=contact.name,
            contact_id=contact.name,
            personality_brief=profile_text['personality'],
            relationship_context=profile_text['context'],
            message_examples=message_samples,
            relationship=relationship,
            message_count=contact.message_count,
            conversation_llm_path=data['conv_file_path'],
            current_location="Home",
            available_for_conversation=True
        )
        
        if verbose:
            print(f"  ✅ Character ready: {contact.name}\n")
        
        return character
    
    def _generate_brief_profile(
        self,
        contact_name: str,
        message_samples: List[Dict],
        metadata: Dict
    ) -> Dict[str, str]:
        """
        Generate brief personality and relationship context via LLM.
        ONE fast call, ~200 words each.
        """
        # Format a few examples for the prompt
        examples_text = []
        for msg in message_samples[:15]:  # Just show first 15 for prompt
            sender = "THEM" if msg.get('sender') == 'contact' else "YOU"
            content = msg.get('content', '').strip()[:150]  # Truncate long ones
            if content:
                examples_text.append(f"{sender}: {content}")
        
        examples = "\n".join(examples_text)
        
        prompt = f"""Analyze these real text messages between Arman and {contact_name}.

MESSAGE SAMPLES:
{examples}

Metadata: {metadata.get('total_messages', 0)} total messages over {metadata.get('conversation_span_days', 0)} days

Create TWO brief descriptions:

1. PERSONALITY (one paragraph, ~100-150 words):
   Who is {contact_name}? What are they like based on how they actually communicate?

2. RELATIONSHIP CONTEXT (one paragraph, ~100-150 words):
   What's the relationship between Arman and {contact_name}? How do they interact?

Keep it concise and grounded in the actual messages. Focus on communication style and patterns.

Return as JSON:
{{
  "personality": "...",
  "context": "..."
}}"""

        client = get_llm_client()
        response = client._call_api(
            messages=[
                {"role": "system", "content": "You create brief, accurate profiles from message data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        # Parse response
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(response[json_start:json_end])
            return json.loads(response)
        except:
            # Fallback
            return self._create_fallback_profile_text(contact_name)
    
    def _create_fallback_profile_text(self, contact_name: str) -> Dict[str, str]:
        """Create fallback profile text"""
        return {
            'personality': f"{contact_name} is someone you communicate with regularly. Based on message history, they seem friendly and engaged.",
            'context': f"You have an ongoing relationship with {contact_name}. Your communication has been consistent over time."
        }
    
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
        profile_text = self._create_fallback_profile_text(contact.name)
        relationship = self._determine_initial_relationship(contact.message_count)
        relationship.character_name = contact.name
        
        return Character(
            name=contact.name,
            contact_id=contact.name,
            personality_brief=profile_text['personality'],
            relationship_context=profile_text['context'],
            message_examples=[],
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
            print(f"  GENERATING {len(contacts)} CHARACTERS (FULL MESSAGE HISTORY)")
            est_time = len(contacts) * 15
            est_cost = len(contacts) * 0.03
            print(f"  Generation time: ~{est_time} seconds (~{est_time // 60} minutes)")
            print(f"  Generation cost: ~${est_cost:.2f}")
            print(f"  Note: Using full message history in conversations (~$0.30-0.50 per conversation)")
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

