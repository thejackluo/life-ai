"""
Contacts Export Pipeline

This module provides utilities for exporting iMessage contacts and conversations
to structured JSON format suitable for LLM processing.

Main Components:
- exporter.py: Main contacts and messages export functionality
- llm_conversation.py: LLM conversation file generation
- llm_processor.py: Processing orchestration
- privacy_handler.py: Privacy and anonymization features
- recent_interactions.py: Recent message analysis

Usage:
    python -m scripts.contacts_export.exporter [vcf_file]

Or from the command line:
    python scripts/contacts_export/exporter.py [vcf_file]
"""

__version__ = "2.0.0"
__all__ = [
    "exporter",
    "llm_conversation",
    "llm_processor",
    "privacy_handler",
    "recent_interactions"
]

