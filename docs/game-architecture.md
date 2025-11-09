# Life AI - Game Architecture Document
**Project:** Life AI Hackathon MVP  
**Date:** November 9, 2025  
**Timeline:** 8-hour sprint (until 9 AM)  
**Architect:** Cloud Dragonborn  
**Developer:** arman

---

## Executive Summary

Life AI is a **production-ready** terminal-based Python application that transforms real message history into playable characters within a life simulation game. Users export their full message history (hundreds of contacts, thousands of messages), select which contacts to generate as characters, and engage in free-form conversations that affect relationship dynamics. The architecture leverages existing message export tooling (`contacts_exporter.py`), OpenAI API for authentic character responses, file-based state management for simplicity, and sentiment analysis for dynamic relationship evolution.

---

## Decision Summary

| Category | Decision | Version | Rationale |
| -------- | -------- | ------- | --------- |
| Language | Python | 3.11+ | Rapid development, excellent LLM libraries |
| LLM Provider | OpenAI API | gpt-4o/gpt-4-turbo | 128k context window, reliability, Jack's credits available |
| LLM Library | openai | 1.x (latest) | Official SDK, async support |
| State Management | JSON Files | - | Simple, inspectable, no DB setup time |
| Data Validation | Pydantic | 2.x | Type safety, validation, serialization |
| Interface | Terminal/CLI | - | Production-ready, focus on core mechanics, accessible |
| Message Export | contacts_exporter.py | Existing | Already handles export, filtering, consolidation |
| Message Format | JSON + TXT | - | Structured data + readable conversation files |
| Conversation Mode | Free-Form Text | - | User types anything, like real messaging |
| Sentiment Analysis | TextBlob/VADER | Latest | Real-time relationship impact from conversation |
| Project Structure | Modular Python | - | Clear separation of concerns, parallel dev |

---

## Project Structure

```
life-ai/
├── main.py                    # Entry point - game initialization and main loop
├── contacts_exporter.py       # EXISTING: Message & contact export tool
├── llm_processor.py           # EXISTING: LLM data processing (dependency of contacts_exporter)
├── .env                       # API keys (OPENAI_API_KEY)
├── .gitignore                 # Exclude .env, data/, saves/, __pycache__
├── requirements.txt           # Dependencies
│
├── src/
│   ├── __init__.py
│   ├── models.py              # Data models (Character, Quest, GameState, Player)
│   ├── llm.py                 # OpenAI integration wrapper
│   ├── game_engine.py         # Core game loop and state management
│   ├── character_gen.py       # contact.json + messages → Character profile
│   ├── character_selector.py  # UI for selecting contacts to generate characters from
│   ├── quest_system.py        # Quest generation and management
│   ├── conversation.py        # Free-form character dialogue system
│   ├── sentiment.py           # Sentiment analysis for relationship dynamics
│   ├── resource_manager.py    # Money, time, energy tracking
│   ├── save_load.py           # JSON persistence layer
│   └── cli.py                 # Terminal UI helpers and commands
│
├── data/                      # Output from contacts_exporter.py (gitignored)
│   ├── [ContactName]/
│   │   ├── contact.json       # Contact info + conversation metadata
│   │   ├── messages_consolidated.txt  # All messages in timeline
│   │   └── conversation_llm.json      # LLM-ready format
│   ├── _summary/
│   │   ├── all_contacts.json
│   │   └── contacts_with_messages.json
│   └── _llm_ready/
│       └── master_index.json  # Index of all conversations
│
├── characters/                # Generated character profiles
│   ├── charles.json
│   ├── ryan.json
│   └── ...
│
├── saves/                     # Game save files (gitignored)
│   ├── save_001.json
│   └── ...
│
└── docs/
    ├── bmm-brainstorming-session-2025-11-09.md
    ├── game-architecture.md (this file)
    └── demo-story.md
```

---

## Technology Stack Details

### Core Technologies

**Python 3.11+**
- Modern type hints support
- Performance improvements
- Standard library enhancements

**OpenAI Python SDK (1.x)**
```bash
pip install openai
```
- Async API support
- Streaming responses (optional enhancement)
- Function calling capability (for structured outputs)

**Pydantic 2.x**
```bash
pip install pydantic
```
- Data validation
- JSON serialization/deserialization
- Type safety

**python-dotenv**
```bash
pip install python-dotenv
```
- Environment variable management
- API key security

**vaderSentiment** (or TextBlob)
```bash
pip install vaderSentiment
```
- Real-time sentiment analysis of player input
- Determines relationship impact of conversations
- Fast, rule-based (no ML model needed)

**Additional (for contacts_exporter.py)**
```bash
pip install vobject dateutil emoji
```
- Already configured in existing tool
- Handles VCF parsing and message processing

### Dependencies (requirements.txt)
```
openai>=1.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
vaderSentiment>=3.3.2
vobject>=0.9.6
python-dateutil>=2.8.2
emoji>=2.0.0
```

---

## Data Models

### Character Model
```python
from pydantic import BaseModel
from typing import List, Optional

class Character(BaseModel):
    id: str                          # Unique identifier
    name: str                        # Display name
    personality: str                 # Core personality traits
    speaking_style: str              # How they communicate
    interests: List[str]             # Topics they care about
    relationship_to_player: str      # Nature of relationship
    relationship_strength: int       # 0-100 score
    last_real_contact: str           # ISO date string
    message_history_path: str        # Path to message JSON
    memorable_exchanges: List[str]   # Key conversation snippets
    
    # In-game dynamic state
    current_location: Optional[str] = "unknown"
    conversation_history: List[dict] = []  # In-game dialogue
```

### Quest Model
```python
class Quest(BaseModel):
    id: str
    title: str
    description: str
    character_ids: List[str]         # Characters involved
    location: Optional[str]
    objectives: List[str]            # Task list
    rewards: dict                    # {"relationship": +15, "money": -8}
    penalties: Optional[dict]
    status: str                      # "active", "completed", "failed"
    time_limit: Optional[int]        # Hours
```

### Player Model
```python
class Player(BaseModel):
    money: float = 100.0
    time_hours: int = 8              # Hours remaining today
    energy: int = 100                # 0-100
    current_location: str = "home"
```

### GameState Model
```python
class GameState(BaseModel):
    player: Player
    characters: List[Character]
    active_quests: List[Quest]
    completed_quests: List[Quest]
    failed_quests: List[Quest]
    relationships: dict[str, int]    # character_id -> strength
    game_time: dict                  # Day, hour tracking
    conversation_log: List[dict]     # Full conversation history
```

---

## User Flow (Production Software)

### First-Time User Setup

**Step 1: Message Export (One-Time)**
```bash
# User runs existing contacts_exporter.py
python contacts_exporter.py --min-messages 100

# This processes:
# - Exports full iMessage database
# - Reads Apple Contacts VCF file
# - Filters contacts with 100+ messages
# - Creates data/ folder with all contacts
# - Generates conversation metadata
```

**Output:**
- `data/` folder with 50-200 contacts (typical user)
- Each contact has: `contact.json`, `messages_consolidated.txt`, `conversation_llm.json`
- `data/_summary/contacts_with_messages.json` - Master list

**Step 2: Character Selection**
```bash
# User launches Life AI
python main.py

# Game prompts:
"Welcome to Life AI! Found 127 contacts with message history.
 Select up to 10 contacts to generate as characters."

# Shows ranked list:
1. Charles - 2,847 messages (last: 2 days ago)
2. Ryan - 1,523 messages (last: 1 week ago)  
3. Sarah - 892 messages (last: 3 weeks ago)
...

Enter numbers (comma-separated): 1,2,3
```

**Step 3: Character Generation**
```
Generating character: Charles...
- Loading message history (2,847 messages)
- Analyzing personality and speaking style...
- Extracting interests and relationship dynamics...
✓ Charles generated! (Relationship: 87/100 - Close Friend)

Generating character: Ryan...
...
```

**Step 4: Game Begins**
```
═══════════════════════════════════════
         LIFE AI - Your Life, Gamified
═══════════════════════════════════════

You wake up at home. Morning light streams in.

Characters available: Charles, Ryan, Sarah
Active quests: 2
```

### Ongoing Gameplay

**Free-Form Conversation:**
```
> talk charles

You call Charles...

CHARLES: "yo what's up man"

You: _
> I've been thinking about that startup idea we discussed

CHARLES: "oh yeah? the one about the ai messaging thing? 
         that's actually fire bro. you should go for it"

[Relationship: Charles +2 (supportive response)]

You: _
> honestly I'm kinda scared to fail

CHARLES: "dude everyone fails at first. you know how many 
         times i tried shit before anything worked? just build it"

[Relationship: Charles +3 (encouraging, authentic)]
```

**Relationship Impact:**
- Positive/supportive → relationship increases
- Negative/hurtful → relationship decreases  
- Authentic conversation → stronger bonds
- Ignoring character over time → relationship decay

---

## Core Systems Architecture

### 1. Message Export (EXISTING - contacts_exporter.py)

**Status:** ✅ Already implemented and working

**What it does:**
- Exports all iMessage conversations via `imessage-exporter` tool
- Reads Apple Contacts VCF file
- Filters contacts by minimum message count
- Consolidates multiple phone numbers per contact
- Creates structured JSON with conversation metadata
- Generates LLM-ready conversation format

**Output Structure:**
```
data/
├── Charles/
│   ├── contact.json              # Name, phone, email, metadata, conversation insights
│   ├── messages_consolidated.txt # Full message timeline (all phone numbers merged)
│   └── conversation_llm.json     # LLM-optimized format
├── Ryan/
│   └── ...
└── _summary/
    └── contacts_with_messages.json  # Master index
```

**No implementation needed** - tool already works and can be adapted as needed.

---

### 2. Character Selection System

**Purpose:** Let user choose which contacts become playable characters

**Implementation:** `character_selector.py`

**Process:**
1. Load `data/_summary/contacts_with_messages.json`
2. Rank by message count and recency
3. Display interactive selection UI
4. User picks 5-10 contacts
5. Store selections for character generation

**UI Flow:**
```python
def select_characters():
    # Load all contacts
    contacts = load_contacts_summary()
    
    # Rank by engagement (message count × recency)
    ranked = rank_by_engagement(contacts)
    
    # Display selection interface
    print("Select characters (enter numbers, comma-separated):")
    for i, contact in enumerate(ranked[:20], 1):
        print(f"{i}. {contact['name']} - {contact['total_messages']} messages")
        print(f"   Last contact: {contact['last_message_date']}")
    
    # Get user selection
    selections = input("Enter numbers: ").split(',')
    selected_contacts = [ranked[int(i)-1] for i in selections]
    
    return selected_contacts
```

---

### 3. Character Generation Pipeline

**Purpose:** Transform contact data + messages → playable character

**Input:** 
- `data/{ContactName}/contact.json` - Contact info + conversation metadata
- `data/{ContactName}/messages_consolidated.txt` - Full message history

**Process:**
```python
async def generate_character(contact_name: str) -> Character:
    # 1. Load contact data
    contact_data = load_json(f"data/{contact_name}/contact.json")
    messages = load_messages(f"data/{contact_name}/messages_consolidated.txt")
    
    # 2. Build LLM analysis prompt
    prompt = f"""
    Analyze this conversation history between the user and {contact_name}.
    Total messages: {len(messages)}
    Date range: {contact_data['conversation_insights']['date_range']}
    
    Extract and return JSON:
    {{
        "personality": "core personality traits",
        "speaking_style": "how they communicate (casual, formal, emoji use, etc.)",
        "interests": ["topic1", "topic2", ...],
        "relationship_nature": "nature of relationship",
        "memorable_exchanges": ["notable conversation 1", "notable conversation 2"],
        "typical_topics": ["what you usually discuss"],
        "emotional_tone": "overall tone of conversations"
    }}
    
    Messages (last 500 for analysis):
    {json.dumps(messages[-500:])}
    """
    
    # 3. Generate profile via LLM
    profile = await llm_request(prompt, response_format="json_object")
    
    # 4. Create Character object
    character = Character(
        id=f"char_{contact_name.lower()}",
        name=contact_name,
        personality=profile['personality'],
        speaking_style=profile['speaking_style'],
        interests=profile['interests'],
        relationship_strength=calculate_initial_strength(contact_data),
        last_real_contact=contact_data['last_message_info']['last_message_date'],
        message_history_path=f"data/{contact_name}/messages_consolidated.txt",
        memorable_exchanges=profile['memorable_exchanges']
    )
    
    # 5. Save character profile
    save_character(character)
    
    return character
```

**Implementation:** `character_gen.py`

---

### 4. Free-Form Conversation System

**Purpose:** Enable authentic, open-ended dialogue with characters

**Key Feature:** User types ANYTHING they want, not multiple choice

**Implementation:** `conversation.py`

**Conversation Loop:**
```python
async def conversation_loop(character: Character, game_state: GameState):
    """
    Real free-form dialogue where user can say anything
    """
    
    print(f"\n═══ Conversation with {character.name} ═══")
    print(f"Relationship: {game_state.relationships[character.id]}/100")
    print("(Type 'exit' to end conversation)\n")
    
    # Load full message history for context
    message_history = load_messages(character.message_history_path)
    
    while True:
        # Get player input - ANYTHING they want to say
        player_input = input("\nYou: ").strip()
        
        if not player_input:
            continue
        
        if player_input.lower() in ["exit", "quit", "bye"]:
            print(f"\n{character.name.upper()}: \"talk soon!\"")
            break
        
        # Analyze sentiment of what player said
        sentiment_score = analyze_sentiment(player_input)  # -1 to +1
        
        # Build context for LLM
        context = build_conversation_context(
            character=character,
            message_history=message_history[-100:],  # Last 100 real messages
            in_game_history=character.conversation_history[-10:],  # Last 10 in-game exchanges
            player_input=player_input,
            current_relationship=game_state.relationships[character.id]
        )
        
        # Generate character response
        response = await generate_character_response(context)
        
        print(f"\n{character.name.upper()}: \"{response}\"")
        
        # Calculate relationship change based on sentiment
        relationship_delta = calculate_relationship_change(
            sentiment=sentiment_score,
            current_strength=game_state.relationships[character.id],
            conversation_context=context
        )
        
        # Update relationship
        old_strength = game_state.relationships[character.id]
        game_state.relationships[character.id] += relationship_delta
        
        # Show relationship change if significant
        if abs(relationship_delta) >= 3:
            print(f"\n[Relationship: {old_strength} → {game_state.relationships[character.id]} ({relationship_delta:+d})]")
        
        # Save conversation to history
        character.conversation_history.append({
            "player": player_input,
            "character": response,
            "relationship_change": relationship_delta,
            "timestamp": datetime.now().isoformat()
        })
```

**LLM Prompt Structure:**
```python
def build_conversation_context(character, message_history, in_game_history, player_input, current_relationship):
    return {
        "system_prompt": f"""You are {character.name}.

Personality: {character.personality}
Speaking style: {character.speaking_style}
Interests: {', '.join(character.interests)}
Relationship with player: {current_relationship}/100

You must respond authentically as {character.name} would, using their actual speaking patterns and personality. Reference shared experiences from your message history when relevant.
""",
        "conversation_context": {
            "real_message_history": message_history,  # For authenticity
            "in_game_conversation": in_game_history,  # For continuity
            "current_situation": {
                "relationship_strength": current_relationship,
                "player_just_said": player_input
            }
        }
    }
```

---

### 5. Sentiment Analysis & Relationship Dynamics

**Purpose:** Make player's words actually matter

**Implementation:** `sentiment.py`

**Sentiment Analysis:**
```python
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment of player's message
    Returns: {
        'compound': -1 to +1 (overall sentiment),
        'pos': 0 to 1 (positive),
        'neg': 0 to 1 (negative),
        'neu': 0 to 1 (neutral)
    }
    """
    analyzer = SentimentIntensityAnalyzer()
    return analyzer.polarity_scores(text)

def calculate_relationship_change(sentiment: dict, current_strength: int, conversation_context: dict) -> int:
    """
    Calculate how conversation affects relationship
    
    Examples:
    - "I hate you, you suck" → compound: -0.8 → -15 relationship
    - "You're such a good friend" → compound: +0.7 → +5 relationship
    - "Hey what's up" → compound: +0.2 → +1 relationship
    """
    
    compound = sentiment['compound']
    
    # Base relationship change from sentiment
    if compound <= -0.5:
        # Very negative
        base_change = -15
    elif compound <= -0.2:
        # Negative
        base_change = -8
    elif compound >= 0.5:
        # Very positive
        base_change = +5
    elif compound >= 0.2:
        # Positive
        base_change = +3
    else:
        # Neutral
        base_change = +1
    
    # Modifier based on relationship strength
    # Stronger relationships are more resilient to negative
    if compound < 0 and current_strength > 70:
        base_change = int(base_change * 0.6)  # 40% damage reduction
    
    # Weak relationships grow faster with positive interaction
    if compound > 0 and current_strength < 50:
        base_change = int(base_change * 1.3)  # 30% bonus growth
    
    return base_change
```

**Example Interactions:**

**Scenario 1: Supportive**
```
You: I just got rejected from that job interview :(
CHARLES: "damn dude that sucks. their loss honestly. 
          something better will come up"
[Sentiment: +0.6 → +5 relationship]
```

**Scenario 2: Harsh**
```
You: honestly you've been a terrible friend lately
CHARLES: "...wow okay. that's kinda harsh man. 
          what's going on?"
[Sentiment: -0.7 → -12 relationship]
```

**Scenario 3: Neutral**
```
You: what are you up to today?
CHARLES: "just chilling. might hit the gym later"
[Sentiment: +0.1 → +1 relationship]
```

---

### 2. LLM Integration Layer

**Purpose:** Unified interface for all AI interactions

**Responsibilities:**
- API key management
- Rate limiting / error handling
- Prompt templating
- Response parsing

**Key Functions:**
```python
async def generate_character(messages: list) -> Character
async def generate_response(character: Character, context: dict) -> str
async def generate_quest(character: Character, relationship: int) -> Quest
```

**Implementation:** `llm.py`

**Error Handling:**
- Retry logic (3 attempts with exponential backoff)
- Fallback responses for API failures
- Token limit monitoring

---

### 3. Conversation System

**Purpose:** Enable authentic character dialogue

**Context Assembly:**
```python
def build_conversation_context(character: Character, game_state: GameState) -> dict:
    return {
        "character_profile": character.model_dump(),
        "message_history": load_messages(character.message_history_path),
        "in_game_history": character.conversation_history[-10:],  # Last 10 exchanges
        "current_situation": {
            "location": character.current_location,
            "player_energy": game_state.player.energy,
            "relationship_strength": game_state.relationships[character.id],
            "active_quests": [q for q in game_state.active_quests if character.id in q.character_ids]
        }
    }
```

**LLM Prompt Structure:**
```
System: You are {character.name}. {character.personality}
You speak in this style: {character.speaking_style}

Context: Full message history + Recent in-game conversations + Current situation

User input: {player_message}

Respond as {character.name} would, naturally and authentically.
```

**Implementation:** `conversation.py`

---

### 4. Quest System

**Purpose:** Generate and manage gameplay objectives

**Quest Generation:**
- Triggered by: New character introduction, relationship milestones, random events
- Inputs: Character data, relationship strength, player resources
- LLM generates contextually appropriate quests

**Quest Types:**
1. **Relationship:** "Have coffee with Sarah"
2. **Reconnection:** "Reach out to Mike (haven't talked in 6 months)"
3. **Activity:** "Go to gym with Arman"
4. **Exploration:** "Visit the coffee shop Sarah mentioned"

**Quest Lifecycle:**
```
Generated → Active → (In Progress) → Completed/Failed
```

**Implementation:** `quest_system.py`

---

### 5. Resource Management

**Purpose:** Track player constraints (money, time, energy)

**Resources:**

**Money:**
- Starting: $100
- Spent on: Travel, activities, meals
- Earned through: Quest completion

**Time:**
- 8 hours per day initially
- Consumed by: Travel, conversations, activities
- Day advances when time depleted or player sleeps

**Energy:**
- 0-100 scale
- Depleted by: Intensive activities, travel
- Restored by: Rest, positive interactions

**Effects:**
- Low energy → reduced quest success chance
- No money → can't afford activities
- No time → day ends, potential quest failures

**Implementation:** `resource_manager.py`

---

### 6. Save/Load System

**Purpose:** Persistent game state across sessions

**Save Format:** Single JSON file per save slot
```json
{
  "save_id": "save_001",
  "timestamp": "2025-11-09T02:30:00",
  "game_state": { ... }
}
```

**Operations:**
- **Save:** `save_game(game_state: GameState, slot: str)`
- **Load:** `load_game(slot: str) -> GameState`
- **Auto-save:** After major events (quest completion, day end)

**Implementation:** `save_load.py`

---

## Game Flow Architecture

### Main Loop

```python
def main():
    # 1. Initialize or load game
    if save_exists():
        game_state = load_game()
    else:
        game_state = initialize_new_game()
    
    # 2. Main game loop
    while True:
        display_status(game_state)
        command = get_user_input()
        
        if command == "talk":
            handle_conversation(game_state)
        elif command == "quests":
            handle_quests(game_state)
        elif command == "travel":
            handle_travel(game_state)
        elif command == "save":
            save_game(game_state)
        elif command == "exit":
            break
        
        # Update game state
        check_quest_conditions(game_state)
        update_resources(game_state)
        
        # Auto-save
        if should_autosave(game_state):
            save_game(game_state)
```

### Command Structure

**Available Commands:**
- `talk [character]` - Start conversation
- `quests` - View active quests
- `complete [quest_id]` - Attempt quest completion
- `status` - Show player resources and relationships
- `characters` - List all characters
- `travel [location]` - Move to location (simplified for MVP)
- `save` - Manual save
- `load` - Load saved game
- `exit` - Quit game

---

## Implementation Patterns

### Naming Conventions

**Files:** `snake_case.py`
**Classes:** `PascalCase`
**Functions/Variables:** `snake_case`
**Constants:** `UPPER_SNAKE_CASE`

### Error Handling

**Pattern:**
```python
try:
    result = await llm_call()
except openai.RateLimitError:
    # Wait and retry
except openai.APIError as e:
    # Log and use fallback
    logger.error(f"API error: {e}")
    return fallback_response()
```

**All user-facing errors:** Friendly messages, no stack traces

### Logging

**Format:** Simple print statements for MVP (console output)
```python
print(f"[INFO] Character {name} generated successfully")
print(f"[ERROR] Failed to load messages: {error}")
```

**Future:** Python `logging` module for production

---

## API Integration Patterns

### OpenAI Request Pattern

```python
async def llm_request(prompt: str, model: str = "gpt-4o") -> str:
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    
    return response.choices[0].message.content
```

### Structured Output (for Character Generation)

Use JSON mode or function calling for guaranteed structured responses:
```python
response = await client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    response_format={"type": "json_object"}
)
```

---

## Development Workflow

### Setup (First Story)

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
echo "OPENAI_API_KEY=sk-..." > .env

# 4. Create directory structure
mkdir -p src data/messages characters saves

# 5. Export message data (manual or scripted)
# Place in data/messages/
```

### Development Order (Updated with contacts_exporter.py)

**Phase 0: Already Complete ✅**
- Message export system (contacts_exporter.py)
- Data structure for contacts and messages
- Conversation metadata generation
- **Time Saved: 2-3 hours**

**Phase 1: Foundation (1.5 hours)**
1. Project structure setup (`src/` folder, `requirements.txt`)
2. Define data models in `models.py`
3. LLM wrapper in `llm.py`
4. Sentiment analysis in `sentiment.py`
5. Test with existing `data/` folder output

**Phase 2: Character System (2 hours)**
6. Character selection UI (`character_selector.py`)
7. Character generation pipeline (`character_gen.py`)
8. Test with 2-3 real contacts from `data/`
9. Validate generated profiles match personality

**Phase 3: Core Game Loop (1.5 hours)**
10. Basic REPL in `main.py`
11. Game state initialization with selected characters
12. Command parsing (talk, status, quests, save, load, exit)
13. Status display

**Phase 4: Conversation & Relationships (2 hours)**
14. Free-form conversation system (`conversation.py`)
15. Sentiment analysis integration
16. Relationship score updates
17. Conversation history tracking

**Phase 5: Quest & Resources (1 hour)**
18. Quest generation (`quest_system.py`)
19. Resource tracking (`resource_manager.py`)
20. Save/load functionality (`save_load.py`)

**Phase 6: Polish & Testing (1 hour)**
21. Bug fixes
22. Error handling
23. User experience improvements
24. Final testing with real data

**Total Estimated Time: 9 hours (down from 11+ hours thanks to contacts_exporter.py)**

---

## Production Deployment (9 AM Presentation)

### Pre-Launch Checklist

**Step 1: Run Message Export (User's Machine)**
```bash
# User exports their real message data
python contacts_exporter.py --min-messages 50

# Outputs data/ folder with all contacts
```

**Step 2: Character Pre-Generation (Optional for Demo)**
- Run character generation on Charles, Ryan, + 1 more
- Validate profiles feel authentic
- Test free-form conversation with each

**Step 3: Test Full User Flow**
```bash
python main.py

# Test:
1. Character selection from large list (100+ contacts)
2. Character generation from scratch
3. Free-form conversation (try supportive, neutral, harsh messages)
4. Relationship score changes work correctly
5. Quest generation and completion
6. Save/load functionality
```

### Presentation Flow (5 minutes)

**This is PRODUCTION SOFTWARE, not just a demo.**

**1. Problem Statement** (45 sec)
- "We lose touch with people who matter"
- "No system for reflecting on relationships"
- "Life feels unstructured compared to games"

**2. Solution Overview** (30 sec)
- "Life AI transforms your real friendships into a playable experience"
- "Free-form conversations with AI characters based on years of messages"
- "Your choices affect relationship dynamics, just like real life"

**3. Live Demo** (3 min)
- Show message export results (100+ contacts exported)
- Character selection UI
- Free-form conversation with Charles
  - Type ANYTHING (not multiple choice)
  - Show sentiment affecting relationship
  - Demonstrate authentic speaking style
- Show relationship score changes
- Save game state

**4. Technical Highlights** (30 sec)
- "Built in 8 hours with existing message export tool"
- "Handles hundreds of contacts, thousands of messages"
- "Sentiment analysis makes your words matter"
- "Full game state persistence"

**5. What's Next** (30 sec)
- "This is V1 - production-ready terminal app"
- "V2 adds 2D graphics and visual world"
- "V3 explores 3D environments"
- "But the core magic works right now"

---

## Technical Constraints & Considerations

### Token Limits

**Context Window:** 128k tokens (GPT-4o/4-turbo)

**Typical Message History:** 
- 1000 messages ≈ 50k-80k tokens (depending on length)
- Leaves 50k+ for system prompt, in-game history, response

**Strategy:**
- Include full message history in character generation
- At runtime, use character profile + last N in-game exchanges
- If needed: Summarize very old conversations

### Performance

**LLM Latency:** 2-5 seconds per response
- Acceptable for terminal-based gameplay
- Can add "..." loading indicator

**Rate Limits:**
- OpenAI: 10k requests/min (tier 2)
- Not a concern for single-player demo

### Cost Estimation

**Character Generation:** ~$0.10-0.30 per character (one-time)
**Gameplay:** ~$0.01-0.03 per conversation turn
**Demo Budget:** <$5 total with Jack's credits

---

## Security & Privacy

### API Key Management
- **Never commit `.env` to git**
- `.gitignore` includes: `.env`, `data/messages/`, `saves/`

### Message Data
- Personal message data stays local
- Not sent to version control
- Processed only for character generation

### Data Handling
- All message data stored locally
- Only character profiles and conversation context sent to OpenAI API
- No persistent storage on OpenAI servers (per API terms)

---

## Architecture Decision Records (ADRs)

### ADR-001: Use OpenAI API over Local Models

**Context:** Need fast, reliable LLM with large context window

**Decision:** OpenAI API (GPT-4o/GPT-4-turbo)

**Rationale:**
- 128k context window handles full message histories
- 8-hour timeline prioritizes speed over cost
- Jack's AWS/OpenAI credits available
- Can swap to local model post-hackathon

**Consequences:**
- Network dependency
- API costs (mitigated by credits)
- Faster development time

---

### ADR-002: File-Based State Management

**Context:** Need persistent storage for game state

**Decision:** JSON files in `saves/` directory

**Rationale:**
- Zero setup time (no database installation)
- Human-readable for debugging
- Simple serialization with Pydantic
- Sufficient for single-player MVP

**Consequences:**
- Not scalable for multiplayer
- Manual file management
- Perfect for hackathon scope

---

### ADR-003: Terminal Interface

**Context:** UI approach for MVP

**Decision:** Terminal/CLI with text commands

**Rationale:**
- Fastest to implement
- Zero UI framework overhead
- Focus on core game mechanics
- Aligns with "V1 text-based" vision

**Consequences:**
- Limited visual appeal
- Requires command memorization
- Perfectly demonstrates core concept
- Can add GUI post-hackathon

---

### ADR-004: Modular Python Structure

**Context:** Code organization for parallel development

**Decision:** Separate modules for each system

**Rationale:**
- Clear separation of concerns
- Easy to test components independently
- Allows parallel development with Jack
- Standard Python project structure

**Consequences:**
- More files to manage
- Requires discipline in module boundaries
- Enables rapid parallel work

---

## Next Steps

1. **Set up development environment** (10 minutes)
2. **Export message data** (20 minutes)
3. **Create demo story document** (15 minutes) ← NEXT
4. **Begin implementation** (remaining time)

---

## Architecture Validation Checklist

- [x] All technology choices have specific versions
- [x] Project structure is complete and specific
- [x] Data models defined for all entities
- [x] Implementation order prioritized
- [x] Demo flow documented
- [x] Security considerations addressed
- [x] No engine/framework overhead
- [x] Optimized for 8-hour timeline
- [x] Clear separation of concerns
- [x] Error handling strategy defined

---

**Architecture Status:** ✅ COMPLETE

**Ready for:** Story Creation → Implementation

**Estimated Setup Time:** 30 minutes  
**Estimated Implementation Time:** 6 hours  
**Buffer for Issues:** 1.5 hours

---

*Generated by BMAD Game Architecture Workflow*  
*Cloud Dragonborn, Principal Game Architect*  
*Date: November 9, 2025*

