# Life AI - Your Life as a Game

A terminal-based life simulation game built from your **real iMessage history**. Talk to AI-powered versions of your friends, make choices that affect relationships, and reflect on your real connections.

## What Is This?

Life AI transforms your text message history into a playable game where:
- Your contacts become game characters with AI-generated personalities
- Conversations affect relationship strength based on sentiment analysis  
- Your words matter - positive messages strengthen bonds, negative ones weaken them
- Real message patterns shape how characters respond to you

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up OpenAI API Key

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-key-here
```

### 3. Export Your Messages (if not done already)

```bash
python contacts_exporter.py
```

This creates a `data/` folder with your exported messages.

### 4. Play the Game!

```bash
python -m src.main
```

## How to Play

### Starting a New Game

1. Enter your name
2. Select 5-10 contacts to become characters (interactive UI)
3. Wait while AI generates personalities from message history
4. Start playing!

### Commands

- `talk [name]` or `t [name]` - Start a conversation
- `status` or `stats` - Check your current state
- `characters` or `c` - See all characters and relationships
- `quests` or `q` - View available quests
- `save` - Save your game
- `load` - Load a saved game
- `help` - Show all commands
- `quit` - Exit (auto-saves)

### Having Conversations

Type anything! The AI will respond based on the character's real personality from your messages.

- Your **words affect relationships** (sentiment analysis in real-time)
- Positive messages: +5 to +15 relationship points
- Negative messages: -5 to -15 relationship points
- Type `bye`, `quit`, or `exit` to end conversation

### Understanding Relationships

- **0-20**: Stranger
- **21-40**: Acquaintance  
- **41-60**: Friend
- **61-80**: Close Friend
- **81-100**: Best Friend

## Technical Details

### Architecture

```
src/
├── core/              # Foundation
│   ├── models.py      # Pydantic data models
│   ├── llm.py         # OpenAI integration
│   └── sentiment.py   # Sentiment analysis
│
├── game/              # Game systems
│   ├── character_selector.py  # Choose contacts
│   ├── character_gen.py       # AI personality generation
│   ├── conversation.py        # Free-form dialogue
│   ├── quest_system.py        # Quest generation
│   ├── resource_manager.py   # Resources (MVP)
│   └── save_load.py           # Persistence
│
└── main.py            # Game entry point
```

### Tech Stack

- **Python 3.11+**
- **OpenAI GPT-4o** - Character personalities and responses
- **vaderSentiment** - Real-time sentiment analysis
- **Pydantic** - Type-safe data models
- **JSON** - Save game format

## Project Status

**Current:** V1 Terminal MVP ✅  
**Next:** V2 2D Visual Experience (Godot) 🚧

See `docs/ARCHITECTURE-SUMMARY.md` and `docs/product/product-v2.md` for roadmap.

## Credits

Built with the BMAD Method for agentic software development.

## License

See LICENSE file.

