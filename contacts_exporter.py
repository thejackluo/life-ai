import vobject
import os
import sys
import re
import subprocess
import shutil
import json
import argparse
from dateutil.parser import parse
from datetime import datetime, timedelta
import emoji

# Import LLM processing functionality from modular structure
from llm_processor import (
    set_privacy_enabled, 
    create_llm_master_files,
    optimize_messages_for_llm,
    generate_conversation_metadata,
    reset_person_mapping,
    process_contact_for_llm_files,
    ANONYMIZE_LLM_DATA,
    RECENT_INTERACTIONS_FILENAME
)

# Configuration
MAIN_OUTPUT_FOLDER = "data"
ALL_MESSAGES_FOLDER = "_all_messages"
SUMMARY_FOLDER = "_summary"
ATTACHMENT_FOLDER = "attachments"
LLM_FOLDER = "_llm_ready"  # Folder for LLM-ready conversation files
LLM_INDEX_FILE = "master_index.json"  # Master index file name
MIN_MESSAGE_COUNT = 10  # Only export contacts with this many messages or more

# Message file configuration
CREATE_INDIVIDUAL_MESSAGE_FILES = False  # Set to True if you need individual files for debugging
CREATE_CONSOLIDATED_MESSAGE_FILES = True  # Always create the unified timeline

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

def count_messages_in_file(file_path):
    """
    Count the number of messages in a message text file.
    Messages are typically separated by timestamps.
    """
    if not os.path.exists(file_path):
        return 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count message blocks - each message typically starts with a timestamp
        # Look for patterns like "Jan 15, 2025  2:30:15 PM" or similar
        timestamp_patterns = [
            r'\b\w{3}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\b',  # Jan 15, 2025  2:30:15 PM
            r'\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M',        # 1/15/25 2:30:15 PM
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',                        # 2025-01-15 14:30:15
        ]
        
        message_count = 0
        for pattern in timestamp_patterns:
            matches = re.findall(pattern, content)
            if matches:
                message_count = max(message_count, len(matches))
        
        # Fallback: count by line breaks if no timestamps found
        if message_count == 0:
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            # Estimate messages (very rough - actual messages might be multi-line)
            message_count = max(1, len(lines) // 3)  # Assume ~3 lines per message on average
        
        return message_count
        
    except Exception as e:
        print(f"  ! Error counting messages in {file_path}: {str(e)}")
        return 0

def get_total_message_count_for_contact(phone_numbers, temp_export_dir):
    """
    Get the total message count across all phone numbers for a contact
    """
    total_count = 0
    
    for phone_number in phone_numbers:
        # Find the message file in temp export
        phone_clean = phone_number.replace('+', '')
        possible_filenames = [
            f"{phone_number}.txt",
            f"{phone_clean}.txt"
        ]
        
        for filename in possible_filenames:
            file_path = os.path.join(temp_export_dir, filename)
            if os.path.exists(file_path):
                count = count_messages_in_file(file_path)
                total_count += count
                break  # Found the file, don't check other variations
    
    return total_count

def normalize_phone_number(phone_str):
    """
    Normalize phone number to match iMessage exporter format (+1xxxxxxxxxx)
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'[^\d]', '', phone_str)
    
    # Handle different phone number formats
    if len(digits_only) == 10:
        # US number without country code
        return f"+1{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        # US number with country code
        return f"+{digits_only}"
    elif digits_only.startswith('1') and len(digits_only) > 11:
        # Handle cases like +15713580363
        return f"+{digits_only}"
    else:
        # International number or other format
        return f"+{digits_only}" if not phone_str.startswith('+') else phone_str

def is_group_chat_filename(filename):
    """
    Determine if a filename represents a group chat vs individual conversation
    """
    # Remove .txt extension
    name = filename.replace('.txt', '')
    
    # Group chat indicators:
    # 1. Contains " - " followed by numbers (group chat IDs)
    if re.search(r' - \d+$', name):
        return True
    
    # 2. Contains multiple phone numbers (comma separated)
    if ',' in name:
        return True
    
    # 3. Contains spaces and isn't just a phone number or email
    if ' ' in name and not re.match(r'^\+?\d+$', name) and '@' not in name:
        return True
    
    # Individual conversation indicators:
    # 1. Single phone number format
    if re.match(r'^\+?\d{10,15}$', name):
        return False
    
    # 2. Single email address
    if re.match(r'^[^@]+@[^@]+\.[^@]+$', name):
        return False
    
    # 3. Short codes (like 12345)
    if re.match(r'^\d{3,6}$', name):
        return False
    
    # Default to group chat if uncertain
    return True

def export_messages_including_groups(temp_export_dir):
    """
    Export all messages, including both individual conversations and group chats
    """
    try:
        print("Exporting all messages (individual + group chats)...")
        
        # Run imessage-exporter to export all messages to temp directory
        cmd = [
            'imessage-exporter',
            '--format', 'txt',
            '--export-path', temp_export_dir
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Warning: imessage-exporter returned code {result.returncode}")
            print(f"stderr: {result.stderr}")
        
        # Categorize all message files
        individual_files = []
        group_files = []
        
        if os.path.exists(temp_export_dir):
            for filename in os.listdir(temp_export_dir):
                if filename.endswith('.txt'):
                    if is_group_chat_filename(filename):
                        group_files.append(filename)
                    else:
                        individual_files.append(filename)
        
        print(f"Found {len(individual_files)} individual conversations")
        print(f"Found {len(group_files)} group chats")
        
        return individual_files, group_files
        
    except Exception as e:
        print(f"Error exporting messages: {str(e)}")
        return [], []

def get_phone_type_from_vcard(vcard, phone_number):
    """
    Get the type/label for a phone number from the vcard
    """
    if hasattr(vcard, 'tel'):
        for tel in vcard.tel_list:
            normalized = normalize_phone_number(tel.value)
            if normalized == phone_number:
                try:
                    params = str(tel.params["TYPE"]).replace("[","").replace("]","").replace("'","").lower()
                    return params
                except KeyError:
                    return "phone"
    return "phone"

def copy_message_file_for_contact(phone_number, contact_folder, contact_name, vcard, temp_export_dir):
    """
    Copy the message file for a specific phone number to the contact's folder
    """
    # Find the message file in temp export
    phone_clean = phone_number.replace('+', '')
    possible_filenames = [
        f"{phone_number}.txt",
        f"{phone_clean}.txt"
    ]
    
    for filename in possible_filenames:
        source_path = os.path.join(temp_export_dir, filename)
        if os.path.exists(source_path):
            # Get phone type for filename
            phone_type = get_phone_type_from_vcard(vcard, phone_number)
            
            # Create descriptive filename
            dest_filename = f"messages_{phone_number}_{phone_type}.txt"
            dest_path = os.path.join(contact_folder, dest_filename)
            
            # Copy the file
            shutil.copy2(source_path, dest_path)
            print(f"  ✓ Copied messages for {phone_number} ({phone_type})")
            return dest_filename
    
    print(f"  ! No messages found for {phone_number}")
    return None

def read_vcf_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading VCF file: {str(e)}", file=sys.stderr)
        sys.exit(1)

def get_last_message_info(messages):
    """
    Get information about the last message in a conversation
    Returns: dict with last_message_date, last_message_sender, last_message_preview
    """
    if not messages:
        return None
    
    # Messages should already be sorted chronologically
    last_message = messages[-1]
    
    # Extract the info
    last_message_info = {
        'last_message_date': last_message.get('timestamp', ''),
        'last_message_sender': last_message.get('sender', 'unknown'),
        'last_message_preview': last_message.get('content', '')[:100]  # First 100 chars
    }
    
    # Try to format the date nicely
    try:
        parsed_date = parse(last_message_info['last_message_date'])
        last_message_info['last_message_date_formatted'] = parsed_date.strftime('%Y-%m-%d')
        last_message_info['last_message_timestamp'] = parsed_date.isoformat()
    except Exception:
        # If parsing fails, use the raw timestamp
        last_message_info['last_message_date_formatted'] = last_message_info['last_message_date']
        last_message_info['last_message_timestamp'] = last_message_info['last_message_date']
    
    return last_message_info

def vcard_to_json(vcard, contact_folder, message_files, conversation_metadata=None, last_message_info=None):
    """
    Convert vCard to structured JSON data with optional conversation insights
    """
    contact_data = {
        "name": vcard.fn.value,
        "contact_information": {},
        "personal_information": {},
        "professional_information": {},
        "online_presence": {},
        "additional_information": {},
        "message_history": [],
        "attachments": [],
        "metadata": {}
    }
    
    # Add conversation insights if available
    if conversation_metadata and conversation_metadata.get('total_messages', 0) > 0:
        contact_data["conversation_insights"] = conversation_metadata
    
    # Add last message information if available
    if last_message_info:
        contact_data["last_message_info"] = last_message_info

    # Add addressbook link if available
    if hasattr(vcard, 'x_abuid'):
        contact_data["metadata"]["addressbook_id"] = vcard.x_abuid.value
        contact_data["metadata"]["addressbook_link"] = f"addressbook://{vcard.x_abuid.value}"

    # Collect phone numbers for message export
    phone_numbers = []
    
    # Email addresses
    if hasattr(vcard, 'email'):
        contact_data["contact_information"]["emails"] = []
        for email in vcard.email_list:
            email_entry = {
                "address": email.value,
                "mailto_link": f"mailto:{email.value}"
            }
            try:
                email_entry["type"] = str(email.params["TYPE"]).replace("[","").replace("]","").replace("'","").lower()
            except KeyError:  
                email_entry["type"] = "email"
            contact_data["contact_information"]["emails"].append(email_entry)

    # Phone numbers
    if hasattr(vcard, 'tel'):
        contact_data["contact_information"]["phone_numbers"] = []
        for tel in vcard.tel_list:
            normalized_phone = normalize_phone_number(tel.value)
            phone_numbers.append(normalized_phone)
            phone_entry = {
                "number": normalized_phone,
                "tel_link": f"tel:{normalized_phone}",
                "original": tel.value
            }
            try:
                phone_entry["type"] = str(tel.params["TYPE"]).replace("[","").replace("]","").replace("'","").lower()
            except KeyError:
                phone_entry["type"] = "phone"
            contact_data["contact_information"]["phone_numbers"].append(phone_entry)

    # Personal information
    if hasattr(vcard, 'bday'):
        try:
            bday = parse(vcard.bday.value)
            contact_data["personal_information"]["birthday"] = {
                "date": bday.strftime("%Y-%m-%d"),
                "original": vcard.bday.value
            }
        except Exception:
            pass

    if hasattr(vcard, 'x_anniversary'):
        try:
            anniversary = parse(vcard.x_anniversary.value)
            contact_data["personal_information"]["anniversary"] = {
                "date": anniversary.strftime("%Y-%m-%d"),
                "original": vcard.x_anniversary.value
            }
        except Exception:
            pass

    if hasattr(vcard, 'x_gender'):
        gender = "Female" if vcard.x_gender.value.lower() == "f" else "Male"
        contact_data["personal_information"]["gender"] = {
            "display": gender,
            "original": vcard.x_gender.value
        }

    # Professional information
    if hasattr(vcard, 'org'):
        contact_data["professional_information"]["organization"] = vcard.org.value[0]

    if hasattr(vcard, 'title'):
        contact_data["professional_information"]["title"] = vcard.title.value

    if hasattr(vcard, 'role'):
        contact_data["professional_information"]["role"] = vcard.role.value

    # Social media and websites
    if hasattr(vcard, 'url'):
        contact_data["online_presence"]["urls"] = []
        urls_to_process = vcard.url_list if isinstance(vcard.url_list, list) else [vcard.url]
        
        for url in urls_to_process:
            url_value = url.value.strip()
            url_entry = {
                "url": url_value,
                "original": url_value
            }
            
            if 'linkedin.com' in url_value.lower():
                url_entry["platform"] = "linkedin"
            elif 'twitter.com' in url_value.lower():
                url_entry["platform"] = "twitter"
            elif 'instagram.com' in url_value.lower():
                url_entry["platform"] = "instagram"
            else:
                url_entry["platform"] = "website"
            
            contact_data["online_presence"]["urls"].append(url_entry)

    # Additional information
    if hasattr(vcard, 'note'):
        contact_data["additional_information"]["note"] = vcard.note.value

    if hasattr(vcard, 'lang'):
        contact_data["additional_information"]["language"] = vcard.lang.value

    if hasattr(vcard, 'geo'):
        contact_data["additional_information"]["location"] = vcard.geo.value

    if hasattr(vcard, 'adr'):
        contact_data["additional_information"]["addresses"] = []
        for adr in vcard.adr_list:
            address_str = str(adr.value).replace('\n', ' ')
            contact_data["additional_information"]["addresses"].append(address_str)

    # Handle photo attachment
    if hasattr(vcard, 'photo'):
        try:
            # Save photo in contact's folder
            attachment_folder = os.path.join(contact_folder, ATTACHMENT_FOLDER)
            os.makedirs(attachment_folder, exist_ok=True)
            
            file_name = f"photo.{vcard.photo.params['TYPE'][0].lower()}"
            photo_path = os.path.join(attachment_folder, file_name)
            
            with open(photo_path, 'wb') as fid:
                fid.write(vcard.photo.value)
            
            contact_data["attachments"].append({
                "type": "photo",
                "filename": file_name,
                "path": f"{ATTACHMENT_FOLDER}/{file_name}",
                "mime_type": vcard.photo.params['TYPE'][0].lower()
            })
        except Exception:
            pass

    # Add message history
    if message_files:
        for i, message_file in enumerate(message_files):
            if message_file:
                # Extract phone number and type from filename
                match = re.match(r'messages_(\+\d+)_(.+)\.txt', message_file)
                if match:
                    phone_num, phone_type = match.groups()
                    contact_data["message_history"].append({
                        "phone_number": phone_num,
                        "phone_type": phone_type,
                        "filename": message_file,
                        "path": message_file
                    })

    # Clean up empty sections
    contact_data = {k: v for k, v in contact_data.items() if v}
    
    return contact_data, phone_numbers

def create_summary_files(contact_data, output_folder):
    """
    Create summary index files in JSON format
    """
    summary_folder = os.path.join(output_folder, SUMMARY_FOLDER)
    os.makedirs(summary_folder, exist_ok=True)
    
    # All contacts summary
    all_contacts = {
        "metadata": {
            "total_contacts": len(contact_data),
            "generated_at": "2025-01-15T06:06:00Z",
            "format": "contacts_export_v2_json"
        },
        "contacts": []
    }
    
    contacts_with_messages = {
        "metadata": {
            "total_contacts_with_messages": 0,
            "generated_at": "2025-01-15T06:06:00Z",
            "format": "contacts_export_v2_json"
        },
        "contacts": []
    }
    
    contacts_with_msgs = 0
    
    for contact_name, data in sorted(contact_data.items()):
        phone_numbers = data['phone_numbers']
        message_files = data['message_files']
        has_messages = any(message_files)
        
        if has_messages:
            contacts_with_msgs += 1
        
        contact_entry = {
            "name": contact_name,
            "file_path": f"{contact_name}/contact.json",
            "phone_numbers": phone_numbers
        }
        
        all_contacts["contacts"].append(contact_entry)
        
        # Add to contacts with messages if applicable
        if has_messages:
            contact_entry_with_msgs = contact_entry.copy()
            contact_entry_with_msgs["message_files"] = [f for f in message_files if f]
            contacts_with_messages["contacts"].append(contact_entry_with_msgs)
    
    # Update metadata
    contacts_with_messages["metadata"]["total_contacts_with_messages"] = contacts_with_msgs
    
    # Write summary files
    with open(os.path.join(summary_folder, 'all_contacts.json'), 'w', encoding='utf-8') as f:
        json.dump(all_contacts, f, indent=2, ensure_ascii=False)
    
    with open(os.path.join(summary_folder, 'contacts_with_messages.json'), 'w', encoding='utf-8') as f:
        json.dump(contacts_with_messages, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Summary:")
    print(f"   Total contacts: {len(contact_data)}")
    print(f"   Contacts with messages: {contacts_with_msgs}")

def process_vcard_data(vcard_data):
    try:
        # Reset person mapping for clean ID assignment
        reset_person_mapping()
        
        vcards = vobject.readComponents(vcard_data)
        
        # Create main output folder
        os.makedirs(MAIN_OUTPUT_FOLDER, exist_ok=True)
        
        # Create temporary directory for message export
        temp_export_dir = os.path.join(MAIN_OUTPUT_FOLDER, "_temp_messages")
        os.makedirs(temp_export_dir, exist_ok=True)
        
        print("🔄 Step 1: Exporting all individual messages...")
        individual_message_files, group_message_files = export_messages_including_groups(temp_export_dir)
        
        print(f"\n🔄 Step 2: Processing {len(list(vcards))} contacts...")
        
        # Reset vcards iterator
        vcards = vobject.readComponents(vcard_data)
        
        contact_count = 0
        contact_data = {}
        filtered_count = 0  # Track how many contacts were filtered out
        llm_conversations_data = {}  # Track LLM conversation data for master files
        
        # Create all messages folder for flat compatibility
        all_messages_folder = os.path.join(MAIN_OUTPUT_FOLDER, ALL_MESSAGES_FOLDER)
        os.makedirs(all_messages_folder, exist_ok=True)
        
        for vcard in vcards:
            if hasattr(vcard, 'fn'):
                contact_name = vcard.fn.value
                safe_contact_name = re.sub(r'[\\/*?:"<>|]', '_', contact_name)
                
                # Get phone numbers first to check message count
                phone_numbers = []
                if hasattr(vcard, 'tel'):
                    for tel in vcard.tel_list:
                        phone_numbers.append(normalize_phone_number(tel.value))
                
                # Check if contact has enough messages
                if phone_numbers:
                    total_message_count = get_total_message_count_for_contact(phone_numbers, temp_export_dir)
                    print(f"\n📇 {contact_name}: {total_message_count} messages")
                    
                    if total_message_count < MIN_MESSAGE_COUNT:
                        print(f"  ⏭️  Skipping (less than {MIN_MESSAGE_COUNT} messages)")
                        filtered_count += 1
                        continue
                else:
                    print(f"\n📇 {contact_name}: No phone numbers")
                    print(f"  ⏭️  Skipping (no phone numbers)")
                    filtered_count += 1
                    continue
                
                print(f"  ✅ Processing (has {total_message_count} messages)")
                
                # Create contact folder
                contact_folder = os.path.join(MAIN_OUTPUT_FOLDER, safe_contact_name)
                os.makedirs(contact_folder, exist_ok=True)
                
                # Copy individual message files for this contact (optional, for debugging)
                message_files = []
                if CREATE_INDIVIDUAL_MESSAGE_FILES:
                    print(f"  📄 Creating individual message files...")
                    for phone in phone_numbers:
                        message_file = copy_message_file_for_contact(
                            phone, contact_folder, contact_name, vcard, temp_export_dir
                        )
                        if message_file:
                            message_files.append(message_file)
                else:
                    print(f"  ⏭️  Skipping individual message files (CREATE_INDIVIDUAL_MESSAGE_FILES=False)")
                
                # Create consolidated message file (merges all phone numbers)
                if CREATE_CONSOLIDATED_MESSAGE_FILES:
                    consolidated_file = create_consolidated_message_file(
                        contact_name, phone_numbers, temp_export_dir, contact_folder
                    )
                    if consolidated_file:
                        message_files.append(consolidated_file)
                        print(f"  ✅ Using consolidated message file for all processing")
                else:
                    print(f"  ⚠️  Warning: CREATE_CONSOLIDATED_MESSAGE_FILES is disabled")
                
                # Process contact for LLM-ready format to get conversation metadata
                llm_file_path, llm_data = process_contact_for_llm_files(
                    contact_name, phone_numbers, vcard, temp_export_dir, MAIN_OUTPUT_FOLDER,
                    consolidate_contact_messages
                )
                
                # Extract conversation metadata for contact file
                conversation_metadata = llm_data['metadata'] if llm_data else None
                
                # Get last message info
                messages, _ = consolidate_contact_messages(contact_name, phone_numbers, temp_export_dir)
                last_message_info = get_last_message_info(messages)
                
                # Generate contact JSON with conversation insights
                contact_json, _ = vcard_to_json(vcard, contact_folder, message_files, conversation_metadata, last_message_info)
                
                # Save contact file as JSON
                contact_file_path = os.path.join(contact_folder, 'contact.json')
                with open(contact_file_path, 'w', encoding='utf-8') as json_file:
                    json.dump(contact_json, json_file, indent=2, ensure_ascii=False)
                
                if llm_data:
                    llm_conversations_data[safe_contact_name] = llm_data
                    print(f"  ✓ Created LLM conversation: {llm_data['metadata']['total_messages']} messages")
                    if llm_data.get('interaction_analysis'):
                        interaction_stats = llm_data['interaction_analysis']
                        print(f"  ✓ Created recent interactions: {interaction_stats.get('message_count', 0)} messages analyzed")
                        print(f"    - Response pairs: {interaction_stats.get('response_pairs', 0)}")
                        print(f"    - Interaction ratio: {interaction_stats.get('interaction_ratio', 0)}")
                    print(f"  ✓ Added conversation insights to contact.json")
                
                # Store contact data for summary
                contact_data[safe_contact_name] = {
                    'phone_numbers': phone_numbers,
                    'message_files': message_files
                }
                
                print(f"  ✓ Saved: {contact_file_path}")
                contact_count += 1
        
        # Copy all individual message files to flat folder for compatibility
        print(f"\n🔄 Step 3: Creating flat message folder for compatibility...")
        for filename in individual_message_files:
            source = os.path.join(temp_export_dir, filename)
            dest = os.path.join(all_messages_folder, filename)
            if os.path.exists(source):
                shutil.copy2(source, dest)
        
        # Process group chats
        group_chat_data = process_group_chats(group_message_files, temp_export_dir, MAIN_OUTPUT_FOLDER)
        
        # Create summary files
        print(f"\n🔄 Step 4: Creating summary files...")
        create_summary_files(contact_data, MAIN_OUTPUT_FOLDER)
        
        # Create LLM master files
        print(f"\n🔄 Step 5: Creating LLM-ready conversation files...")
        if llm_conversations_data:
            master_index_path, summaries_path = create_llm_master_files(llm_conversations_data, MAIN_OUTPUT_FOLDER, MIN_MESSAGE_COUNT)
            print(f"  ✓ Created master index: {master_index_path}")
            print(f"  ✓ Created conversation summaries: {summaries_path}")
        else:
            print("  ! No conversations met the minimum message criteria")
        
        # Clean up temp directory
        shutil.rmtree(temp_export_dir)
        
        print(f"\n" + "="*60)
        print(f"✅ JSON EXPORT COMPLETE")
        print(f"="*60)
        print(f"📊 Filtering Results:")
        print(f"   Minimum message count: {MIN_MESSAGE_COUNT}")
        print(f"   Contacts exported: {contact_count}")
        print(f"   Contacts filtered out: {filtered_count}")
        print(f"   Total contacts processed: {contact_count + filtered_count}")
        print(f"   LLM conversations created: {len(llm_conversations_data)}")
        print(f"   Group chats processed: {len(group_chat_data) if group_chat_data else 0}")
        print(f"\n📁 Output location: {MAIN_OUTPUT_FOLDER}/")
        print(f"📁 Individual contacts: {MAIN_OUTPUT_FOLDER}/[ContactName]/contact.json")
        print(f"📁 LLM conversations: {MAIN_OUTPUT_FOLDER}/[ContactName]/conversation_llm.json")
        print(f"📁 Recent interactions: {MAIN_OUTPUT_FOLDER}/[ContactName]/{RECENT_INTERACTIONS_FILENAME}")
        print(f"📁 Group chats: {MAIN_OUTPUT_FOLDER}/_group_chats/[GroupName]/group_chat.json")
        print(f"📁 All messages (flat): {MAIN_OUTPUT_FOLDER}/{ALL_MESSAGES_FOLDER}/")
        print(f"📁 Summary files: {MAIN_OUTPUT_FOLDER}/{SUMMARY_FOLDER}/")
        print(f"📁 LLM master index: {MAIN_OUTPUT_FOLDER}/{LLM_FOLDER}/{LLM_INDEX_FILE}")
        
    except Exception as e:
        print(f"❌ Error processing contacts: {str(e)}", file=sys.stderr)
        sys.exit(1)

def check_imessage_exporter():
    """Check if imessage-exporter is installed"""
    try:
        result = subprocess.run(['imessage-exporter', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ imessage-exporter found: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        print("❌ imessage-exporter not found!")
        print("\nTo install imessage-exporter:")
        print("1. Install Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh")
        print("2. Install imessage-exporter: cargo install imessage-exporter")
        print("3. Ensure Terminal has Full Disk Access in System Settings")
        return False
    
    return False

def parse_message_file_for_llm(file_path, phone_number):
    """
    Parse a message file and extract structured message data for LLM processing
    """
    if not os.path.exists(file_path):
        return []
    
    messages = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split content into blocks by double newlines or timestamp patterns
        lines = content.split('\n')
        current_message = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a timestamp
            timestamp_patterns = [
                r'^(\w{3}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',  # Jan 15, 2025  2:30:15 PM (removed $ to allow extra text)
                r'^(\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',    # 1/15/25 2:30:15 PM (removed $ to allow extra text)
            ]
            
            timestamp_match = None
            for pattern in timestamp_patterns:
                timestamp_match = re.match(pattern, line)
                if timestamp_match:
                    break
            
            if timestamp_match:
                # Save previous message if exists
                if current_message.get('content'):
                    messages.append(current_message.copy())
                
                # Start new message
                current_message = {
                    'timestamp_raw': timestamp_match.group(1),
                    'content': '',
                    'sender': 'unknown'
                }
                
            elif line in ['Me', 'me']:
                current_message['sender'] = 'me'
                
            elif line.startswith('+') or line.startswith('1'):
                # Phone number line - indicates contact sent this
                current_message['sender'] = 'contact'
                
            elif line.startswith('(Read by them') or line.startswith('(Delivered'):
                # Read receipt or delivery info - add to metadata
                if 'metadata' not in current_message:
                    current_message['metadata'] = []
                current_message['metadata'].append(line)
                
            else:
                # Content line
                if current_message.get('content'):
                    current_message['content'] += ' ' + line
                else:
                    current_message['content'] = line
        
        # Add the last message
        if current_message.get('content'):
            messages.append(current_message)
        
        # Convert timestamps to standardized format
        for msg in messages:
            try:
                # Parse the timestamp and convert to ISO format
                parsed_time = parse(msg['timestamp_raw'])
                msg['timestamp'] = parsed_time.isoformat()
                # Remove the raw timestamp since we have the standardized one
                del msg['timestamp_raw']
            except Exception:
                # If parsing fails, keep the raw timestamp as the timestamp
                msg['timestamp'] = msg['timestamp_raw']
                del msg['timestamp_raw']
        
        return messages
        
    except Exception as e:
        print(f"  ! Error parsing message file {file_path}: {str(e)}")
        return []

def consolidate_contact_messages(contact_name, phone_numbers, temp_export_dir):
    """
    Consolidate all messages for a contact from multiple phone numbers into a single timeline
    Returns: (all_messages, phone_usage)
    """
    all_messages = []
    phone_usage = {}
    
    for phone_number in phone_numbers:
        # Find message file for this phone number
        phone_clean = phone_number.replace('+', '')
        possible_filenames = [
            f"{phone_number}.txt",
            f"{phone_clean}.txt"
        ]
        
        for filename in possible_filenames:
            file_path = os.path.join(temp_export_dir, filename)
            if os.path.exists(file_path):
                messages = parse_message_file_for_llm(file_path, phone_number)
                all_messages.extend(messages)
                phone_usage[phone_number] = len(messages)
                break
    
    # Sort all messages chronologically
    all_messages.sort(key=lambda x: x.get('timestamp', ''))
    
    return all_messages, phone_usage

def create_consolidated_message_file(contact_name, phone_numbers, temp_export_dir, contact_folder):
    """
    Create a single consolidated message file that merges all phone numbers for a contact
    into one chronological timeline. This ensures we have one unified conversation view.
    """
    print(f"  🔄 Creating consolidated message file for {contact_name}...")
    
    # Parse messages from all phone numbers but preserve more original format info
    all_raw_messages = []
    phone_usage = {}
    
    for phone_number in phone_numbers:
        # Find message file for this phone number
        phone_clean = phone_number.replace('+', '')
        possible_filenames = [
            f"{phone_number}.txt",
            f"{phone_clean}.txt"
        ]
        
        for filename in possible_filenames:
            file_path = os.path.join(temp_export_dir, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse but keep original format
                    lines = content.split('\n')
                    current_message_lines = []
                    message_timestamp = None
                    message_sender = None
                    
                    for line in lines:
                        line_stripped = line.strip()
                        if not line_stripped:
                            if current_message_lines and message_timestamp:
                                # Save current message
                                all_raw_messages.append({
                                    'timestamp_line': message_timestamp,
                                    'sender_line': message_sender,
                                    'content_lines': current_message_lines.copy(),
                                    'phone_source': phone_number
                                })
                                current_message_lines = []
                                message_timestamp = None
                                message_sender = None
                            continue
                        
                        # Check if line is a timestamp
                        timestamp_patterns = [
                            r'^(\w{3}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',
                            r'^(\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',
                        ]
                        
                        is_timestamp = False
                        for pattern in timestamp_patterns:
                            if re.match(pattern, line_stripped):
                                is_timestamp = True
                                break
                        
                        if is_timestamp:
                            # Save previous message if exists
                            if current_message_lines and message_timestamp:
                                all_raw_messages.append({
                                    'timestamp_line': message_timestamp,
                                    'sender_line': message_sender,
                                    'content_lines': current_message_lines.copy(),
                                    'phone_source': phone_number
                                })
                            
                            # Start new message
                            message_timestamp = line_stripped
                            current_message_lines = []
                            message_sender = None
                            
                        elif line_stripped in ['Me', 'me'] or line_stripped.startswith('+') or line_stripped.startswith('1'):
                            # Sender line
                            message_sender = line_stripped
                            
                        else:
                            # Content line
                            current_message_lines.append(line_stripped)
                    
                    # Add the last message
                    if current_message_lines and message_timestamp:
                        all_raw_messages.append({
                            'timestamp_line': message_timestamp,
                            'sender_line': message_sender,
                            'content_lines': current_message_lines.copy(),
                            'phone_source': phone_number
                        })
                    
                    phone_usage[phone_number] = len([m for m in all_raw_messages if m['phone_source'] == phone_number])
                    
                except Exception as e:
                    print(f"  ! Error reading {file_path}: {str(e)}")
                break
    
    if not all_raw_messages:
        print(f"  ! No messages found for {contact_name}")
        return None
    
    # Sort messages chronologically
    def parse_timestamp_for_sorting(timestamp_line):
        try:
            from dateutil.parser import parse
            return parse(timestamp_line)
        except:
            return datetime.min
    
    all_raw_messages.sort(key=lambda x: parse_timestamp_for_sorting(x['timestamp_line']))
    
    # Create consolidated file content in original format
    consolidated_content = []
    
    for message in all_raw_messages:
        # Add timestamp
        consolidated_content.append(message['timestamp_line'])
        
        # Add sender (normalize to show phone number for contact messages)
        sender = message['sender_line']
        if sender and (sender.startswith('+') or sender.startswith('1')):
            # This is a contact message - use the source phone number for clarity
            consolidated_content.append(message['phone_source'])
        elif sender:
            consolidated_content.append(sender)
        else:
            consolidated_content.append('Unknown')
        
        # Add content lines
        for content_line in message['content_lines']:
            consolidated_content.append(content_line)
        
        # Add empty line between messages
        consolidated_content.append('')
    
    # Write consolidated file
    consolidated_filename = 'messages_consolidated.txt'
    consolidated_path = os.path.join(contact_folder, consolidated_filename)
    
    try:
        with open(consolidated_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(consolidated_content))
        
        print(f"  ✓ Created consolidated message file: {consolidated_filename}")
        print(f"    - Total messages: {len(all_raw_messages)}")
        print(f"    - Phone numbers: {len(phone_numbers)}")
        print(f"    - Phone usage: {phone_usage}")
        
        return consolidated_filename
        
    except Exception as e:
        print(f"  ! Error creating consolidated message file: {str(e)}")
        return None

def parse_group_chat_file(file_path):
    """
    Parse a group chat message file to extract participants and messages
    """
    messages = []
    participants = set()
    group_name = None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_message = {}
        expecting_sender = False  # Flag to track if next line should be sender
        
        for line in lines:
            line = line.strip()
            if not line:
                # Save current message if exists
                if current_message.get('content'):
                    messages.append(current_message.copy())
                    current_message = {}
                expecting_sender = False
                continue
            
            # Check for timestamp pattern
            timestamp_patterns = [
                r'^(\w{3}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',
                r'^(\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',
            ]
            
            timestamp_match = None
            for pattern in timestamp_patterns:
                timestamp_match = re.match(pattern, line)
                if timestamp_match:
                    break
            
            if timestamp_match:
                # Save previous message if exists
                if current_message.get('content'):
                    messages.append(current_message.copy())
                
                # Start new message
                current_message = {
                    'timestamp_raw': timestamp_match.group(1),
                    'content': '',
                    'sender': 'unknown'
                }
                expecting_sender = True  # Next non-empty line should be the sender
                
            elif expecting_sender:
                # This line immediately follows a timestamp, so it's the sender
                if line in ['Me', 'me']:
                    current_message['sender'] = 'me'
                elif re.match(r'^\+\d{10,15}$', line) or re.match(r'^\d{10,15}$', line):
                    # Phone number sender
                    normalized_phone = normalize_phone_number(line)
                    current_message['sender'] = normalized_phone
                    participants.add(normalized_phone)
                elif '@' in line and '.' in line and len(line.split()) == 1:
                    # Email address sender
                    current_message['sender'] = line
                    participants.add(line)
                else:
                    # Unknown sender format, treat as content
                    current_message['sender'] = 'unknown'
                    current_message['content'] = line
                
                expecting_sender = False
                
            elif line.startswith('(Read by') or line.startswith('(Delivered') or line.startswith('Tapbacks:'):
                # Read receipt, delivery info, or tapback info - skip
                continue
                
            else:
                # Content line
                if current_message.get('content'):
                    current_message['content'] += ' ' + line
                else:
                    current_message['content'] = line
        
        # Add the last message
        if current_message.get('content'):
            messages.append(current_message)
        
        # Convert timestamps to standardized format
        for msg in messages:
            try:
                if 'timestamp_raw' in msg:
                    parsed_time = parse(msg['timestamp_raw'])
                    msg['timestamp'] = parsed_time.isoformat()
                    del msg['timestamp_raw']
            except Exception:
                if 'timestamp_raw' in msg:
                    msg['timestamp'] = msg['timestamp_raw']
                    del msg['timestamp_raw']
        
        return {
            'messages': messages,
            'participants': list(participants),
            'total_messages': len(messages),
            'group_name': group_name  # We'll try to extract this later
        }
        
    except Exception as e:
        print(f"  ! Error parsing group chat file {file_path}: {str(e)}")
        return None

def create_group_chat_json(group_filename, group_data, group_folder):
    """
    Create a JSON file for a group chat similar to contact.json
    """
    if not group_data:
        return None
    
    # Extract a cleaner group name from filename
    group_name = group_filename.replace('.txt', '')
    
    # Generate conversation metadata
    messages = group_data['messages']
    participants = group_data['participants']
    
    if not messages:
        return None
    
    # Basic stats
    total_messages = len(messages)
    sent_messages = sum(1 for m in messages if m.get('sender') == 'me')
    received_messages = total_messages - sent_messages
    
    # Participant activity
    participant_activity = {}
    for participant in participants:
        participant_activity[participant] = sum(1 for m in messages if m.get('sender') == participant)
    
    # Date range
    timestamps = [m.get('timestamp') for m in messages if m.get('timestamp')]
    if timestamps:
        try:
            first_date = parse(min(timestamps))
            last_date = parse(max(timestamps))
            date_range = f"{first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')}"
            conversation_span_days = (last_date - first_date).days
        except Exception:
            date_range = "Unknown"
            conversation_span_days = 0
    else:
        date_range = "Unknown"
        conversation_span_days = 0
    
    # Message frequency
    message_frequency = round(total_messages / max(conversation_span_days, 1), 2) if conversation_span_days > 0 else total_messages
    
    # Create group chat data structure
    group_json = {
        "group_name": group_name,
        "file_name": group_filename,
        "type": "group_chat",
        "participants": {
            "phone_numbers": participants,
            "count": len(participants),
            "activity": participant_activity
        },
        "conversation_insights": {
            "total_messages": total_messages,
            "sent_messages": sent_messages,
            "received_messages": received_messages,
            "date_range": date_range,
            "conversation_span_days": conversation_span_days,
            "message_frequency_per_day": message_frequency,
            "most_active_participant": max(participant_activity.items(), key=lambda x: x[1])[0] if participant_activity else "unknown"
        },
        "message_history": [{
            "filename": group_filename,
            "path": group_filename,
            "type": "group_chat_messages"
        }],
        "metadata": {
            "generated_at": "2025-01-15T06:06:00Z",
            "format": "group_chat_export_v1"
        }
    }
    
    # Save group chat JSON
    json_filename = 'group_chat.json'
    json_path = os.path.join(group_folder, json_filename)
    
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(group_json, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Created group chat JSON: {json_path}")
        return group_json
        
    except Exception as e:
        print(f"  ! Error creating group chat JSON: {str(e)}")
        return None

def process_group_chats(group_files, temp_export_dir, output_folder):
    """
    Process all group chat files and create structured data
    """
    print(f"\n🔄 Step 3: Processing {len(group_files)} group chats...")
    
    # Create group chats folder
    group_chats_folder = os.path.join(output_folder, "_group_chats")
    os.makedirs(group_chats_folder, exist_ok=True)
    
    group_chat_data = {}
    processed_count = 0
    
    for group_file in group_files:
        group_file_path = os.path.join(temp_export_dir, group_file)
        
        if not os.path.exists(group_file_path):
            continue
        
        print(f"\n💬 Processing group: {group_file}")
        
        # Parse the group chat file
        group_data = parse_group_chat_file(group_file_path)
        
        if not group_data or group_data['total_messages'] < MIN_MESSAGE_COUNT:
            if group_data:
                print(f"  ⏭️  Skipping (only {group_data['total_messages']} messages, need {MIN_MESSAGE_COUNT})")
            else:
                print(f"  ⏭️  Skipping (failed to parse)")
            continue
        
        print(f"  ✅ Found {group_data['total_messages']} messages from {len(group_data['participants'])} participants")
        
        # Create a safe folder name for this group
        safe_group_name = re.sub(r'[\\/*?:"<>|]', '_', group_file.replace('.txt', ''))
        group_folder = os.path.join(group_chats_folder, safe_group_name)
        os.makedirs(group_folder, exist_ok=True)
        
        # Copy the original message file
        dest_path = os.path.join(group_folder, group_file)
        shutil.copy2(group_file_path, dest_path)
        
        # Create structured JSON
        group_json = create_group_chat_json(group_file, group_data, group_folder)
        
        if group_json:
            group_chat_data[safe_group_name] = {
                'file_path': os.path.join("_group_chats", safe_group_name, "group_chat.json"),
                'participants': group_data['participants'],
                'total_messages': group_data['total_messages'],
                'group_name': group_file.replace('.txt', '')
            }
            processed_count += 1
    
    print(f"\n📊 Group Chat Summary:")
    print(f"   Total group chats found: {len(group_files)}")
    print(f"   Successfully processed: {processed_count}")
    
    # Create group chat summary file
    if group_chat_data:
        summary_data = {
            "metadata": {
                "total_group_chats": len(group_chat_data),
                "generated_at": "2025-01-15T06:06:00Z",
                "format": "group_chat_summary_v1"
            },
            "group_chats": []
        }
        
        for group_name, data in group_chat_data.items():
            summary_data["group_chats"].append({
                "group_name": data['group_name'],
                "file_path": data['file_path'],
                "participants": data['participants'],
                "total_messages": data['total_messages']
            })
        
        summary_path = os.path.join(group_chats_folder, 'group_chats_summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Created group chat summary: {summary_path}")
    
    return group_chat_data

if __name__ == "__main__":
    print("🚀 Starting Integrated Contacts & Messages Exporter v2 (JSON)")
    print("="*60)
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Export contacts and iMessage conversations to structured JSON format")
    parser.add_argument("vcf_file", nargs="?", help="Path to the VCF file to process. If not provided, will scan current directory")
    parser.add_argument("--min-messages", type=int, help=f"Minimum number of messages for a contact to be exported (default: {MIN_MESSAGE_COUNT})")
    parser.add_argument("--disable-privacy", action="store_true", help="Disable privacy features for LLM data (don't anonymize sensitive information)")
    args = parser.parse_args()
    
    # Update minimum message count if provided
    if args.min_messages is not None:
        MIN_MESSAGE_COUNT = args.min_messages
        print(f"✓ Using minimum message count: {MIN_MESSAGE_COUNT}")
    
    # Update privacy setting if specified
    if args.disable_privacy:
        set_privacy_enabled(False)
        print("⚠️ Privacy features disabled - LLM data will contain sensitive information")
    else:
        print(f"✓ Privacy features enabled - LLM data will be anonymized")
    
    # Check prerequisites
    if not check_imessage_exporter():
        sys.exit(1)
    
    # Get VCF file - either from command line args or by scanning directory
    vcf_path = None
    
    # Check if a file was provided as command line argument
    if args.vcf_file:
        provided_path = args.vcf_file
        if os.path.exists(provided_path) and provided_path.lower().endswith('.vcf'):
            vcf_path = provided_path
        else:
            print(f"❌ Error: Cannot find VCF file at '{provided_path}'")
            print("Please provide a valid .vcf file path.")
        sys.exit(1)
    
    # If no path was provided via command line, scan for vcf files
    if not vcf_path:
        vcf_files = [f for f in os.listdir('.') if f.lower().endswith('.vcf')]
        
        if not vcf_files:
            print("❌ Error: No VCF files found in the current directory.")
            print("Please provide a .vcf file in the same directory as this script or specify path as argument.")
            sys.exit(1)
        elif len(vcf_files) == 1:
            vcf_path = vcf_files[0]
        else:
            print("📋 Multiple VCF files found. Please select one:")
            for i, file in enumerate(vcf_files):
                print(f"  {i+1}. {file} ({os.path.getsize(file) / (1024*1024):.2f} MB)")
            
            while True:
                try:
                    choice = int(input("\nEnter file number to use: "))
                    if 1 <= choice <= len(vcf_files):
                        vcf_path = vcf_files[choice-1]
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(vcf_files)}")
                except ValueError:
                    print("Please enter a valid number")
    
    print(f"✓ Using VCF file: {vcf_path}")
    print("\n🎯 This script will:")
    print("• Export all contacts to individual folders as JSON")
    print("• Export individual message conversations AND group chats")
    print(f"• Only export contacts with {MIN_MESSAGE_COUNT}+ messages")
    print("• Standardize phone number formatting")
    print("• Create structured, machine-readable JSON files")
    print("• Create LLM-ready conversation format with message grouping & cleaning")
    print("• Create recent interactions files with preserved formatting for pattern analysis")
    if ANONYMIZE_LLM_DATA:
        print("• Anonymize sensitive data in LLM files (names, phone numbers, addresses)")
        print("• Create mapping files for re-identification if needed")
    print("• Link message files to contact records")
    print("• Generate summary and index files in JSON")
    
    input("\nPress Enter to continue...")
    
    vcard_data = read_vcf_file(vcf_path)
    process_vcard_data(vcard_data) 
