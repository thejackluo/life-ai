# Scripts Directory

This directory contains utility scripts for the Life AI project.

## Contacts Export Pipeline

Located in `contacts_export/`, this module handles exporting iMessage contacts and conversations to structured JSON format suitable for LLM processing.

### Usage

```bash
# From project root
python scripts/contacts_export/exporter.py [vcf_file]

# Or as a module
python -m scripts.contacts_export.exporter [vcf_file]
```

### Components

- **exporter.py**: Main contacts and messages export functionality
- **llm_conversation.py**: LLM conversation file generation (main conversation format)
- **llm_processor.py**: Processing orchestration and workflow management
- **privacy_handler.py**: Privacy and anonymization features
- **recent_interactions.py**: Recent message analysis and pattern detection

### Configuration

The export pipeline can be configured with command-line arguments:

```bash
# Set minimum message count threshold
python scripts/contacts_export/exporter.py contacts.vcf --min-messages 20

# Disable privacy features (not recommended)
python scripts/contacts_export/exporter.py contacts.vcf --disable-privacy
```

### Output

Exports are saved to `data/` with the following structure:

```
data/
├── [Contact Name]/
│   ├── contact.json                          # Contact metadata
│   ├── conversation_llm.json                 # LLM-ready conversation
│   ├── conversation_recent_interactions.json # Recent messages for pattern analysis
│   └── messages_consolidated.txt             # Raw message timeline
├── _llm_ready/
│   ├── master_index.json                     # Index of all conversations
│   └── conversation_summaries.json           # Quick stats
└── _summary/
    ├── all_contacts.json
    └── contacts_with_messages.json
```

### Features

- **Full message history** for authentic character generation
- **Privacy anonymization** with mapping for re-identification
- **Recent interactions** analysis for communication patterns
- **Group chat** support
- **Consolidated timelines** across multiple phone numbers
- **LLM-optimized** formatting with message grouping and cleaning

### Requirements

- Python 3.10+
- imessage-exporter (cargo install imessage-exporter)
- Terminal with Full Disk Access (macOS)
- See `requirements.txt` for Python dependencies

