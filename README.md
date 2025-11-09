# Life AI: Your Life as an Interactive Game

A memory-based life simulation game that transforms your actual relationships, places, and aspirations into an explorable world. Not an escape from reality—a tool for understanding, reflecting on, and strengthening your connection to it.

---

## Overview

Life AI creates a persistent, interactive world model of your actual life where:

- **Characters are real people you know** - friends, family, mentors, aspirational figures
- **Locations are actual places** - using real geographic coordinates and distances
- **Quests emerge from your life patterns** - reflecting relationships and goals
- **The world remembers and evolves** - actions have consequences, relationships develop
- **Structure meets freedom** - enough guidance to be engaging, enough openness to feel personal

Unlike AI Dungeon's freeform generation or generic life sims, Life AI grounds every element in your reality while adding game structure that makes life feel intentional and explorable.

---

## Vision

### The Core Problem

Modern life creates a paradox: we're more connected than ever, yet we experience profound disconnection from people and places that matter. We lose touch with friends, forget meaningful memories, lack structure for pursuing goals, and struggle to see our lives as narratives with agency.

### Our Solution

Transform your life into an interactive game that helps you:

- **Recognize patterns** in your relationships and choices
- **Explore possibilities** between current reality and aspirational future
- **Strengthen connections** through reflection and prompts to action
- **See structure** in what feels like chaos
- **Take intentional action** on what matters most

---

## Product Versions

### V1: Text-Based MVP

A complete, playable text adventure game with:

- Node-based world representation with real geography
- AI-generated quests based on relationships and goals
- Dynamic dialogue with character personalities
- Resource management (money, time, energy)
- Relationship progression system
- Multiple endings based on choices
- Local AI support (LM Studio) + OpenAI API fallback

**Status:** In Development  
**Documentation:** [`docs/product/product-v1.md`](docs/product/product-v1.md)

### V2: 2D Visual Experience

Evolution of V1 with rich visual presentation:

- Interactive 2D world map (Godot engine)
- AI-generated character portraits and location art
- Visual quest journal and relationship networks
- Cinematic key moments with music
- Point-and-click exploration
- All V1 systems enhanced with visual layer

**Status:** Planned  
**Documentation:** [`docs/product/product-v2.md`](docs/product/product-v2.md)

---

## Key Features

### Personal World Generation

Input 5-10 important people and places from your life. AI generates rich backstories, personalities, and connections, creating a world that feels authentically yours.

### Memory-Based Quests

- **Relationship quests:** "Have coffee with Sarah" or "Reconnect with Mike"
- **Location quests:** "Try that Korean BBQ place" or "Visit the museum"
- **Aspirational quests:** "Meet Elon Musk" or "Pitch to Y Combinator"
- **Personal growth:** "Go to gym 3x this week" or "Finish side project"

### Real Geography Integration

Travel times and costs based on actual distances. Your world's topology reflects the real spatial relationships between places in your life.

### Relationship Dynamics

Every interaction affects relationship strength (0-100). Relationships deepen with investment, fade with neglect—just like real life.

### Meaningful Choices

Structured options (3-5 choices) at decision points. Enough freedom to feel creative, enough structure to maintain momentum. Every choice has consequences.

### Multiple Endings

Your playthrough concludes based on which relationships you invested in, which goals you pursued, and how you balanced different life aspects.

---

## Technology Stack

### V1 (Text-Based MVP)

- **Language:** Python 3.10+
- **AI Integration:** LM Studio (local models) + OpenAI API (fallback)
- **Data Models:** Pydantic
- **Configuration:** YAML
- **External APIs:** Google Maps (coordinates and distances)
- **Interface:** Rich CLI with colorama

### V2 (2D Visual)

- **Game Engine:** Godot 4.x
- **Scripting:** GDScript + Python bridge
- **Asset Generation:** AI-generated (Stable Diffusion, DALL-E, etc.)
- **Audio:** Dynamic music system, environmental sound
- **Backend:** V1 Python engine (preserved)

---

## Project Structure

```
life-ai/
├── app/                          # Application code
│   ├── core/                     # Game engine core
│   │   ├── world.py             # World graph management
│   │   ├── state_machine.py    # Player state tracking
│   │   ├── character_manager.py # Character system
│   │   ├── quest_engine.py      # Quest generation
│   │   └── resources.py         # Resource management
│   ├── models/                   # Data models
│   │   ├── place.py
│   │   ├── character.py
│   │   ├── relationship.py
│   │   ├── event.py
│   │   └── game_state.py
│   ├── ai/                       # AI integration
│   │   ├── provider.py          # AI provider abstraction
│   │   ├── prompts.py           # Prompt engineering
│   │   └── generators.py        # Generation functions
│   ├── cli/                      # Text interface (V1)
│   │   ├── game.py              # Main game loop
│   │   ├── commands.py          # Command handling
│   │   └── display.py           # Output formatting
│   └── godot/                    # 2D environment (V2)
│       ├── scenes/
│       ├── scripts/
│       └── assets/
├── data/                         # Sample data
│   ├── characters.json
│   ├── places.json
│   ├── relationships.json
│   └── events.json
├── docs/                         # Documentation
│   ├── product/                  # Product vision
│   │   ├── product-v1.md        # Text-based MVP
│   │   └── product-v2.md        # 2D visual experience
│   ├── architecture/             # Technical docs (TBD)
│   └── general/                  # Meeting notes & context
├── config/                       # Configuration
│   ├── game_config.yaml
│   ├── ai_config.yaml
│   └── maps_config.yaml
├── scripts/                      # Utility scripts
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- (Optional) LM Studio for local AI models
- (Optional) OpenAI API key for cloud fallback
- (Optional) Google Maps API key for location features

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/life-ai.git
cd life-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure settings
cp config/ai_config.yaml.example config/ai_config.yaml
# Edit config files with your API keys and preferences
```

### Quick Start

```bash
# Run the game (V1 text-based)
python -m app.cli.game

# Follow the setup wizard to create your world
# Start playing!
```

---

## Development

### Development Philosophy

Based on Jack and Arman's approach:

- **Start simple, iterate quickly** - Text MVP before 2D
- **AI-assisted development** - Using Cursor, vMat for planning
- **Voice-driven prompting** - Natural language workflow
- **Open source first** - Local models, Godot engine
- **Build in public** - Share progress and learnings

### Tools Used

- **Cursor** - AI-assisted coding with voice input
- **vMat** - Architecture planning and consistency
- **LM Studio** - Local AI model testing
- **Godot 4.x** - 2D game engine (V2)
- **GitHub** - Version control and collaboration

### Contributing

This project is currently in early development by Jack and Arman. We're not accepting external contributions yet, but feel free to:

- Star and watch the repo
- Open issues for bugs or suggestions
- Share your thoughts and ideas
- Follow development progress

---

## Roadmap

### Phase 1: Foundation (Current)

- [x] Project structure setup
- [x] Product vision documents (V1 & V2)
- [ ] Core data models implementation
- [ ] World graph and state machine
- [ ] AI provider abstraction layer

### Phase 2: Text MVP (V1)

- [ ] Character and quest systems
- [ ] CLI interface and commands
- [ ] Resource management
- [ ] Save/load functionality
- [ ] Sample data and testing
- [ ] Beta testing with 20-50 users

### Phase 3: 2D Foundation (V2)

- [ ] Godot project setup
- [ ] Python-Godot bridge
- [ ] Basic world map rendering
- [ ] Character portrait generation
- [ ] Location scene generation

### Phase 4: Visual Polish (V2)

- [ ] Full UI implementation
- [ ] Music and sound design
- [ ] Cinematic moments
- [ ] Animation and effects
- [ ] Performance optimization

### Phase 5: Launch

- [ ] Marketing materials
- [ ] Documentation completion
- [ ] Community building
- [ ] Public release

---

## Philosophy

### Success = Hard Work + Leverage + Luck

As discussed in the founding meeting, success isn't just about individual effort. Life AI embodies this philosophy:

- **Hard work:** The game respects effort and investment
- **Leverage:** Shows how connections and relationships create opportunities
- **Luck:** Acknowledges randomness while revealing controllable pathways

### Life as a Game with Side Quests

"Everyone views the world as a game with infinite possibilities. Complete all the side quests."

Life AI helps you see your life as a game—not to trivialize it, but to recognize agency, structure, and the importance of side quests alongside main goals.

### Technology That Strengthens Human Connection

AI should help us understand and connect with each other better, not replace human interaction. Life AI uses AI to create reflection that prompts real-world connection.

---

## Inspiration & Context

Life AI was conceived during a hackathon planning session between Jack and Arman, inspired by:

- **Google's Genie 3** - World generation with memory
- **AI Dungeon** - But with structure and persistence
- **Life simulation games** - But personal and meaningful
- **The "leverage" concept** - Understanding pathways to success
- **Disconnection problem** - Modern life's relationship challenges

See [`docs/general/life-ai-raw-meeting.md`](docs/general/life-ai-raw-meeting.md) for full context.

---

## License

[License information to be added]

---

## Contact

- **Jack** - Project lead, architecture
- **Arman** - Collaboration, design input

For inquiries: [contact information]

---

## Acknowledgments

Special thanks to:

- The AI research community for making this possible
- Google's Genie 3 team for inspiration
- The open-source Godot community
- LM Studio and Suno teams
- Everyone building tools that help us understand ourselves better

---

**Remember:** This is your life as a game. What side quests will you complete?
