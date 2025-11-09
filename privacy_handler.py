"""
Privacy Handler Module

This module handles privacy-aware processing and anonymization for LLM data consumption.
It provides name/phone/email anonymization and privacy mapping functionality.
"""

import re
import json
import os
from datetime import datetime

# Privacy Configuration for LLM Data
ANONYMIZE_LLM_DATA = True  # Enable/disable privacy features
PERSON_PLACEHOLDER_PREFIX = "[[PERSON_"  # Prefix for person placeholders (will become [[PERSON_1]], [[PERSON_2]], etc.)
PHONE_PLACEHOLDER_PREFIX = "[[PHONE_"  # Prefix for phone number placeholders
EMAIL_PLACEHOLDER_PREFIX = "[[EMAIL_"  # Prefix for email placeholders
SOCIAL_PLACEHOLDER_PREFIX = "[[SOCIAL_MEDIA_"  # Prefix for social media placeholders
ORGANIZATION_PLACEHOLDER_PREFIX = "[[ORGANIZATION_"  # Prefix for organization placeholders
ADDRESS_PLACEHOLDER_PREFIX = "[[ADDRESS_"  # Prefix for address placeholders
PASSWORD_PLACEHOLDER = "[[CREDENTIALS]]"  # Placeholder for passwords and credentials
PRIVACY_MAPPING_FILE = "privacy_mapping.json"  # File containing the mapping data

# Recent Interactions Configuration
RECENT_INTERACTIONS_COUNT = 75  # Number of recent messages to include in interactions file
RECENT_INTERACTIONS_FILENAME = "conversation_recent_interactions.json"  # Filename for recent interactions file

# Global ID counters and mappings
_person_id_counter = 0
_person_name_to_id = {}  # Maps actual names to person IDs

_organization_id_counter = 0
_organization_to_id = {}  # Maps organization names to org IDs

_social_media_id_counter = 0
_social_media_to_id = {}  # Maps social media handles to social IDs

_address_id_counter = 0
_address_to_id = {}  # Maps addresses to address IDs

# Regex patterns for sensitive data detection
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
PARTIAL_EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\b'  # Catches partial emails like user@gmail
PHONE_PATTERN = r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
SOCIAL_MEDIA_PATTERNS = [
    r'(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)',  # Twitter/X handles
    r'(?:instagram\.com)/([A-Za-z0-9_\.]+)',     # Instagram handles
    r'(?:linkedin\.com/in)/([A-Za-z0-9_-]+)',    # LinkedIn profiles
    r'(?:facebook\.com)/([A-Za-z0-9\.]+)',       # Facebook profiles
    r'(?:github\.com)/([A-Za-z0-9_-]+)',         # GitHub usernames
    r'@([A-Za-z0-9_]+)'                          # Generic @ mentions
]

# Enhanced username patterns to catch directly mentioned usernames
USERNAME_CONTEXT_PATTERNS = [
    r'github\s+username\s+is\s+([A-Za-z0-9_-]{3,})',        # GitHub username is X
    r'gh\s+username\s+is\s+([A-Za-z0-9_-]{3,})',            # gh username is X
    r'github\s+user\s+is\s+([A-Za-z0-9_-]{3,})',            # GitHub user is X
    r'twitter\s+handle\s+is\s+@?([A-Za-z0-9_]{3,})',        # Twitter handle is X
    r'instagram\s+(?:is|username)\s+@?([A-Za-z0-9_\.]{3,})', # Instagram is X or username is X
    r'ig\s+(?:is|username)\s+@?([A-Za-z0-9_\.]{3,})',        # ig is X or username is X 
    r'linkedin\s+(?:is|profile)\s+([A-Za-z0-9_-]{3,})',      # LinkedIn is X or profile is X
    r'facebook\s+(?:is|username)\s+([A-Za-z0-9\.]{3,})',     # Facebook is X or username is X
    r'discord\s+(?:is|tag)\s+([A-Za-z0-9_#\.]{3,})',         # Discord is X or tag is X
    r'telegram\s+(?:is|username)\s+@?([A-Za-z0-9_]{3,})',    # Telegram is X or username is X
    r'my\s+username\s+(?:is|:)\s+([A-Za-z0-9_\.-]{3,})',      # My username is X
    r'username\s+(?:is|:)\s+([A-Za-z0-9_\.-]{3,})',           # Username is X (general)
    r'my\s+github\s+username\s+is\s+([A-Za-z0-9_-]{3,})',     # My GitHub username is X
    r'my\s+twitter\s+(?:handle|username)\s+is\s+@?([A-Za-z0-9_]{3,})'  # My Twitter handle/username is X
]

# Password detection patterns (look for context followed by potential password)
PASSWORD_PATTERNS = [
    r'password\s+(?:is|:)\s+([A-Za-z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?]{6,})',  # "password is X" or "password: X"
    r'pwd\s+(?:is|:)\s+([A-Za-z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?]{6,})',       # "pwd is X" or "pwd: X"
    r'credentials\s+(?:are|is|:)\s+([A-Za-z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?]{6,})',  # "credentials are X"
    r'login\s+(?:is|:)\s+([A-Za-z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?]{6,})',     # "login is X" or "login: X"
    r'passw[o0]rd\s*[=:]\s*([A-Za-z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?]{6,})',   # password=X or password:X
    r'the\s+password\s+(?:is|:)\s+([A-Za-z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?]{6,})',  # "the password is X"
]


def set_privacy_enabled(enabled):
    """Set whether privacy features are enabled globally."""
    global ANONYMIZE_LLM_DATA
    ANONYMIZE_LLM_DATA = enabled


def get_person_id(contact_name):
    """
    Get a unique person ID for a contact name, creating one if it doesn't exist.
    This ensures the same person always gets the same ID across all files.
    """
    global _person_id_counter, _person_name_to_id
    
    if contact_name not in _person_name_to_id:
        _person_id_counter += 1
        _person_name_to_id[contact_name] = _person_id_counter
    
    return _person_name_to_id[contact_name]


def get_person_placeholder(contact_name):
    """
    Get the privacy placeholder for a contact name (e.g., [[PERSON_1]])
    """
    if not ANONYMIZE_LLM_DATA:
        return contact_name
    
    person_id = get_person_id(contact_name)
    return f"{PERSON_PLACEHOLDER_PREFIX}{person_id}]]"


def get_organization_id(org_name):
    """
    Get a unique organization ID for an organization name, creating one if it doesn't exist.
    """
    global _organization_id_counter, _organization_to_id
    
    if org_name not in _organization_to_id:
        _organization_id_counter += 1
        _organization_to_id[org_name] = _organization_id_counter
    
    return _organization_to_id[org_name]


def get_organization_placeholder(org_name):
    """
    Get the privacy placeholder for an organization (e.g., [[ORGANIZATION_1]])
    """
    if not ANONYMIZE_LLM_DATA or not org_name:
        return org_name
    
    org_id = get_organization_id(org_name)
    return f"{ORGANIZATION_PLACEHOLDER_PREFIX}{org_id}]]"


def get_social_media_id(handle):
    """
    Get a unique social media ID for a handle/username, creating one if it doesn't exist.
    """
    global _social_media_id_counter, _social_media_to_id
    
    if handle not in _social_media_to_id:
        _social_media_id_counter += 1
        _social_media_to_id[handle] = _social_media_id_counter
    
    return _social_media_to_id[handle]


def get_social_media_placeholder(handle):
    """
    Get the privacy placeholder for a social media handle (e.g., [[SOCIAL_MEDIA_1]])
    """
    if not ANONYMIZE_LLM_DATA or not handle:
        return handle
    
    social_id = get_social_media_id(handle)
    return f"{SOCIAL_PLACEHOLDER_PREFIX}{social_id}]]"


def get_address_id(address):
    """
    Get a unique address ID for an address, creating one if it doesn't exist.
    """
    global _address_id_counter, _address_to_id
    
    if address not in _address_to_id:
        _address_id_counter += 1
        _address_to_id[address] = _address_id_counter
    
    return _address_to_id[address]


def get_address_placeholder(address):
    """
    Get the privacy placeholder for an address (e.g., [[ADDRESS_1]])
    """
    if not ANONYMIZE_LLM_DATA or not address:
        return address
    
    address_id = get_address_id(address)
    return f"{ADDRESS_PLACEHOLDER_PREFIX}{address_id}]]"


def get_phone_placeholder(contact_name, phone_index):
    """
    Get the privacy placeholder for a phone number using hierarchical format (e.g., [[PHONE_74_1]])
    """
    if not ANONYMIZE_LLM_DATA:
        return None
    
    person_id = get_person_id(contact_name)
    return f"{PHONE_PLACEHOLDER_PREFIX}{person_id}_{phone_index}]]"


def get_email_placeholder(contact_name, email_index):
    """
    Get the privacy placeholder for an email using hierarchical format (e.g., [[EMAIL_74_1]])
    """
    if not ANONYMIZE_LLM_DATA:
        return None
    
    person_id = get_person_id(contact_name)
    return f"{EMAIL_PLACEHOLDER_PREFIX}{person_id}_{email_index}]]"


def reset_person_mapping():
    """
    Reset all global mappings. Useful for testing or when starting fresh.
    """
    global _person_id_counter, _person_name_to_id
    global _organization_id_counter, _organization_to_id
    global _social_media_id_counter, _social_media_to_id
    global _address_id_counter, _address_to_id
    
    _person_id_counter = 0
    _person_name_to_id = {}
    
    _organization_id_counter = 0
    _organization_to_id = {}
    
    _social_media_id_counter = 0
    _social_media_to_id = {}
    
    _address_id_counter = 0
    _address_to_id = {}


def anonymize_data_for_llm(data, contact_name):
    """
    Anonymize sensitive data for LLM processing while maintaining a mapping for restoration
    """
    if not ANONYMIZE_LLM_DATA:
        return data, None
    
    # Create mapping dictionary to store original values
    mapping = {
        "name": contact_name,
        "person_id": get_person_id(contact_name),  # Store the unique person ID
        "person_placeholder": get_person_placeholder(contact_name),  # Store the placeholder used
        "phones": {},
        "emails": {},
        "organizations": {},
        "social_media": {},
        "addresses": {},
        "credentials": {},
        "original_data": {}
    }
    
    # Create a copy of the data to modify
    anonymized = json.loads(json.dumps(data))
    
    # Extract first name for more comprehensive replacement
    # This handles cases where only the first name is used in messages
    first_name = contact_name.split()[0] if contact_name else ""
    
    # Anonymize contact information
    if "contact" in anonymized:
        # Save original contact info
        mapping["original_data"]["contact"] = json.loads(json.dumps(anonymized["contact"]))
        
        # Replace contact name with placeholder
        anonymized["contact"]["name"] = get_person_placeholder(contact_name)
        
        # Create unique placeholders for each phone number
        if "phone_numbers" in anonymized["contact"]:
            for i, phone in enumerate(anonymized["contact"]["phone_numbers"]):
                placeholder = get_phone_placeholder(contact_name, i+1)
                mapping["phones"][placeholder] = phone
                anonymized["contact"]["phone_numbers"][i] = placeholder
        
        # Create unique placeholders for each email
        if "emails" in anonymized["contact"]:
            for i, email in enumerate(anonymized["contact"]["emails"]):
                placeholder = get_email_placeholder(contact_name, i+1)
                mapping["emails"][placeholder] = email
                anonymized["contact"]["emails"][i] = placeholder
        
        # Anonymize organization if present
        if "organization" in anonymized["contact"]:
            org_placeholder = get_organization_placeholder(anonymized["contact"]["organization"])
            mapping["organizations"][org_placeholder] = anonymized["contact"]["organization"]
            anonymized["contact"]["organization"] = org_placeholder
        
        # Remove addresses if present
        if "addresses" in anonymized["contact"]:
            for i, address in enumerate(anonymized["contact"]["addresses"]):
                addr_placeholder = get_address_placeholder(address)
                mapping["addresses"][addr_placeholder] = address
            del anonymized["contact"]["addresses"]
    
    # Anonymize phone numbers in conversation metadata
    if "conversation_metadata" in anonymized:
        # Save original metadata
        mapping["original_data"]["metadata"] = json.loads(json.dumps(anonymized["conversation_metadata"]))
        
        # Replace phone numbers in metadata
        if "most_active_number" in anonymized["conversation_metadata"]:
            phone = anonymized["conversation_metadata"]["most_active_number"]
            # Find or create placeholder for this phone
            placeholder = None
            for ph_placeholder, ph_value in mapping["phones"].items():
                if ph_value == phone:
                    placeholder = ph_placeholder
                    break
                    
            if not placeholder:
                placeholder = get_phone_placeholder(contact_name, len(mapping['phones'])+1)
                mapping["phones"][placeholder] = phone
                
            anonymized["conversation_metadata"]["most_active_number"] = placeholder
        
        # Replace phone numbers in phone_number_usage
        if "phone_number_usage" in anonymized["conversation_metadata"]:
            phone_usage = {}
            for phone, count in anonymized["conversation_metadata"]["phone_number_usage"].items():
                # Find or create placeholder for this phone
                placeholder = None
                for ph_placeholder, ph_value in mapping["phones"].items():
                    if ph_value == phone:
                        placeholder = ph_placeholder
                        break
                        
                if not placeholder:
                    placeholder = get_phone_placeholder(contact_name, len(mapping['phones'])+1)
                    mapping["phones"][placeholder] = phone
                    
                phone_usage[placeholder] = count
                
            anonymized["conversation_metadata"]["phone_number_usage"] = phone_usage
    
    # Anonymize message content (works for both main messages and recent_messages)
    message_keys = ["messages", "recent_messages"]
    for msg_key in message_keys:
        if msg_key in anonymized:
            # Replace sensitive information in message content with placeholders
            for msg in anonymized[msg_key]:
                if "content" in msg:
                    content = msg["content"]
                    
                    # Replace the full contact name with placeholder (case-insensitive)
                    content = re.sub(re.escape(contact_name), get_person_placeholder(contact_name), content, flags=re.IGNORECASE)
                    
                    # Replace just the first name if it's different from the full name
                    # Use word boundary to avoid replacing partial matches
                    if first_name and first_name != contact_name and len(first_name) > 1:
                        # Create pattern that matches the first name as a whole word (case-insensitive)
                        pattern = r'\b' + re.escape(first_name) + r'\b'
                        content = re.sub(pattern, get_person_placeholder(contact_name), content, flags=re.IGNORECASE)
                    
                    # Replace organization names in content if present
                    for org_placeholder, org_value in mapping["organizations"].items():
                        if org_value and len(org_value) > 2:  # Only replace if meaningful
                            content = content.replace(org_value, org_placeholder)
                    
                    # Replace any phone numbers in content
                    for placeholder, phone in mapping["phones"].items():
                        content = content.replace(phone, placeholder)
                    
                    # Replace known emails in content
                    for placeholder, email in mapping["emails"].items():
                        content = content.replace(email, placeholder)
                    
                    # Find and replace additional phone numbers in content using regex
                    phone_matches = re.findall(PHONE_PATTERN, content)
                    for phone_match in phone_matches:
                        # Check if we already have this phone in our mapping
                        existing = False
                        for _, phone in mapping["phones"].items():
                            if phone_match in phone:
                                existing = True
                                break
                        
                        if not existing:
                            placeholder = get_phone_placeholder(contact_name, len(mapping['phones'])+1)
                            mapping["phones"][placeholder] = phone_match
                            content = content.replace(phone_match, placeholder)
                    
                    # Find and replace additional emails in content using regex
                    email_matches = re.findall(EMAIL_PATTERN, content)
                    for email_match in email_matches:
                        # Check if we already have this email in our mapping
                        existing = False
                        for _, email in mapping["emails"].items():
                            if email_match == email:
                                existing = True
                                break
                        
                        if not existing:
                            placeholder = get_email_placeholder(contact_name, len(mapping['emails'])+1)
                            mapping["emails"][placeholder] = email_match
                            content = content.replace(email_match, placeholder)
                    
                    # Find and replace partial emails (like user@gmail without .com)
                    partial_email_matches = re.findall(PARTIAL_EMAIL_PATTERN, content)
                    for partial_email_match in partial_email_matches:
                        # Skip if this was already handled by the full email pattern
                        already_handled = False
                        for _, email in mapping["emails"].items():
                            if partial_email_match in email:
                                already_handled = True
                                break
                        
                        if not already_handled:
                            placeholder = get_email_placeholder(contact_name, len(mapping['emails'])+1)
                            mapping["emails"][placeholder] = partial_email_match
                            content = content.replace(partial_email_match, placeholder)
                    
                    # Find and replace social media handles/links
                    for pattern in SOCIAL_MEDIA_PATTERNS:
                        social_matches = re.findall(pattern, content)
                        for social_match in social_matches:
                            full_match = re.search(f"({pattern})", content)
                            if full_match:
                                full_text = full_match.group(0)
                                placeholder = get_social_media_placeholder(social_match)
                                mapping["social_media"][placeholder] = full_text
                                content = content.replace(full_text, placeholder)
                    
                    # Find and replace directly mentioned usernames using enhanced patterns
                    for pattern in USERNAME_CONTEXT_PATTERNS:
                        try:
                            username_matches = re.findall(pattern, content, re.IGNORECASE)
                            for username in username_matches:
                                if username:
                                    # Get unique placeholder for this username
                                    placeholder = get_social_media_placeholder(username)
                                    mapping["social_media"][placeholder] = username
                                    
                                    # Create the regex to find the exact match including context
                                    context_pattern = pattern.replace("([A-Za-z0-9", "([A-Za-z0-9")  # Ensure we match the same pattern
                                    match_with_context = re.search(context_pattern, content, re.IGNORECASE)
                                    
                                    if match_with_context:
                                        full_match = match_with_context.group(0)
                                        replacement = full_match.replace(username, placeholder)
                                        content = content.replace(full_match, replacement)
                        except Exception as e:
                            # If there's an error with a particular pattern, continue with other patterns
                            print(f"  ! Error with pattern {pattern}: {str(e)}")
                            continue
                    
                    # Find and replace passwords and credentials
                    for pattern in PASSWORD_PATTERNS:
                        password_matches = re.findall(pattern, content, re.IGNORECASE)
                        for pwd_match in password_matches:
                            # Don't store the password itself in the mapping to enhance security
                            # Just store a note that a password was found at this location
                            cred_key = f"{PASSWORD_PLACEHOLDER}_{len(mapping['credentials'])+1}"
                            mapping["credentials"][cred_key] = "Password redacted for security"
                            
                            # Replace the exact password match with a placeholder
                            content = re.sub(
                                f"({re.escape(pwd_match)})", 
                                PASSWORD_PLACEHOLDER, 
                                content
                            )
                    
                    # Update the message content
                    msg["content"] = content
    
    return anonymized, mapping


def get_global_mappings():
    """
    Get all global mappings for master files
    """
    return {
        "global_person_mapping": _person_name_to_id,
        "global_organization_mapping": _organization_to_id,
        "global_social_media_mapping": _social_media_to_id,
        "global_address_mapping": _address_to_id
    } 