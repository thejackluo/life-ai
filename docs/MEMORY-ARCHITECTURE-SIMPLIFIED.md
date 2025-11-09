# Life AI: Simplified Memory Architecture
**Analyst:** Mary (Business Analyst)  
**Date:** November 9, 2025  
**Version:** 2.1 - SIMPLIFIED & FOCUSED ON EVOLUTION

---

## Core Concept

**Three simple layers:**
1. **Deep Profile** - Who they are + your history (generated once)
2. **Living State** - How they feel NOW (changes every conversation)
3. **Evolution** - How they've changed through gameplay (grows over time)

**Focus:** Less on categorizing memories, more on **characters that change and grow**.

---

## Layer 1: Deep Profile (Static Background)

**Generated once from message analysis. Gives AI rich context.**

```python
class DeepProfile(BaseModel):
    """
    Everything about this person from your real message history.
    ~2000 words of LLM-generated analysis.
    """
    
    # PERSONALITY (500 words)
    personality_analysis: str
    # "Mom is highly conscientious and caring. She shows love through
    # practical support - asking about appointments, offering help with
    # tasks, coordinating family events. She's bilingual (English/Farsi),
    # tends to worry about family safety, expresses pride in your
    # accomplishments. Communication is warm but can be anxious when
    # concerned about wellbeing..."
    
    # YOUR HISTORY (500 words)
    relationship_history: str
    # "You've been texting for 500+ days. Pattern: mostly practical
    # coordination mixed with caring check-ins. Notable moments include:
    # - Emotional apology about Kamrad situation (showed vulnerability)
    # - Father's Day planning together
    # - Ryan's birthday coordination
    # - Medical advice exchanges (trusts you with family health)
    # Relationship has maintained stable caring dynamic with periodic
    # deeper emotional moments..."
    
    # KEY MEMORIES (5-10 rough groupings, NOT hyper-specific)
    key_moments: List[MemoryCluster]
    # Examples:
    # - "Family celebrations and planning (multiple events)"
    # - "Health and safety moments (burns, doctor visits)"
    # - "Emotional vulnerability (apology conversation)"
    # - "Daily life coordination (groceries, schedules, money)"
    
    # PEOPLE & CONTEXT (200 words)
    important_people: str  # "Ryan (brother), Dad, Kamrad, Eunis, Neda, Roza..."
    topics_discussed: str  # "family events, health, household tasks, finances..."
    inside_language: str  # "Uses Farsi phrases, specific family terms..."
    
    # HOW THEY RELATE TO YOU (300 words)
    support_style: str  # How they help you
    communication_baseline: str  # Their normal texting style
    emotional_baseline: str  # Their default mood with you
    
    # METADATA
    based_on_messages: int
    time_span: str  # "June 2024 - October 2025"
    generated_at: datetime


class MemoryCluster(BaseModel):
    """
    A ROUGH grouping of similar memories.
    Not specific - just thematic clusters.
    """
    theme: str  # "Family celebrations", "Health concerns", "Conflicts"
    timeframe: str  # "Summer 2024", "Fall 2024" - rough
    description: str  # General description of what happened
    examples: List[str]  # 2-3 specific quotes from messages
    emotional_tone: str  # "happy", "tense", "caring", "everyday"
```

**Generation Time:** ~30-45 seconds, ~$0.10-0.15  
**Output:** ~2000 words of rich context

---

## Layer 2: Living State (Dynamic Current State)

**Changes after EVERY conversation. Represents how they feel NOW.**

```python
class LivingState(BaseModel):
    """
    Current state - how the character feels and behaves RIGHT NOW.
    """
    
    # CURRENT MOOD
    mood: str  # "happy", "sad", "worried", "excited", "neutral", "distant"
    mood_intensity: float = Field(ge=0.0, le=1.0)
    why_this_mood: str  # Brief explanation
    
    # EMOTIONAL STATE TOWARD PLAYER
    current_feeling: str  # "close", "distant", "hurt", "grateful", "curious"
    openness: float = Field(ge=0.0, le=1.0)  # How open they are right now
    trust: float = Field(ge=0.0, le=1.0)  # Current trust level
    
    # RECENT MEMORY (last 3-5 conversations)
    recent_topics: List[str]  # Simple list
    last_conversation_summary: str  # One sentence
    unfinished_business: List[str]  # Things left hanging
    
    # CURRENT EXPECTATIONS
    what_they_want_to_talk_about: List[str]
    questions_for_player: List[str]
    concerns: List[str]
    
    # BEHAVIOR MODIFIERS (how they're acting different from baseline)
    acting_more: List[str]  # "guarded", "playful", "serious", "caring"
    acting_less: List[str]  # "open", "responsive", "warm"
    
    # TEMPORAL
    last_updated: datetime
    conversations_since_baseline: int
```

**How it updates:**

```python
def update_living_state(character, conversation, sentiment_delta):
    """
    After each conversation, LLM analyzes how character's state should change.
    
    Prompt:
    "Based on this conversation, how does {name}'s current emotional state
    change? Consider:
    - What was said (sentiment: {delta})
    - How they felt before (current mood: {mood})
    - Their baseline personality
    - Relationship history
    
    Update: mood, openness, trust, behavior modifiers, what they're thinking"
    
    Fast LLM call (~5 seconds, $0.02)
    """
```

---

## Layer 3: Evolution (Progression Arc)

**Tracks the character's journey through the game.**

```python
class RelationshipEvolution(BaseModel):
    """
    How the character has evolved since game started.
    """
    
    # BASELINE (where they started)
    starting_strength: int
    starting_personality: str  # Snapshot at game start
    game_started: datetime
    
    # PROGRESSION
    conversations_had: int = 0
    total_positive_interactions: int = 0
    total_negative_interactions: int = 0
    
    # CHANGES OVER TIME
    personality_shifts: List[EvolutionEvent]
    # Example:
    # "Day 3: Became more open after 3 positive conversations"
    # "Day 7: Became guarded after argument"
    # "Day 10: Trust deepened after vulnerability shared"
    
    gameplay_memories: List[GameMemory]
    # New memories created in-game (not from message history)
    
    # TRAJECTORY
    sentiment_graph: List[Tuple[int, float]]  # (day, strength) for graphing
    current_arc: str  # "growing closer", "drifting apart", "stable", "recovering"
    
    # NEXT EVOLUTION
    evolution_points_earned: int = 0
    next_evolution_threshold: int = 100
    potential_next_shift: str  # What might change next


class EvolutionEvent(BaseModel):
    """A moment when character evolved"""
    day: int  # Game day
    trigger: str  # What caused it
    change: str  # What changed
    impact: str  # How it affects future interactions


class GameMemory(BaseModel):
    """Something that happened during gameplay"""
    day: int
    what_happened: str
    category: str  # "bonding", "conflict", "fun", "deep" - simple
    affects_future: bool  # Will this come up in future conversations?
```

---

## Simplified Implementation Plan

### Phase 1: Deep Profile Generation (4-5 hours)

**Build:**
```
src/core/memory_models.py
  - DeepProfile
  - MemoryCluster
  
src/game/memory/
  - profile_generator.py
    → generate_deep_profile(messages) -> DeepProfile
```

**LLM Prompt Strategy:**

```
ONE comprehensive prompt instead of 5-7 separate calls.

"Analyze these {N} messages and create a comprehensive character profile.

Include:

1. PERSONALITY ANALYSIS (500 words)
   - Core traits and patterns
   - Communication style
   - Emotional patterns
   
2. RELATIONSHIP HISTORY (500 words)
   - How your relationship has evolved
   - Typical interaction patterns
   - Overall dynamic
   
3. KEY MEMORY CLUSTERS (5-10 rough groupings)
   - Group similar events/moments into themes
   - Don't be hyper-specific, just capture general areas
   - Example: 'Family celebrations' not 'Ryan's birthday June 24 2024'
   
4. PEOPLE & CONTEXT (200 words)
   - Who they mention, topics discussed, special language
   
5. SUPPORT STYLE (200 words)
   - How they help, celebrate, handle conflict

Return as structured JSON."
```

**Result:** 2000 word profile, one LLM call, ~40 seconds, ~$0.15

---

### Phase 2: Living State System (3-4 hours)

**Build:**
```
src/core/memory_models.py
  - LivingState
  
src/game/memory/
  - state_manager.py
    → update_state_after_conversation()
    → get_current_state_context()
```

**After each conversation:**

```python
def update_living_state(character, conversation):
    """
    Quick LLM call to update how character feels NOW.
    
    Prompt:
    "Character {name} just had this conversation with player:
    {conversation_summary}
    
    Sentiment: {delta}
    Previous mood: {current_mood}
    Baseline personality: {brief_summary}
    
    How does their emotional state change?
    Update: mood, openness, trust, behavior shifts, what they're thinking
    
    Keep it simple and natural."
    
    Fast call: ~5 seconds, ~$0.02
    """
```

---

### Phase 3: Evolution Tracking (3-4 hours)

**Build:**
```
src/core/memory_models.py
  - RelationshipEvolution
  - EvolutionEvent
  - GameMemory
  
src/game/memory/
  - evolution_tracker.py
    → record_conversation()
    → check_for_evolution()
    → generate_evolution_event()
```

**Evolution Check (every 5-10 conversations):**

```python
def check_for_evolution(character):
    """
    Periodically check if character should evolve.
    
    Checks:
    - Has relationship strength changed significantly? (+/-20)
    - Have we had a major emotional moment?
    - Has player's behavior pattern shifted?
    
    If yes:
      → LLM generates evolution event
      → Character personality shifts slightly
      → New behavioral patterns emerge
    """
```

---

## Integration with Conversations

### Before Enhancement:
```python
def generate_response(character, player_msg):
    context = f"""
    Personality: {character.personality_summary}
    Style: {character.communication_style}
    Relationship: {character.relationship.level}
    """
    # ~100 words context
```

### After Enhancement:
```python
def generate_response(character, player_msg):
    context = f"""
    DEEP PROFILE:
    {character.deep_profile.personality_analysis[:500]}
    
    HISTORY:
    {character.deep_profile.relationship_history[:300]}
    
    RELEVANT MEMORIES:
    {get_relevant_clusters(character, player_msg)}
    
    CURRENT STATE:
    Mood: {character.living_state.mood} - {character.living_state.why_this_mood}
    Feeling toward you: {character.living_state.current_feeling}
    Openness: {character.living_state.openness}
    Recent topics: {character.living_state.recent_topics}
    
    EVOLUTION:
    Recent changes: {character.evolution.personality_shifts[-3:]}
    Current arc: {character.evolution.current_arc}
    """
    # ~800-1000 words context, highly relevant
```

---

## Example: Character Evolution in Action

### Mom - Gameplay Scenario

**Game Start (Day 1):**
```python
Deep Profile:
  personality: "Caring, organized, shows love through practical help..."
  history: "500 days of texts, mix of coordination and emotional moments..."
  key_moments: ["Family celebrations", "Health concerns", "Vulnerability"]

Living State:
  mood: "warm and caring"
  openness: 0.8
  current_feeling: "loving"
  
Evolution:
  starting_strength: 75
  personality_shifts: []
```

**Conversation 1 - You're loving and appreciative:**
```
You: "Hey Mom, I really appreciate everything you do for me. You're amazing."
Sentiment: +16.8

→ Living State updates:
  mood: "touched and proud"
  openness: 0.9 (increased)
  current_feeling: "deeply loved"
  recent_topics: ["appreciation", "gratitude"]

→ Mom's response:
  "Oh azizam, you're going to make me cry! That means the world to me. 
   I'm so proud of you. How are you doing, sweetheart?"
  
  [Uses Farsi term, emotional, asks caring question - matches BOTH
   deep profile AND current elevated emotional state]
```

**Conversation 5 - After multiple deep talks:**
```
Evolution Check triggered!

→ Evolution Event generated:
  type: "TRUST DEEPENED"
  description: "Arman has been really opening up lately"
  personality_shift: "More comfortable being vulnerable herself"
  
→ Living State:
  openness: 0.95 (very open now)
  behavior: acting_more: ["emotionally expressive", "sharing feelings"]
  
→ Future conversations:
  Mom now shares MORE personal things, reciprocates vulnerability
```

**Conversation 8 - You're short and cold:**
```
You: "fine"
Sentiment: -4.2

→ Living State updates:
  mood: "concerned, confused"
  openness: 0.75 (decreased)
  current_feeling: "worried something's wrong"
  concerns: ["Is Arman okay?", "Did I do something?"]
  
→ Mom's response:
  "Is everything alright? You seem different. I'm here if you want to talk."
  
  [She NOTICES the change because LivingState tracks mood and openness]
```

**Conversation 10 - You apologize:**
```
You: "Sorry I was cold earlier, I was just stressed. I love you Mom."
Sentiment: +15.3

→ Evolution Check triggered!

→ Milestone created:
  type: "RESILIENCE_TESTED"
  description: "Worked through moment of tension, relationship stronger"
  
→ Evolution Event:
  personality_shift: "More resilient, knows relationship can handle ups/downs"
  new_depth: "Trusts Arman will communicate when ready"
  
→ Living State:
  mood: "relieved and loving"
  openness: back to 0.9
  gameplay_memory: "We worked through that, I'm glad we can be honest"
```

---

## Implementation: Simplified Approach

### Data Models (NEW FILE: src/core/memory_models.py)

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class MemoryCluster(BaseModel):
    """Rough grouping of similar memories - NOT hyper-specific"""
    theme: str  # "family events", "deep talks", "everyday coordination"
    timeframe: str  # "Summer 2024", "Early days" - rough
    description: str  # What generally happened in these moments
    examples: List[str]  # 2-3 actual quotes
    mood: str  # Overall emotional tone


class DeepProfile(BaseModel):
    """Static background - who they are and your history"""
    personality_analysis: str  # 500 words
    relationship_history: str  # 500 words
    key_moments: List[MemoryCluster]  # 5-10 clusters
    important_people: str  # 200 words
    topics_discussed: str  # List of major topics
    inside_language: str  # Special phrases, language quirks
    support_style: str  # How they help/care
    communication_baseline: str  # Normal style
    emotional_baseline: str  # Default mood
    based_on_messages: int
    generated_at: datetime


class LivingState(BaseModel):
    """Current state - changes every conversation"""
    # EMOTIONAL STATE
    mood: str
    mood_intensity: float = 0.5
    why_this_mood: str
    
    # FEELINGS TOWARD PLAYER
    current_feeling: str
    openness: float = 0.7
    trust: float = 0.7
    
    # RECENT CONTEXT
    recent_topics: List[str] = Field(default_factory=list)
    last_talked: str = "Just started playing"
    unfinished: List[str] = Field(default_factory=list)
    
    # CURRENT BEHAVIOR
    acting_more: List[str] = Field(default_factory=list)  # Different from baseline
    acting_less: List[str] = Field(default_factory=list)
    
    # THOUGHTS
    concerns: List[str] = Field(default_factory=list)
    wants_to_ask: List[str] = Field(default_factory=list)
    
    # TRACKING
    last_updated: datetime = Field(default_factory=datetime.now)
    version: int = 0


class EvolutionEvent(BaseModel):
    """A moment when character evolved"""
    game_day: int
    trigger: str  # What caused evolution
    change: str  # What changed in personality/behavior
    significance: str  # "minor", "moderate", "major"


class GameMemory(BaseModel):
    """Something that happened during gameplay"""
    game_day: int
    description: str
    category: str  # "bonding", "conflict", "fun", "deep" - simple
    emotional_weight: float


class RelationshipEvolution(BaseModel):
    """How relationship has changed through gameplay"""
    starting_strength: int
    starting_date: datetime
    
    # PROGRESSION
    conversations_had: int = 0
    positive_interactions: int = 0
    negative_interactions: int = 0
    
    # EVOLUTION
    personality_shifts: List[EvolutionEvent] = Field(default_factory=list)
    gameplay_memories: List[GameMemory] = Field(default_factory=list)
    
    # TRAJECTORY
    sentiment_history: List[Tuple[int, float]] = Field(default_factory=list)
    current_arc: str = "beginning"  # "growing", "stable", "declining", "recovering"
    
    # NEXT EVOLUTION
    evolution_points: int = 0  # Accumulate through interactions
    next_threshold: int = 100  # When next evolution triggers
```

---

## The Magic: How It All Works Together

### Conversation Flow (Enhanced)

```python
def have_conversation(game_state, character):
    """Enhanced conversation with all 3 layers"""
    
    # 1. DISPLAY CURRENT STATE
    print(f"💚 Conversation with {character.name}")
    print(f"Relationship: {character.relationship.strength}/100")
    print(f"Mood: {character.living_state.mood} ({character.living_state.why_this_mood})")
    print(f"Feeling: {character.living_state.current_feeling}")
    
    # 2. GENERATE RESPONSE WITH FULL CONTEXT
    context = build_rich_context(character, player_message)
    # Includes: deep_profile + living_state + recent evolution
    
    response = generate_with_llm(context, player_message)
    
    # 3. UPDATE LIVING STATE (after each message)
    character.living_state = update_state(character, player_message, sentiment)
    
    # 4. CHECK FOR EVOLUTION (every N conversations or big moments)
    if should_check_evolution(character):
        evolution_event = check_evolution(character)
        if evolution_event:
            character.evolution.personality_shifts.append(evolution_event)
            # Character has PERMANENTLY changed!
```

### Example Flow:

**Turn 1:**
```
Player: "I love you Mom"
Sentiment: +17.2

Living State update:
  mood: "warm" → "deeply touched"
  openness: 0.8 → 0.9
  current_feeling: "loving" → "emotionally connected"
  
Response uses this new state:
  "Oh sweetheart, I love you so much too! (heart) You made my day."
```

**Turn 2 (same conversation):**
```
Player: "I've been meaning to tell you how much I appreciate you"
Sentiment: +15.6

Living State update:
  mood: "deeply touched" → "overwhelmed with love"
  openness: 0.9 → 0.95
  evolution_points: +20 (big positive moment)
  
Response reflects elevated state:
  "Arman azizam, you're going to make me cry! I needed to hear that.
   You know I'm always here for you, right? Always."
   
[More emotional, more vulnerable than her baseline because
 current state is emotionally heightened]
```

**Turn 10 (different conversation, days later):**
```
Player: "whatever"
Sentiment: -3.1

Living State update:
  mood: "warm" → "confused and worried"
  openness: 0.85 → 0.7
  concerns: ["Is something wrong?", "Did I upset him?"]
  
Response reflects concern:
  "Is everything okay? You seem upset. Do you want to talk about it?"
  
[She NOTICED the tone shift because LivingState tracks and reacts]
```

---

## Cost & Time Analysis (Simplified)

### Per Character Generation:
```
Deep Profile: 1 LLM call, 30-45 sec, $0.10-0.15
Living State: Initialized from Deep Profile (no cost)
Evolution: Starts empty

Total: ~45 seconds, ~$0.15 per character
For 8 characters: ~6 minutes, ~$1.20
```

### During Gameplay:
```
Per conversation:
- Main response: existing cost
- State update: +$0.02, +3 seconds
- Evolution check (every 5 convos): +$0.03, +5 seconds

Marginal cost: ~2-5 cents per conversation, 3-5 seconds
```

**Much simpler than before!**

---

## Revised Questions for You:

**1. Does this simplified 3-layer approach feel right?**
   - Deep Profile (static)
   - Living State (changes every conversation)
   - Evolution (progression over time)

**2. Should I start building this now?**
   - Deep Profile generator first (prove it works)
   - Then add Living State + Evolution
   - Test with Mom first

**3. How much detail in Deep Profile?**
   - 2000 words? (comprehensive)
   - 1000 words? (focused)
   - 500 words? (concise)

**What do you think, Arman? Ready to build this simpler, more focused system?** 🚀
