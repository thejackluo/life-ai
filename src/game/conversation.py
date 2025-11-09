"""
Conversation System

Handles free-form conversations between player and characters,
integrating LLM responses and sentiment analysis for relationship dynamics.
"""

from typing import Optional, List
from datetime import datetime

from src.core.models import GameState, Character, Conversation, Message
from src.core.llm import get_character_response
from src.core.sentiment import get_analyzer

# Type checking import to avoid circular dependency
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.core.memory_models import MemoryCluster


def have_conversation(game_state: GameState, character: Character) -> None:
    """
    Start and manage a conversation with a character.
    
    Args:
        game_state: Current game state
        character: Character to talk to
    """
    # Get relationship mood indicator
    rel_emoji, rel_color, rel_mood = _get_relationship_mood(character)
    
    print("\n" + "💬 " * 30)
    print(f"\n  {rel_emoji} Conversation with {character.name}")
    print(f"  Relationship: {character.get_relationship_description()}")
    print(f"  Mood: {rel_mood}")
    print("\n" + "💬 " * 30 + "\n")
    
    # Start conversation
    conversation = game_state.start_conversation(character.name)
    analyzer = get_analyzer()
    
    # Opening message from character
    opening = _generate_opening_message(character)
    print(f"  {character.name}: {opening}\n")
    conversation.add_message(character.name, opening)
    
    # Conversation loop
    while True:
        # Get player input
        print(f"  You: ", end='')
        player_input = input().strip()
        
        if not player_input:
            continue
        
        # Check for exit commands
        if player_input.lower() in ['exit', 'quit', 'bye', 'goodbye', 'end']:
            # Goodbye message
            goodbye = _generate_goodbye_message(character)
            print(f"\n  {character.name}: {goodbye}\n")
            conversation.add_message(character.name, goodbye)
            break
        
        # Analyze sentiment
        impact, category, description = analyzer.get_relationship_impact(player_input)
        
        # Add player message to conversation
        player_msg = conversation.add_message("player", player_input, sentiment=impact)
        
        # Show sentiment feedback with granular impact
        if abs(impact) > 0.5:  # Only show if somewhat significant
            feedback = analyzer.get_contextual_feedback(player_input, character.name)
            print(f"  {feedback}")
        
        # Update relationship
        character.relationship.update_strength(impact)
        
        # Build conversation history for context
        conv_history = [
            {"speaker": msg.speaker, "content": msg.content}
            for msg in conversation.messages[-10:]  # Last 10 messages
        ]
        
        # Generate character response with relationship context
        print(f"\n  {character.name}: ", end='', flush=True)
        
        try:
            # Build message-grounded context
            context = _build_message_grounded_context(character, conversation)
            
            response = get_character_response(
                character_name=character.name,
                personality=character.personality_brief,
                style=character.relationship_context,  # Using context as "style" field
                history=conv_history,
                player_msg=player_input,
                rel_level=character.relationship.level.value,
                context=context
            )
            
            # Type out response (simulated typing effect)
            _type_text(response)
            print("\n")
            
            # Add to conversation
            conversation.add_message(character.name, response)
            
        except Exception as e:
            print(f"[Error generating response: {e}]")
            print(f"That's interesting... let me think about that.\n")
            conversation.add_message(character.name, "That's interesting...")
        
        # Show relationship change if significant  
        if abs(impact) >= 3:
            change_text = f"+{impact:.1f}" if impact > 0 else f"{impact:.1f}"
            rel_emoji = "💚" if impact > 0 else "💔"
            print(f"  {rel_emoji} Relationship {change_text} → {character.relationship.strength}/100\n")
    
    # End conversation
    game_state.end_current_conversation()
    
    # Summary
    print("\n" + "="*70)
    print("  CONVERSATION SUMMARY")
    print("="*70)
    print(f"  Messages exchanged: {conversation.turns_count}")
    print(f"  Overall sentiment: {conversation.total_sentiment_delta:+.1f}")
    print(f"  Final relationship: {character.get_relationship_description()}")
    print("="*70 + "\n")


def _get_relationship_mood(character: Character) -> tuple:
    """
    Get visual indicators for relationship state.
    
    Returns:
        Tuple of (emoji, color_desc, mood_text)
    """
    strength = character.relationship.strength
    level = character.relationship.level.value
    
    if strength >= 80:
        return "💚", "warm green", "Very close and comfortable"
    elif strength >= 60:
        return "💙", "friendly blue", "Close and trusting"
    elif strength >= 40:
        return "💛", "neutral yellow", "Friendly but casual"
    elif strength >= 20:
        return "🧡", "distant orange", "Acquaintances, somewhat distant"
    else:
        return "💔", "strained red", "Relationship is strained"


def _generate_opening_message(character: Character) -> str:
    """Generate an appropriate opening message from the character"""
    rel_level = character.relationship.level
    
    # Different openings based on relationship level
    if rel_level.value == "best_friend":
        openings = [
            "Hey! So good to see you!",
            "What's up! How have you been?",
            "Hey you! I was just thinking about you!",
        ]
    elif rel_level.value == "close_friend":
        openings = [
            "Hey! How's it going?",
            "Hi! What's new with you?",
            "Hey there! How have you been?",
        ]
    elif rel_level.value == "friend":
        openings = [
            "Hey! How are you?",
            "Hi! Good to see you.",
            "Hey, what's up?",
        ]
    elif rel_level.value == "acquaintance":
        openings = [
            "Hi! How's it going?",
            "Hey, how are you?",
            "Hi there!",
        ]
    else:  # stranger
        openings = [
            "Hi, how are you?",
            "Hello!",
            "Hey!",
        ]
    
    # Pick based on character name hash for consistency
    idx = hash(character.name) % len(openings)
    return openings[idx]


def _generate_goodbye_message(character: Character) -> str:
    """Generate an appropriate goodbye message from the character"""
    rel_level = character.relationship.level
    
    if rel_level.value == "best_friend":
        goodbyes = [
            "Talk to you soon! Miss you already!",
            "Alright, catch you later! Love you!",
            "See you soon! Take care!",
        ]
    elif rel_level.value == "close_friend":
        goodbyes = [
            "Talk soon! Take care!",
            "Alright, see you later!",
            "Catch you later!",
        ]
    elif rel_level.value == "friend":
        goodbyes = [
            "See you later!",
            "Talk to you soon!",
            "Bye!",
        ]
    else:
        goodbyes = [
            "See you around!",
            "Bye!",
            "Take care!",
        ]
    
    idx = hash(character.name) % len(goodbyes)
    return goodbyes[idx]


def _build_message_grounded_context(character: Character, conversation: Conversation) -> str:
    """
    Build context using ACTUAL MESSAGE EXAMPLES.
    This is the key to authenticity.
    
    Args:
        character: Character with message examples
        conversation: Current conversation
        
    Returns:
        Context with real message examples
    """
    context_parts = []
    
    # Show actual message examples
    if character.message_examples:
        examples_text = character.get_message_examples_text()
        context_parts.append(f"HOW YOU ACTUALLY TEXT (study these real examples):\n\n{examples_text}")
    
    # Add current mood if different from neutral
    if character.current_mood != "neutral":
        context_parts.append(f"\nCURRENT MOOD: {character.current_mood}")
    
    # Add recent topics if any
    if character.recent_conversation_topics:
        context_parts.append(f"\nRECENT TOPICS: {', '.join(character.recent_conversation_topics[-3:])}")
    
    return "\n\n".join(context_parts)


def _build_relationship_context(character: Character, conversation: Conversation) -> str:
    """
    Build context about relationship state for more dynamic AI responses.
    
    Args:
        character: The character
        conversation: Current conversation
        
    Returns:
        Context string for AI
    """
    strength = character.relationship.strength
    recent_sentiment = conversation.total_sentiment_delta
    
    contexts = []
    
    # Overall relationship state
    if strength >= 80:
        contexts.append("You're very close friends - comfortable, supportive, can be vulnerable")
    elif strength >= 60:
        contexts.append("Good friends - trust each other, share regularly")
    elif strength >= 40:
        contexts.append("Friendly but not super close - casual and light")
    elif strength >= 20:
        contexts.append("Acquaintances - somewhat distant, polite")
    else:
        contexts.append("Relationship is strained - there's tension")
    
    # Recent conversation sentiment
    if recent_sentiment > 10:
        contexts.append("This conversation has been going really well")
    elif recent_sentiment < -10:
        contexts.append("This conversation has been tense or negative")
    
    # Sentiment trend from relationship history
    if len(character.relationship.sentiment_history) >= 3:
        recent_avg = sum(character.relationship.sentiment_history[-3:]) / 3
        if recent_avg > 5:
            contexts.append("Recent interactions have been very positive")
        elif recent_avg < -5:
            contexts.append("Recent interactions have been negative")
    
    return ". ".join(contexts) if contexts else None


def _type_text(text: str, delay: float = 0.03) -> None:
    """
    Print text with a typing effect (optional, can be disabled for speed).
    
    Args:
        text: Text to print
        delay: Delay between characters (0 for instant)
    """
    import sys
    import time
    
    # Disable typing effect for now (too slow for development)
    # Can be enabled later as a config option
    delay = 0
    
    if delay == 0:
        print(text, end='', flush=True)
    else:
        for char in text:
            print(char, end='', flush=True)
            time.sleep(delay)


def analyze_conversation_sentiment(conversation: Conversation) -> dict:
    """
    Analyze the overall sentiment of a conversation.
    
    Args:
        conversation: Conversation object
        
    Returns:
        Dict with sentiment analysis
    """
    analyzer = get_analyzer()
    
    player_messages = [
        msg.content for msg in conversation.messages 
        if msg.speaker == "player"
    ]
    
    if not player_messages:
        return {
            'average_sentiment': 0.0,
            'tone': 'neutral',
            'trend': 'stable'
        }
    
    return analyzer.analyze_conversation_tone(player_messages)

