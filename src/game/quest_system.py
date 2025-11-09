"""
Quest System (MVP - Simplified)

Basic quest generation and tracking. Can be expanded in future versions.
"""

from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from src.core.models import Quest, QuestStatus, QuestType, GameState, Character
from src.core.llm import get_llm_client


def generate_social_quest(character: Character) -> Quest:
    """
    Generate a simple social quest for a character.
    
    Args:
        character: Character to generate quest for
        
    Returns:
        Quest object
    """
    # For MVP, use simple template-based quests
    # Can be enhanced with LLM generation later
    
    rel_level = character.relationship.level.value
    
    if rel_level in ['stranger', 'acquaintance']:
        title = f"Get to know {character.name} better"
        description = f"Have a meaningful conversation with {character.name} to strengthen your connection."
        objectives = [
            "Start a conversation",
            "Ask about their interests",
            "Share something about yourself"
        ]
        reward = 15
    elif rel_level == 'friend':
        title = f"Catch up with {character.name}"
        description = f"It's been a while since you talked to {character.name}. Check in with them."
        objectives = [
            "Have a conversation",
            "Discuss recent events"
        ]
        reward = 10
    else:  # close_friend, best_friend
        title = f"Meaningful conversation with {character.name}"
        description = f"Have a deep, meaningful conversation with {character.name}."
        objectives = [
            "Start a conversation",
            "Discuss something important or personal"
        ]
        reward = 20
    
    quest = Quest(
        id=f"quest_{uuid.uuid4().hex[:8]}",
        title=title,
        description=description,
        quest_type=QuestType.SOCIAL,
        objectives=objectives,
        objectives_completed=[False] * len(objectives),
        required_character=character.name,
        time_cost=30,
        energy_cost=10,
        relationship_reward={character.name: reward}
    )
    
    return quest


def check_quest_progress(quest: Quest, game_state: GameState) -> bool:
    """
    Check if a quest has been completed based on game state.
    
    Args:
        quest: Quest to check
        game_state: Current game state
        
    Returns:
        True if quest should be marked complete
    """
    # For MVP: Simple completion logic
    # A social quest completes after having a conversation
    
    if quest.quest_type == QuestType.SOCIAL and quest.required_character:
        # Check if we've had a conversation with this character recently
        for conv in game_state.conversation_history[-5:]:  # Check last 5 conversations
            if conv.character_name == quest.required_character:
                # Mark objectives as complete
                for i in range(len(quest.objectives_completed)):
                    quest.objectives_completed[i] = True
                
                quest.status = QuestStatus.COMPLETED
                quest.completed_at = datetime.now()
                return True
    
    return False


def generate_quests_for_game(game_state: GameState, count: int = 3) -> List[Quest]:
    """
    Generate initial quests for the game.
    
    Args:
        game_state: Current game state
        count: Number of quests to generate
        
    Returns:
        List of Quest objects
    """
    quests = []
    
    # Generate social quests for characters we haven't talked to much
    characters = sorted(
        game_state.characters.values(),
        key=lambda c: c.relationship.interactions_count
    )
    
    for char in characters[:count]:
        quest = generate_social_quest(char)
        quests.append(quest)
    
    return quests


def apply_quest_rewards(quest: Quest, game_state: GameState) -> None:
    """
    Apply quest rewards to game state.
    
    Args:
        quest: Completed quest
        game_state: Current game state
    """
    # Apply relationship rewards
    for char_name, reward in quest.relationship_reward.items():
        character = game_state.get_character(char_name)
        if character:
            character.relationship.update_strength(reward)
            print(f"  💚 Relationship with {char_name} increased by {reward}!")
    
    # Apply money reward
    if quest.money_reward > 0:
        game_state.resources.earn_money(quest.money_reward)
        print(f"  💰 Earned ${quest.money_reward}!")
    
    # Apply energy reward
    if quest.energy_reward > 0:
        game_state.resources.restore_energy(quest.energy_reward)
        print(f"  ⚡ Restored {quest.energy_reward} energy!")


def update_quests(game_state: GameState) -> List[str]:
    """
    Update all active quests and check for completions.
    
    Args:
        game_state: Current game state
        
    Returns:
        List of quest titles that were completed
    """
    completed = []
    
    for quest in game_state.get_active_quests():
        if check_quest_progress(quest, game_state):
            completed.append(quest.title)
            game_state.completed_quests.append(quest.id)
            apply_quest_rewards(quest, game_state)
    
    return completed

