"""
LLM Processor Module

This module orchestrates both main LLM conversation processing and recent interactions
analysis, providing a unified interface for the contacts exporter.
"""

import re
import os
from datetime import datetime

# Import from our specialized modules
from privacy_handler import (
    set_privacy_enabled,
    reset_person_mapping,
    ANONYMIZE_LLM_DATA,
    RECENT_INTERACTIONS_FILENAME
)
from llm_conversation import (
    create_llm_conversation_file,
    create_llm_master_files,
    optimize_messages_for_llm,
    generate_conversation_metadata
)
from recent_interactions import (
    create_recent_interactions_file
)


def create_llm_files_for_contact(contact_name, contact_data, messages, output_folder):
    """
    Create both LLM conversation files for a single contact:
    1. Main LLM conversation file (optimized)
    2. Recent interactions file (preserved formatting)
    
    Returns a unified result structure for the master index.
    """
    if not messages:
        return None, None
    
    # Create main LLM conversation file
    llm_file_path, conversation_metadata = create_llm_conversation_file(
        contact_name, contact_data, messages, output_folder
    )
    
    # Create recent interactions file
    recent_file_path, interaction_analysis = create_recent_interactions_file(
        contact_name, contact_data, messages, output_folder
    )
    
    # Return unified result structure
    result_data = {
        'main_file': llm_file_path,
        'recent_file': recent_file_path,
        'conversation_metadata': conversation_metadata,
        'interaction_analysis': interaction_analysis
    }
    
    return result_data


def process_contact_for_llm_files(contact_name, phone_numbers, vcard, temp_export_dir, output_folder, 
                                  consolidate_contact_messages_func):
    """
    Process a single contact for both LLM file types
    This function is designed to be called from contacts_exporter.py
    """
    # Get consolidated messages
    messages, phone_usage = consolidate_contact_messages_func(contact_name, phone_numbers, temp_export_dir)
    
    if not messages:
        return None, None
    
    # Extract contact data from vcard for context
    contact_data = {'phone_numbers': phone_numbers, 'phone_usage': phone_usage}
    
    if hasattr(vcard, 'email'):
        contact_data['emails'] = [{'address': email.value} for email in vcard.email_list]
    
    if hasattr(vcard, 'org'):
        contact_data['organization'] = vcard.org.value[0]
    
    if hasattr(vcard, 'title'):
        contact_data['title'] = vcard.title.value
    
    # Create both LLM files
    llm_result = create_llm_files_for_contact(
        contact_name, contact_data, messages, output_folder
    )
    
    if not llm_result:
        return None, None
    
    # Return data for master index with updated file paths
    safe_contact_name = re.sub(r'[\\/*?:"<>|]', '_', contact_name)
    llm_data = {
        'file_path': f"{safe_contact_name}/conversation_llm.json",
        'recent_file_path': f"{safe_contact_name}/{RECENT_INTERACTIONS_FILENAME}",
        'metadata': llm_result['conversation_metadata'],
        'interaction_analysis': llm_result['interaction_analysis'],
        'phone_numbers': phone_numbers
    }
    
    if 'emails' in contact_data:
        llm_data['emails'] = [email['address'] for email in contact_data['emails']]
    if 'organization' in contact_data:
        llm_data['organization'] = contact_data['organization']
    
    return llm_result['main_file'], llm_data


# Re-export commonly used functions for backward compatibility
__all__ = [
    'set_privacy_enabled',
    'reset_person_mapping', 
    'create_llm_master_files',
    'optimize_messages_for_llm',
    'generate_conversation_metadata',
    'create_llm_files_for_contact',
    'process_contact_for_llm_files',
    'ANONYMIZE_LLM_DATA',
    'RECENT_INTERACTIONS_FILENAME'
] 