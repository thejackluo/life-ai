"""
Core Data Models for Life AI

Pydantic models that define all game entities, state, and relationships.
These models provide type safety, validation, and easy serialization.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, TYPE_CHECKING
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from src.core.memory_models import CharacterMemory


# ============================================================================
# ENUMS
# ============================================================================

class RelationshipLevel(str, Enum):
    """Relationship strength categories"""
    STRANGER = "stranger"           # 0-20
    ACQUAINTANCE = "acquaintance"   # 21-40
    FRIEND = "friend"               # 41-60
    CLOSE_FRIEND = "close_friend"   # 61-80
    BEST_FRIEND = "best_friend"     # 81-100


class QuestStatus(str, Enum):
    """Quest lifecycle states"""
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class QuestType(str, Enum):
    """Types of quests"""
    SOCIAL = "social"              # Relationship-focused
    PERSONAL_GROWTH = "personal_growth"  # Self-improvement
    EXPLORATION = "exploration"    # Discover new places
    ASPIRATIONAL = "aspirational"  # Meet new people/goals


# ============================================================================
# RELATIONSHIP & CHARACTER MODELS
# ============================================================================

class Relationship(BaseModel):
    """Tracks relationship state between player and a character"""
    character_name: str
    strength: int = Field(default=50, ge=0, le=100)  # 0-100 scale
    level: RelationshipLevel = RelationshipLevel.FRIEND
    
    # History tracking
    interactions_count: int = 0
    last_interaction: Optional[datetime] = None
    sentiment_history: List[float] = Field(default_factory=list)  # Recent sentiment scores
    
    # Relationship evolution
    total_positive_interactions: int = 0
    total_negative_interactions: int = 0
    
    def update_strength(self, sentiment_delta: float) -> None:
        """Update relationship strength based on sentiment"""
        self.strength = max(0, min(100, self.strength + sentiment_delta))
        self.interactions_count += 1
        self.last_interaction = datetime.now()
        
        # Track sentiment history (keep last 10)
        self.sentiment_history.append(sentiment_delta)
        if len(self.sentiment_history) > 10:
            self.sentiment_history.pop(0)
        
        # Track positive/negative
        if sentiment_delta > 0:
            self.total_positive_interactions += 1
        elif sentiment_delta < 0:
            self.total_negative_interactions += 1
        
        # Update relationship level
        self._update_level()
    
    def _update_level(self) -> None:
        """Update relationship level based on strength"""
        if self.strength >= 81:
            self.level = RelationshipLevel.BEST_FRIEND
        elif self.strength >= 61:
            self.level = RelationshipLevel.CLOSE_FRIEND
        elif self.strength >= 41:
            self.level = RelationshipLevel.FRIEND
        elif self.strength >= 21:
            self.level = RelationshipLevel.ACQUAINTANCE
        else:
            self.level = RelationshipLevel.STRANGER


class Character(BaseModel):
    """
    Represents a character in the game, generated from real contacts.
    Contains AI-generated personality and message history context.
    
    Can use either basic or enhanced memory system.
    """
    # Identity
    name: str
    contact_id: str  # Maps to contact in data folder
    
    # PERSONALITY (brief, not complex)
    personality_brief: str  # One paragraph about who they are
    relationship_context: str  # One paragraph about your history
    
    # THE KEY: ACTUAL MESSAGE EXAMPLES
    message_examples: List[Dict] = Field(default_factory=list)  # 30-50 real messages
    
    # DYNAMIC STATE (simple)
    current_mood: str = "neutral"
    recent_conversation_topics: List[str] = Field(default_factory=list)
    
    # Relationship with player
    relationship: Relationship
    
    # Context from real messages
    message_count: int = 0
    conversation_llm_path: Optional[str] = None  # Path to conversation_llm.json
    
    # Game state
    current_location: Optional[str] = None  # Place name
    available_for_conversation: bool = True
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    
    def get_relationship_description(self) -> str:
        """Get human-readable relationship description"""
        return f"{self.relationship.level.value.replace('_', ' ').title()} ({self.relationship.strength}/100)"
    
    def get_message_examples_text(self, max_examples: Optional[int] = None) -> str:
        """Format message examples for LLM prompt"""
        if not self.message_examples:
            return "No message examples available."
        
        # Use all messages if max_examples not specified
        examples_to_show = self.message_examples if max_examples is None else self.message_examples[:max_examples]
        
        formatted = []
        for i, msg in enumerate(examples_to_show, 1):
            sender = "YOU" if msg.get('sender') == 'contact' else "ARMAN"
            content = msg.get('content', '').strip()
            if content:
                # Truncate very long messages for readability
                if len(content) > 300:
                    content = content[:297] + "..."
                formatted.append(f"--- EXAMPLE {i} ---\n{sender}: \"{content}\"")
        
        return "\n\n".join(formatted)


# ============================================================================
# CONVERSATION MODELS
# ============================================================================

class Message(BaseModel):
    """A single message in a conversation"""
    speaker: str  # 'player' or character name
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    sentiment_score: Optional[float] = None  # -1.0 to 1.0


class Conversation(BaseModel):
    """Tracks an ongoing conversation with a character"""
    character_name: str
    messages: List[Message] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    
    # Conversation analytics
    total_sentiment_delta: float = 0.0  # Cumulative effect on relationship
    turns_count: int = 0
    
    def add_message(self, speaker: str, content: str, sentiment: Optional[float] = None) -> Message:
        """Add a message to the conversation"""
        msg = Message(speaker=speaker, content=content, sentiment_score=sentiment)
        self.messages.append(msg)
        
        if speaker == "player" and sentiment is not None:
            self.total_sentiment_delta += sentiment
        
        self.turns_count += 1
        return msg
    
    def end_conversation(self) -> None:
        """Mark conversation as ended"""
        self.ended_at = datetime.now()


# ============================================================================
# PLACE & LOCATION MODELS
# ============================================================================

class Place(BaseModel):
    """
    Represents a physical location in the player's world.
    Based on real places mentioned in messages or inferred.
    """
    name: str
    description: str
    
    # Geography (simplified for V1)
    distance_from_home: float = 0.0  # Miles
    travel_time: int = 0  # Minutes
    travel_cost: float = 0.0  # Dollars
    
    # Characters who frequent this place
    typical_characters: List[str] = Field(default_factory=list)
    
    # Discovery
    discovered: bool = False
    visit_count: int = 0
    first_visited: Optional[datetime] = None
    
    # Metadata
    place_type: str = "generic"  # home, coffee_shop, gym, campus, etc.


# ============================================================================
# QUEST MODELS
# ============================================================================

class Quest(BaseModel):
    """
    Represents a quest/objective in the game.
    Quests emerge from relationship states and player choices.
    """
    id: str
    title: str
    description: str
    quest_type: QuestType
    
    # Status
    status: QuestStatus = QuestStatus.AVAILABLE
    
    # Requirements & Rewards
    required_location: Optional[str] = None
    required_character: Optional[str] = None
    time_cost: int = 60  # Minutes
    energy_cost: int = 10
    money_cost: float = 0.0
    
    # Rewards
    relationship_reward: Dict[str, int] = Field(default_factory=dict)  # character_name -> points
    money_reward: float = 0.0
    energy_reward: int = 0
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress
    objectives: List[str] = Field(default_factory=list)
    objectives_completed: List[bool] = Field(default_factory=list)
    
    def is_available(self) -> bool:
        """Check if quest can be started"""
        return self.status == QuestStatus.AVAILABLE
    
    def is_expired(self) -> bool:
        """Check if quest has expired"""
        if self.expires_at and datetime.now() > self.expires_at:
            return True
        return False
    
    def complete_objective(self, index: int) -> bool:
        """Mark an objective as complete"""
        if 0 <= index < len(self.objectives_completed):
            self.objectives_completed[index] = True
            
            # Check if all objectives done
            if all(self.objectives_completed):
                self.status = QuestStatus.COMPLETED
                self.completed_at = datetime.now()
                return True
        return False


# ============================================================================
# RESOURCE MODELS
# ============================================================================

class Resources(BaseModel):
    """
    Tracks player resources (money, time, energy).
    Resources gate certain actions and create interesting choices.
    """
    money: float = 100.0  # Starting money
    energy: int = Field(default=100, ge=0, le=100)  # 0-100
    
    # Time tracking (simplified for V1)
    current_day: int = 1
    current_hour: int = 9  # 9 AM start
    
    # Statistics
    total_money_earned: float = 0.0
    total_money_spent: float = 0.0
    
    def can_afford(self, money_cost: float, energy_cost: int, time_cost_minutes: int) -> bool:
        """Check if player can afford an action"""
        if self.money < money_cost:
            return False
        if self.energy < energy_cost:
            return False
        # For V1, simplified time check (just has hours in day)
        hours_available = 24 - self.current_hour
        if time_cost_minutes / 60 > hours_available:
            return False
        return True
    
    def spend(self, money: float = 0.0, energy: int = 0, time_minutes: int = 0) -> None:
        """Spend resources"""
        self.money -= money
        self.energy = max(0, self.energy - energy)
        self.total_money_spent += money
        
        # Advance time
        self.current_hour += time_minutes // 60
        if self.current_hour >= 24:
            self.current_day += 1
            self.current_hour = self.current_hour % 24
    
    def earn_money(self, amount: float) -> None:
        """Earn money"""
        self.money += amount
        self.total_money_earned += amount
    
    def restore_energy(self, amount: int) -> None:
        """Restore energy"""
        self.energy = min(100, self.energy + amount)
    
    def get_time_string(self) -> str:
        """Get formatted time string"""
        period = "AM" if self.current_hour < 12 else "PM"
        hour_12 = self.current_hour if self.current_hour <= 12 else self.current_hour - 12
        if hour_12 == 0:
            hour_12 = 12
        return f"Day {self.current_day}, {hour_12}:00 {period}"


# ============================================================================
# GAME STATE MODEL
# ============================================================================

class GameState(BaseModel):
    """
    Root game state model that contains everything.
    This is what gets serialized for save/load.
    """
    # Player info
    player_name: str = "Player"
    
    # Game entities
    characters: Dict[str, Character] = Field(default_factory=dict)  # name -> Character
    places: Dict[str, Place] = Field(default_factory=dict)  # name -> Place
    quests: Dict[str, Quest] = Field(default_factory=dict)  # id -> Quest
    
    # Current state
    current_location: str = "Home"
    current_conversation: Optional[Conversation] = None
    resources: Resources = Field(default_factory=Resources)
    
    # History
    conversation_history: List[Conversation] = Field(default_factory=list)
    completed_quests: List[str] = Field(default_factory=list)  # Quest IDs
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_played: datetime = Field(default_factory=datetime.now)
    total_play_time_minutes: int = 0
    
    # Game progression
    days_survived: int = 1
    total_conversations: int = 0
    total_decisions_made: int = 0
    
    def add_character(self, character: Character) -> None:
        """Add a character to the game"""
        self.characters[character.name] = character
    
    def get_character(self, name: str) -> Optional[Character]:
        """Get a character by name"""
        return self.characters.get(name)
    
    def add_place(self, place: Place) -> None:
        """Add a place to the game"""
        self.places[place.name] = place
    
    def get_place(self, name: str) -> Optional[Place]:
        """Get a place by name"""
        return self.places.get(name)
    
    def add_quest(self, quest: Quest) -> None:
        """Add a quest to the game"""
        self.quests[quest.id] = quest
    
    def get_active_quests(self) -> List[Quest]:
        """Get all active quests"""
        return [q for q in self.quests.values() if q.status == QuestStatus.ACTIVE]
    
    def get_available_quests(self) -> List[Quest]:
        """Get all available quests"""
        return [q for q in self.quests.values() if q.status == QuestStatus.AVAILABLE and not q.is_expired()]
    
    def start_conversation(self, character_name: str) -> Conversation:
        """Start a conversation with a character"""
        self.current_conversation = Conversation(character_name=character_name)
        return self.current_conversation
    
    def end_current_conversation(self) -> None:
        """End the current conversation"""
        if self.current_conversation:
            self.current_conversation.end_conversation()
            self.conversation_history.append(self.current_conversation)
            self.total_conversations += 1
            self.current_conversation = None
    
    def update_last_played(self) -> None:
        """Update last played timestamp"""
        self.last_played = datetime.now()
    
    def get_summary(self) -> str:
        """Get a summary of the current game state"""
        return f"""
=== GAME STATE SUMMARY ===
Player: {self.player_name}
Location: {self.current_location}
Day {self.resources.current_day}, {self.resources.get_time_string()}

Resources:
- Money: ${self.resources.money:.2f}
- Energy: {self.resources.energy}/100

Characters: {len(self.characters)}
Active Quests: {len(self.get_active_quests())}
Conversations: {self.total_conversations}
Days Played: {self.days_survived}
"""

