"""
LLM Conversation Module

This module handles the creation of main LLM-ready conversation files with message 
optimization, grouping, and cleaning for general AI processing.
"""

import re
import json
import os
from datetime import datetime, timedelta
from dateutil.parser import parse
import emoji

# Import privacy functionality
from privacy_handler import (
    ANONYMIZE_LLM_DATA,
    RECENT_INTERACTIONS_COUNT,
    anonymize_data_for_llm,
    get_person_placeholder,
    get_phone_placeholder,
    get_email_placeholder,
    get_global_mappings,
    PRIVACY_MAPPING_FILE
)


def process_emojis_for_llm(content):
    """
    Process emojis for LLM optimization:
    1. Convert emojis to text descriptions
    2. Remove consecutive duplicate emojis
    3. Clean up excessive emoji usage
    """
    if not content:
        return content
    
    # Convert emojis to text descriptions first
    content = emoji.demojize(content, delimiters=(":", ":"))
    
    # Reduce consecutive duplicate emoji descriptions BEFORE replacements
    # This handles cases like :heart::heart::heart: → :heart:
    content = re.sub(r'(:[\w_-]+:)(\1)+', r'\1', content)
    
    # Replace common emojis with shorter, LLM-friendly text
    emoji_replacements = {
        ':face_with_tears_of_joy:': '(laughing)',
        ':red_heart:': '(heart)',
        ':smiling_face_with_heart-eyes:': '(heart eyes)', 
        ':thumbs_up:': '(thumbs up)',
        ':thumbs_down:': '(thumbs down)',
        ':fire:': '(fire)',
        ':clapping_hands:': '(clapping)',
        ':folded_hands:': '(praying)',
        ':rolling_on_the_floor_laughing:': '(laughing)',
        ':crying_face:': '(crying)',
        ':smiling_face:': '',  # Remove simple smiles as they add little value
        ':winking_face:': '',  # Remove simple winks
        ':kissing_face:': '(kiss)',
        ':thinking_face:': '(thinking)',
        ':face_with_rolling_eyes:': '(eye roll)',
        ':person_shrugging:': '(shrug)',
        ':shrugging:': '(shrug)',
        # Add some more common ones
        ':grinning_face:': '',
        ':beaming_face_with_smiling_eyes:': '',
        ':star-struck:': '(amazed)',
        ':partying_face:': '(party)'
    }
    
    for emoji_code, replacement in emoji_replacements.items():
        content = content.replace(emoji_code, replacement)
    
    # For remaining complex emoji descriptions, be more selective
    # Remove very long/complex emoji descriptions
    content = re.sub(r':[\w_-]{15,}:', '', content)  # Remove very long emoji descriptions
    # Convert remaining medium-length emojis to simple tag
    content = re.sub(r':[\w_-]+:', '(emoji)', content)
    
    # Clean up multiple consecutive (emoji) tags
    content = re.sub(r'\(emoji\)\s*\(emoji\)+', '(emoji)', content)
    
    # Remove standalone (emoji) that don't add value
    if content.strip() == '(emoji)':
        return ''
    
    # Clean up extra spaces
    content = ' '.join(content.split())
    
    return content


def clean_message_content(content):
    """
    Clean message content for LLM processing by removing noise and stop words
    """
    if not content or not isinstance(content, str):
        return ""
    
    # Remove excessive whitespace and normalize
    content = ' '.join(content.split())
    
    # Process emojis for LLM optimization
    content = process_emojis_for_llm(content)
    
    # Remove read receipt and delivery artifacts
    content = re.sub(r'\(Read by .+?\)', '', content)
    content = re.sub(r'\(Delivered.+?\)', '', content)
    
    # Remove system messages about replies and reactions
    content = re.sub(r'This message responded to an earlier message\.?', '', content)
    content = re.sub(r'Replied to ".+?"', '', content)
    content = re.sub(r'Reacted to ".+?" with .+', '', content)
    content = re.sub(r'Emphasized ".+?"', '', content)
    content = re.sub(r'Liked ".+?"', '', content)
    content = re.sub(r'Loved ".+?"', '', content)
    content = re.sub(r'Laughed at ".+?"', '', content)
    content = re.sub(r'Questioned ".+?"', '', content)
    content = re.sub(r'Disliked ".+?"', '', content)
    
    # Remove tapback artifacts
    content = re.sub(r'Tapback: .+', '', content)
    
    # Remove other system messages
    content = re.sub(r'\[.+?\]', '', content)  # Remove bracketed system messages
    
    # Clean up multiple spaces again after removals
    content = ' '.join(content.split())
    
    # Remove very short meaningless messages
    short_meaningless = {
        'ok', 'okay', 'k', 'kk', 'lol', 'haha', 'yeah', 'yes', 'no', 'np', 
        'yep', 'nope', 'sure', 'cool', 'nice', 'alright', 'ty', 'thx', 'thanks',
        'hmm', 'mhm', 'yup', 'nah', 'sup', 'hey', 'hi', 'hello', 'bye'
    }
    
    if content.lower().strip() in short_meaningless:
        return ""
    
    # Remove if it's just emojis or very short
    if len(content.strip()) <= 2:
        return ""
    
    # Remove excessive punctuation
    content = re.sub(r'[.]{3,}', '...', content)
    content = re.sub(r'[!]{2,}', '!', content)
    content = re.sub(r'[?]{2,}', '?', content)
    
    return content.strip()


def should_start_new_group(prev_timestamp, curr_timestamp, time_window_minutes):
    """
    Determine if we should start a new message group based on time gap
    """
    try:
        prev_time = parse(prev_timestamp)
        curr_time = parse(curr_timestamp)
        
        time_diff = curr_time - prev_time
        return time_diff > timedelta(minutes=time_window_minutes)
    except Exception:
        # If we can't parse timestamps, start new group to be safe
        return True


def is_content_similar(content1, content2, similarity_threshold=0.8):
    """
    Check if two pieces of content are too similar (to prevent duplication)
    """
    # Simple similarity check - if one is contained in the other and they're similar length
    shorter = content1 if len(content1) < len(content2) else content2
    longer = content2 if len(content1) < len(content2) else content1
    
    if len(shorter) == 0:
        return False
    
    # If the shorter text is mostly contained in the longer text
    if shorter in longer and len(shorter) / len(longer) > similarity_threshold:
        return True
    
    return False


def group_consecutive_messages(messages, time_window_minutes=10):
    """
    Group consecutive messages from the same sender within a time window
    """
    if not messages:
        return []
    
    grouped_messages = []
    current_group = None
    
    for message in messages:
        # Clean the content first
        cleaned_content = clean_message_content(message.get('content', ''))
        
        # Skip empty messages after cleaning
        if not cleaned_content:
            continue
        
        sender = message.get('sender', 'unknown')
        timestamp = message.get('timestamp', '')
        
        # If this is the first message or different sender, start new group
        if (current_group is None or 
            current_group['sender'] != sender or 
            should_start_new_group(current_group['timestamp'], timestamp, time_window_minutes)):
            
            # Save previous group if it exists
            if current_group:
                grouped_messages.append(current_group)
            
            # Start new group
            current_group = {
                'timestamp': timestamp,
                'sender': sender,
                'content': cleaned_content
            }
        else:
            # Check for duplication before adding to current group
            existing_content = current_group['content'].lower()
            new_content = cleaned_content.lower()
            
            # Only add if it's not a duplicate or very similar
            if (new_content not in existing_content and 
                not is_content_similar(existing_content, new_content)):
                current_group['content'] += ' ' + cleaned_content
    
    # Add the last group
    if current_group:
        grouped_messages.append(current_group)
    
    return grouped_messages


def optimize_messages_for_llm(messages):
    """
    Apply all LLM optimizations: grouping, cleaning, and filtering
    """
    # First group consecutive messages
    grouped = group_consecutive_messages(messages)
    
    # Filter out any remaining empty or very short messages
    filtered = []
    for msg in grouped:
        content = msg.get('content', '').strip()
        if len(content) >= 3:  # Keep messages with at least 3 characters
            filtered.append(msg)
    
    return filtered


def generate_conversation_metadata(messages, contact_data):
    """
    Generate conversation intelligence metadata for LLM processing
    """
    if not messages:
        return {}
    
    # Basic stats
    total_messages = len(messages)
    sent_messages = sum(1 for m in messages if m.get('sender') == 'me')
    received_messages = sum(1 for m in messages if m.get('sender') == 'contact')
    
    # Date range
    timestamps = [m.get('timestamp') for m in messages if m.get('timestamp')]
    if timestamps:
        first_message = min(timestamps)
        
        try:
            first_date = parse(first_message)
            current_date = datetime.now()
            conversation_span_days = (current_date - first_date).days
            
            date_range = f"{first_date.strftime('%Y-%m-%d')} to present"
        except Exception:
            date_range = f"{first_message} to present"
            conversation_span_days = 0
    else:
        date_range = "Unknown"
        conversation_span_days = 0
    
    # Phone number usage - we'll need to get this from the consolidation process
    phone_usage = contact_data.get('phone_usage', {})
    most_active_number = max(phone_usage.items(), key=lambda x: x[1])[0] if phone_usage else "unknown"
    
    # Message frequency
    message_frequency = round(total_messages / max(conversation_span_days, 1), 2)
    
    metadata = {
        "total_messages": total_messages,
        "sent_messages": sent_messages,
        "received_messages": received_messages,
        "date_range": date_range,
        "conversation_span_days": conversation_span_days,
        "message_frequency_per_day": message_frequency,
        "most_active_number": most_active_number,
        "phone_number_usage": phone_usage
    }
    
    return metadata


def create_llm_conversation_file(contact_name, contact_data, messages, output_folder):
    """
    Create an LLM-ready conversation file for a single contact
    """
    # Apply LLM optimizations: grouping, cleaning, filtering
    optimized_messages = optimize_messages_for_llm(messages)
    
    # Extract contact information
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
    
    # Generate conversation metadata (use optimized messages for stats)
    conversation_metadata = generate_conversation_metadata(optimized_messages, contact_data)
    
    # Create the LLM-ready structure
    llm_data = {
        "contact": contact_info,
        "conversation_metadata": conversation_metadata,
        "messages": optimized_messages
    }
    
    # Apply anonymization if enabled
    anonymized_data, privacy_mapping = anonymize_data_for_llm(llm_data, contact_name)
    
    # Save inside the contact's folder instead of separate _llm_ready folder
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', contact_name)
    contact_folder = os.path.join(output_folder, safe_name)
    llm_file_path = os.path.join(contact_folder, 'conversation_llm.json')
    
    with open(llm_file_path, 'w', encoding='utf-8') as f:
        json.dump(anonymized_data if ANONYMIZE_LLM_DATA else llm_data, f, indent=2, ensure_ascii=False)
    
    # Save privacy mapping if anonymization was applied
    if ANONYMIZE_LLM_DATA and privacy_mapping:
        mapping_file_path = os.path.join(contact_folder, 'privacy_mapping.json')
        with open(mapping_file_path, 'w', encoding='utf-8') as f:
            json.dump(privacy_mapping, f, indent=2, ensure_ascii=False)
    
    return llm_file_path, conversation_metadata


def create_llm_master_files(llm_conversations_data, output_folder, min_message_count):
    """
    Create master index and summary files for LLM processing
    """
    llm_folder = os.path.join(output_folder, "_llm_ready")
    os.makedirs(llm_folder, exist_ok=True)
    
    # Master Index - Full index of all conversations
    master_index = {
        "metadata": {
            "total_conversations": len(llm_conversations_data),
            "generated_at": datetime.now().isoformat(),
            "format": "llm_ready_conversations",
            "min_message_count": min_message_count,
            "privacy_enabled": ANONYMIZE_LLM_DATA,
            "includes_recent_interactions": True,
            "recent_interactions_count": RECENT_INTERACTIONS_COUNT
        },
        "conversations": []
    }
    
    # Conversation Summaries - Quick stats for each conversation
    conversation_summaries = {
        "metadata": {
            "total_conversations": len(llm_conversations_data),
            "generated_at": datetime.now().isoformat(),
            "format": "llm_conversation_summaries",
            "privacy_enabled": ANONYMIZE_LLM_DATA,
            "includes_recent_interactions": True
        },
        "summaries": []
    }
    
    # Master privacy mapping
    global_mappings = get_global_mappings()
    all_privacy_mappings = {
        "metadata": {
            "total_conversations": len(llm_conversations_data),
            "generated_at": datetime.now().isoformat()
        },
        **global_mappings,
        "mappings": {}
    }
    
    # Overall statistics
    total_messages = 0
    total_sent = 0
    total_received = 0
    most_active_contacts = []
    
    for contact_name, data in sorted(llm_conversations_data.items()):
        file_path = data['file_path']
        recent_file_path = data.get('recent_file_path')
        metadata = data['metadata']
        interaction_analysis = data.get('interaction_analysis', {})
        
        index_name = get_person_placeholder(contact_name) if ANONYMIZE_LLM_DATA else contact_name
        
        # Add to master index
        index_entry = {
            "contact_name": index_name,
            "file_path": file_path,
            "recent_interactions_file": recent_file_path,
            "total_messages": metadata.get('total_messages', 0),
            "date_range": metadata.get('date_range', 'Unknown'),
        }
        
        # Add interaction analysis summary if available
        if interaction_analysis:
            index_entry["recent_interaction_summary"] = {
                "messages_analyzed": interaction_analysis.get('message_count', 0),
                "response_pairs": interaction_analysis.get('response_pairs', 0),
                "interaction_ratio": interaction_analysis.get('interaction_ratio', 0),
                "timespan_hours": interaction_analysis.get('timespan_hours', 0)
            }
        
        if ANONYMIZE_LLM_DATA:
            # Use placeholders for phone numbers
            if 'phone_numbers' in data:
                anonymized_phones = []
                for i, _ in enumerate(data['phone_numbers']):
                    anonymized_phones.append(get_phone_placeholder(contact_name, i+1))
                index_entry['phone_numbers'] = anonymized_phones
            
            # Use placeholders for emails if present
            if 'emails' in data:
                anonymized_emails = []
                for i, _ in enumerate(data['emails']):
                    anonymized_emails.append(get_email_placeholder(contact_name, i+1))
                index_entry['emails'] = anonymized_emails
            
            # Use placeholder for most active number
            if metadata.get('most_active_number'):
                index_entry['most_active_number'] = get_phone_placeholder(contact_name, 1)
        else:
            # Use real data
            if 'phone_numbers' in data:
                index_entry['phone_numbers'] = data['phone_numbers']
            if 'emails' in data:
                index_entry['emails'] = data['emails']
            if metadata.get('most_active_number'):
                index_entry['most_active_number'] = metadata.get('most_active_number')
        
        if 'organization' in data:
            index_entry['organization'] = data['organization']
        
        master_index["conversations"].append(index_entry)
        
        # Add to conversation summaries
        summary_entry = {
            "contact_name": index_name,
            "file_path": file_path,
            "recent_interactions_file": recent_file_path
        }
        
        # Anonymize metadata for summary if needed
        if ANONYMIZE_LLM_DATA:
            anonymized_metadata = json.loads(json.dumps(metadata))
            if 'most_active_number' in anonymized_metadata:
                anonymized_metadata['most_active_number'] = get_phone_placeholder(contact_name, 1)
            if 'phone_number_usage' in anonymized_metadata:
                phone_usage = {}
                for i, (_, count) in enumerate(anonymized_metadata['phone_number_usage'].items()):
                    phone_usage[get_phone_placeholder(contact_name, i+1)] = count
                anonymized_metadata['phone_number_usage'] = phone_usage
            summary_entry["conversation_metadata"] = anonymized_metadata
            summary_entry["interaction_analysis"] = interaction_analysis  # Interaction analysis doesn't need anonymization
        else:
            summary_entry["conversation_metadata"] = metadata
            summary_entry["interaction_analysis"] = interaction_analysis
            
        conversation_summaries["summaries"].append(summary_entry)
        
        # Store privacy mapping in master file
        if ANONYMIZE_LLM_DATA:
            # Check for individual privacy mapping file
            safe_name = re.sub(r'[\\/*?:"<>|]', '_', contact_name)
            mapping_file_path = os.path.join(output_folder, safe_name, 'privacy_mapping.json')
            
            if os.path.exists(mapping_file_path):
                try:
                    with open(mapping_file_path, 'r', encoding='utf-8') as f:
                        mapping_data = json.load(f)
                        all_privacy_mappings["mappings"][contact_name] = mapping_data
                except Exception as e:
                    print(f"  ! Error reading privacy mapping for {contact_name}: {str(e)}")
        
        # Update overall stats
        msg_count = metadata.get('total_messages', 0)
        total_messages += msg_count
        total_sent += metadata.get('sent_messages', 0)
        total_received += metadata.get('received_messages', 0)
        
        most_active_contacts.append({
            "name": index_name if ANONYMIZE_LLM_DATA else contact_name,
            "message_count": msg_count
        })
    
    # Sort by most active
    most_active_contacts.sort(key=lambda x: x['message_count'], reverse=True)
    
    # Add overall statistics to metadata
    master_index["metadata"]["overall_stats"] = {
        "total_messages_all_conversations": total_messages,
        "total_sent_messages": total_sent,
        "total_received_messages": total_received,
        "average_messages_per_conversation": round(total_messages / len(llm_conversations_data), 1) if llm_conversations_data else 0,
        "most_active_contacts": most_active_contacts[:10]  # Top 10
    }
    
    # Write files
    master_index_path = os.path.join(llm_folder, "master_index.json")
    with open(master_index_path, 'w', encoding='utf-8') as f:
        json.dump(master_index, f, indent=2, ensure_ascii=False)
    
    summaries_path = os.path.join(llm_folder, "conversation_summaries.json")
    with open(summaries_path, 'w', encoding='utf-8') as f:
        json.dump(conversation_summaries, f, indent=2, ensure_ascii=False)
    
    # Write the master privacy mapping file if anonymization is enabled
    if ANONYMIZE_LLM_DATA:
        mapping_path = os.path.join(llm_folder, PRIVACY_MAPPING_FILE)
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(all_privacy_mappings, f, indent=2, ensure_ascii=False)
    
    return master_index_path, summaries_path 