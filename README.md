# Life AI - Your Life as a Game

A terminal-based life simulation game built from your **real iMessage history**. Talk to AI-powered versions of your friends, make choices that affect relationships, and reflect on your real connections.

## What Is This?

Life AI transforms your text message history into a playable game where:
- Your contacts become game characters grounded in their ACTUAL messages
- The AI sees their FULL message history - every text, every phrase, every pattern
- Conversations affect relationship strength based on sentiment analysis  
- Your words matter - positive messages strengthen bonds, negative ones weaken them
- Characters respond authentically because they're built from real communication

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

## How It Works

### The Key Innovation: Full Message History

Unlike traditional chatbots, Life AI shows the LLM **every single message** from your real conversation history. For a contact with 1000 messages, the AI sees all 1000 - learning their exact communication style, phrases, humor, and patterns.

**Example:** If Ryan says "bro" in 80% of his messages, the AI will use "bro" naturally because it's seen the pattern in hundreds of real examples.

### Cost & Performance

**Character Generation:** ~15 seconds per character, ~$0.03  
**Conversations:** ~$0.30-0.50 per conversation (varies by message count)  
**Why the cost?** We send the full message history (500-2000 messages) with every response for maximum authenticity.

**For demo/testing purposes, this cost is acceptable. For production, we could optimize with message sampling.**

## Technical Details

### Architecture

```
src/
├── core/              # Foundation
│   ├── models.py      # Pydantic data models (simplified)
│   ├── llm.py         # OpenAI integration
│   └── sentiment.py   # Sentiment analysis
│
├── game/              # Game systems
│   ├── character_selector.py  # Choose contacts (1-20 characters)
│   ├── character_gen.py       # Load full message history
│   ├── message_sampler.py     # Message loading utilities
│   ├── conversation.py        # Free-form dialogue with full context
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

