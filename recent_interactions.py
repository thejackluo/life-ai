"""
Recent Interactions Module

This module handles the creation of recent interactions files that focus on 
communication pattern analysis with preserved formatting and minimal cleaning.
"""

import re
import json
import os
from datetime import datetime
from dateutil.parser import parse

# Import privacy functionality
from privacy_handler import (
    ANONYMIZE_LLM_DATA,
    RECENT_INTERACTIONS_COUNT,
    RECENT_INTERACTIONS_FILENAME,
    anonymize_data_for_llm
)


def clean_message_content_minimal(content):
    """
    Minimal cleaning for recent interactions - preserves original formatting and style
    Only removes system artifacts that don't add conversational value
    """
    if not content or not isinstance(content, str):
        return ""
    
    # Only remove system artifacts that don't represent actual communication
    content = re.sub(r'\(Read by .+?\)', '', content)  # Read receipts
    content = re.sub(r'\(Delivered.+?\)', '', content)  # Delivery receipts
    
    # Remove system messages about replies and reactions (these aren't the actual messages)
    content = re.sub(r'This message responded to an earlier message\.?', '', content)
    content = re.sub(r'Replied to ".+?"', '', content)
    content = re.sub(r'Reacted to ".+?" with .+', '', content)
    content = re.sub(r'Emphasized ".+?"', '', content)
    content = re.sub(r'Liked ".+?"', '', content)
    content = re.sub(r'Loved ".+?"', '', content)
    content = re.sub(r'Laughed at ".+?"', '', content)
    content = re.sub(r'Questioned ".+?"', '', content)
    content = re.sub(r'Disliked ".+?"', '', content)
    content = re.sub(r'Tapback: .+', '', content)
    
    # Remove bracketed system messages but keep everything else
    content = re.sub(r'\[.+?\]', '', content)
    
    # Normalize excessive whitespace but preserve intentional formatting
    content = re.sub(r'\s+', ' ', content)  # Multiple spaces/newlines -> single space
    content = content.strip()
    
    # Keep the message even if very short - in recent interactions, "ok" or "yes" matters for pattern analysis
    return content


def extract_recent_interactions(messages, count=RECENT_INTERACTIONS_COUNT):
    """
    Extract recent messages for interaction pattern analysis with minimal processing
    Preserves original formatting and communication style
    """
    if not messages:
        return []
    
    # Take the most recent messages (already sorted chronologically)
    recent_messages = messages[-count:] if len(messages) > count else messages
    
    # Apply minimal cleaning while preserving communication patterns
    processed_messages = []
    
    for message in recent_messages:
        content = clean_message_content_minimal(message.get('content', ''))
        
        # Keep even very short messages - they're important for interaction patterns
        if content:  # Only filter out completely empty messages
            processed_message = {
                'timestamp': message.get('timestamp', ''),
                'sender': message.get('sender', 'unknown'),
                'content': content
            }
            
            # Preserve any metadata that might be useful for interaction analysis
            if 'metadata' in message:
                processed_message['metadata'] = message['metadata']
                
            processed_messages.append(processed_message)
    
    return processed_messages


def analyze_interaction_patterns(messages):
    """
    Analyze interaction patterns in recent messages to provide context for LLM
    """
    if not messages:
        return {}
    
    # Basic interaction stats
    total_messages = len(messages)
    user_messages = [m for m in messages if m.get('sender') == 'me']
    contact_messages = [m for m in messages if m.get('sender') == 'contact']
    
    # Response patterns
    response_pairs = []
    for i in range(len(messages) - 1):
        current = messages[i]
        next_msg = messages[i + 1]
        if current.get('sender') != next_msg.get('sender'):
            response_pairs.append({
                'prompt': current.get('content', ''),
                'response': next_msg.get('content', ''),
                'prompt_sender': current.get('sender'),
                'response_sender': next_msg.get('sender')
            })
    
    # Communication style indicators
    user_avg_length = sum(len(m.get('content', '')) for m in user_messages) / len(user_messages) if user_messages else 0
    contact_avg_length = sum(len(m.get('content', '')) for m in contact_messages) / len(contact_messages) if contact_messages else 0
    
    # Recent activity
    timestamps = [m.get('timestamp') for m in messages if m.get('timestamp')]
    if timestamps:
        try:
            first_recent = parse(timestamps[0])
            last_recent = parse(timestamps[-1])
            timespan_hours = (last_recent - first_recent).total_seconds() / 3600
        except Exception:
            timespan_hours = 0
    else:
        timespan_hours = 0
    
    analysis = {
        "message_count": total_messages,
        "user_messages": len(user_messages),
        "contact_messages": len(contact_messages),
        "response_pairs": len(response_pairs),
        "user_avg_message_length": round(user_avg_length, 1),
        "contact_avg_message_length": round(contact_avg_length, 1),
        "timespan_hours": round(timespan_hours, 2),
        "interaction_ratio": round(len(contact_messages) / len(user_messages), 2) if user_messages else 0
    }
    
    return analysis


def create_recent_interactions_file(contact_name, contact_data, messages, output_folder):
    """
    Create a recent interactions file focusing on communication patterns with preserved formatting
    """
    if not messages:
        return None, None
    
    # Extract recent interactions with minimal processing
    recent_interactions = extract_recent_interactions(messages)
    
    if not recent_interactions:
        return None, None
    
    # Analyze interaction patterns
    interaction_analysis = analyze_interaction_patterns(recent_interactions)
    
    # Extract contact information (same as main LLM file)
    contact_info = {
        "name": contact_name,
        "phone_numbers": contact_data.get('phone_numbers', []),
    }
    
    # Add additional contact context if available
    if 'emails' in contact_data:
        contact_info['emails'] = [email['address'] for email in contact_data['emails']]
    
    if 'organization' in contact_data:
        contact_info['organization'] = contact_data['organization']
    
    if 'title' in contact_data:
        contact_info['title'] = contact_data['title']
    
    # Create the recent interactions structure
    recent_interactions_data = {
        "format": "recent_interactions_analysis",
        "purpose": "Communication pattern analysis with preserved formatting",
        "contact": contact_info,
        "interaction_analysis": interaction_analysis,
        "recent_messages": recent_interactions,
        "metadata": {
            "total_messages_analyzed": len(recent_interactions),
            "messages_requested": RECENT_INTERACTIONS_COUNT,
            "generated_at": datetime.now().isoformat()
        }
    }
    
    # Apply anonymization if enabled (but preserve formatting)
    anonymized_data, privacy_mapping = anonymize_data_for_llm(recent_interactions_data, contact_name)
    
    # Save the recent interactions file
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', contact_name)
    contact_folder = os.path.join(output_folder, safe_name)
    recent_file_path = os.path.join(contact_folder, RECENT_INTERACTIONS_FILENAME)
    
    with open(recent_file_path, 'w', encoding='utf-8') as f:
        json.dump(anonymized_data if ANONYMIZE_LLM_DATA else recent_interactions_data, f, indent=2, ensure_ascii=False)
    
    return recent_file_path, interaction_analysis 