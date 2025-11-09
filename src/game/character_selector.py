"""
Character Selector Module

Provides UI for selecting which contacts from the exported data
should become characters in the game.
"""

import json
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class ContactData:
    """Represents a contact available for selection"""
    
    def __init__(self, name: str, data: Dict):
        self.name = name
        self.message_count = data.get('total_messages', 0)
        self.relationship_hint = self._guess_relationship(data)
        # Don't use file_path from data (it has anonymized name), construct from real name
        self.file_path = f"{name}/conversation_llm.json"
        self.recent_file_path = f"{name}/conversation_recent_interactions.json"
        self.date_range = data.get('date_range', 'Unknown')
        
    def _guess_relationship(self, data: Dict) -> str:
        """Guess relationship type based on message patterns"""
        msg_count = data.get('total_messages', 0)
        
        if msg_count > 500:
            return "Very Close"
        elif msg_count > 200:
            return "Close Friend"
        elif msg_count > 50:
            return "Friend"
        else:
            return "Acquaintance"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.message_count} msgs, {self.relationship_hint})"


class CharacterSelector:
    """
    Handles selection of contacts to import as game characters.
    """
    
    def __init__(self, data_folder: str = "data"):
        """
        Initialize character selector.
        
        Args:
            data_folder: Path to folder containing exported contact data
        """
        self.data_folder = Path(data_folder)
        self.master_index_path = self.data_folder / "_llm_ready" / "master_index.json"
        self.privacy_mapping_path = self.data_folder / "_llm_ready" / "privacy_mapping.json"
        self.contacts: List[ContactData] = []
        self.name_mapping: Dict[str, str] = {}  # Maps [[PERSON_X]] -> Real Name
        self._load_privacy_mapping()
        self._load_contacts()
    
    def _load_privacy_mapping(self) -> None:
        """Load privacy mapping to de-anonymize names"""
        if not self.privacy_mapping_path.exists():
            # No privacy mapping, names are already real
            return
        
        try:
            with open(self.privacy_mapping_path, 'r', encoding='utf-8') as f:
                mapping_data = json.load(f)
            
            # Create reverse mapping: person_id -> real_name
            global_mapping = mapping_data.get('global_person_mapping', {})
            for real_name, person_id in global_mapping.items():
                anonymized = f"[[PERSON_{person_id}]]"
                self.name_mapping[anonymized] = real_name
        
        except Exception as e:
            print(f"  ⚠️  Could not load privacy mapping: {e}")
    
    def _de_anonymize_name(self, name: str) -> str:
        """Convert anonymized name to real name"""
        return self.name_mapping.get(name, name)
    
    def _load_contacts(self) -> None:
        """Load contacts from master index"""
        if not self.master_index_path.exists():
            raise FileNotFoundError(
                f"Master index not found at {self.master_index_path}. "
                "Please run contacts_exporter.py first."
            )
        
        with open(self.master_index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        # Extract contact list
        conversations = index_data.get('conversations', [])
        
        for conv in conversations:
            name = conv.get('contact_name', 'Unknown')
            # De-anonymize the name if it was anonymized
            real_name = self._de_anonymize_name(name)
            # Update the conv data with real name for ContactData
            conv_copy = conv.copy()
            conv_copy['contact_name'] = real_name
            self.contacts.append(ContactData(real_name, conv_copy))
        
        # Sort by message count (most active first)
        self.contacts.sort(key=lambda c: c.message_count, reverse=True)
    
    def get_top_contacts(self, n: int = 20) -> List[ContactData]:
        """
        Get the top N most active contacts.
        
        Args:
            n: Number of contacts to return
            
        Returns:
            List of ContactData objects
        """
        return self.contacts[:n]
    
    def search_contacts(self, query: str) -> List[ContactData]:
        """
        Search for contacts by name.
        
        Args:
            query: Search string (case-insensitive)
            
        Returns:
            List of matching ContactData objects
        """
        query_lower = query.lower()
        return [c for c in self.contacts if query_lower in c.name.lower()]
    
    def display_contacts_table(self, contacts: List[ContactData], page: int = 1, page_size: int = 10) -> Tuple[List[ContactData], bool]:
        """
        Display contacts in a numbered table format.
        
        Args:
            contacts: List of contacts to display
            page: Page number (1-indexed)
            page_size: Number of contacts per page
            
        Returns:
            Tuple of (contacts_on_page, has_more_pages)
        """
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_contacts = contacts[start_idx:end_idx]
        has_more = end_idx < len(contacts)
        
        print("\n" + "="*70)
        print(f"  {'#':<4} {'Name':<30} {'Messages':<12} {'Type':<20}")
        print("="*70)
        
        for i, contact in enumerate(page_contacts, start=start_idx + 1):
            print(f"  {i:<4} {contact.name:<30} {contact.message_count:<12} {contact.relationship_hint:<20}")
        
        print("="*70)
        
        if has_more:
            print(f"\n  (Page {page}/{(len(contacts) + page_size - 1) // page_size}) - More contacts available")
        
        return page_contacts, has_more
    
    def interactive_selection(
        self, 
        min_characters: int = 1, 
        max_characters: int = 20,
        default_count: int = 8
    ) -> List[ContactData]:
        """
        Interactive terminal UI for selecting characters.
        
        Args:
            min_characters: Minimum number of characters required
            max_characters: Maximum number of characters allowed
            default_count: Default number of characters to suggest
            
        Returns:
            List of selected ContactData objects
        """
        print("\n" + "🎭 " * 20)
        print("\n  LIFE AI - CHARACTER SELECTION")
        print("\n  Choose which contacts to bring into your game.")
        print(f"  Select at least {min_characters}, up to {max_characters} characters.\n")
        print("🎭 " * 20)
        
        selected_contacts: List[ContactData] = []
        page = 1
        
        while True:
            # Show selection status
            if selected_contacts:
                print(f"\n  ✓ Selected ({len(selected_contacts)}/{max_characters}):")
                for i, contact in enumerate(selected_contacts, 1):
                    print(f"    {i}. {contact.name}")
            
            # Display contacts
            print(f"\n  📋 Available Contacts:")
            page_contacts, has_more = self.display_contacts_table(self.contacts, page)
            
            # Show commands
            print("\n  Commands:")
            print("    [number]      - Select/deselect contact by number")
            print("    [s]earch      - Search for specific contact")
            print("    [t]op N       - Select top N most active contacts")
            print("    [n]ext page   - View next page")
            print("    [p]rev page   - View previous page")
            print("    [d]one        - Finish selection")
            print("    [q]uit        - Cancel and exit")
            
            # Get input
            choice = input("\n  → ").strip().lower()
            
            if not choice:
                continue
            
            # Handle commands
            if choice in ['d', 'done']:
                if len(selected_contacts) >= min_characters:
                    print(f"\n  ✓ Selected {len(selected_contacts)} characters!")
                    return selected_contacts
                else:
                    print(f"\n  ⚠️  Please select at least {min_characters} characters.")
                    continue
            
            elif choice in ['q', 'quit']:
                print("\n  Cancelled character selection.")
                return []
            
            elif choice in ['n', 'next']:
                if has_more:
                    page += 1
                else:
                    print("\n  ⚠️  Already on last page.")
                continue
            
            elif choice in ['p', 'prev', 'previous']:
                if page > 1:
                    page -= 1
                else:
                    print("\n  ⚠️  Already on first page.")
                continue
            
            elif choice in ['s', 'search']:
                query = input("\n  Search for: ").strip()
                if query:
                    results = self.search_contacts(query)
                    if results:
                        print(f"\n  Found {len(results)} matches:")
                        self.display_contacts_table(results, 1, 20)
                    else:
                        print(f"\n  No contacts found matching '{query}'")
                input("\n  Press Enter to continue...")
                continue
            
            elif choice.startswith('t'):
                # Top N selection
                try:
                    parts = choice.split()
                    n = int(parts[1]) if len(parts) > 1 else default_count
                    n = min(n, max_characters)
                    
                    top_contacts = self.get_top_contacts(n)
                    selected_contacts = top_contacts
                    print(f"\n  ✓ Selected top {len(selected_contacts)} most active contacts!")
                    
                except (ValueError, IndexError):
                    print(f"\n  ⚠️  Invalid format. Use: t [number] (e.g., 't 8')")
                continue
            
            else:
                # Try to parse as number selection
                try:
                    num = int(choice)
                    if 1 <= num <= len(self.contacts):
                        contact = self.contacts[num - 1]
                        
                        # Toggle selection
                        if contact in selected_contacts:
                            selected_contacts.remove(contact)
                            print(f"\n  ✗ Removed: {contact.name}")
                        else:
                            if len(selected_contacts) < max_characters:
                                selected_contacts.append(contact)
                                print(f"\n  ✓ Added: {contact.name}")
                            else:
                                print(f"\n  ⚠️  Maximum {max_characters} characters reached.")
                    else:
                        print(f"\n  ⚠️  Number out of range (1-{len(self.contacts)})")
                        
                except ValueError:
                    print(f"\n  ⚠️  Invalid command: '{choice}'")
                
                continue
    
    def quick_select_top(self, n: int = 8) -> List[ContactData]:
        """
        Quickly select top N most active contacts without UI.
        
        Args:
            n: Number of contacts to select
            
        Returns:
            List of selected ContactData objects
        """
        return self.get_top_contacts(n)


def select_characters(data_folder: str = "data", interactive: bool = True) -> List[ContactData]:
    """
    Main entry point for character selection.
    
    Args:
        data_folder: Path to exported contact data
        interactive: If True, use interactive UI; if False, auto-select top 8
        
    Returns:
        List of selected ContactData objects
    """
    selector = CharacterSelector(data_folder)
    
    if interactive:
        return selector.interactive_selection()
    else:
        return selector.quick_select_top()


if __name__ == "__main__":
    # Test the selector
    selected = select_characters()
    print(f"\nFinal selection: {len(selected)} characters")
    for contact in selected:
        print(f"  - {contact}")

