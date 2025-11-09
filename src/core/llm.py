"""
LLM Integration Module

Handles all OpenAI API interactions with prompt management,
error handling, and retry logic. Provides clean interfaces for
character generation and conversation.
"""

import os
import json
import time
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMClient:
    """
    Wrapper around OpenAI API with prompt management and error handling.
    """
    
    def __init__(self, model: str = "gpt-4o", temperature: float = 0.7):
        """
        Initialize LLM client.
        
        Args:
            model: OpenAI model to use (default: gpt-4o)
            temperature: Sampling temperature 0.0-1.0 (default: 0.7)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Please create a .env file with your OpenAI API key."
            )
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def _call_api(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Make API call with retry logic.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Max tokens to generate
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If all retries fail
        """
        temp = temperature if temperature is not None else self.temperature
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"  ! API error (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(f"API call failed after {self.max_retries} attempts: {str(e)}")
    
    # ========================================================================
    # CHARACTER GENERATION
    # ========================================================================
    
    def generate_character_personality(
        self, 
        contact_name: str,
        message_history: List[Dict[str, str]],
        conversation_metadata: Dict
    ) -> Dict[str, any]:
        """
        Generate AI personality for a character based on real message history.
        
        Args:
            contact_name: Name of the contact
            message_history: List of messages from conversation_llm.json
            conversation_metadata: Metadata about the conversation
            
        Returns:
            Dict with personality_summary, communication_style, interests, typical_topics, favorite_phrases
        """
        # Build context from messages (use recent ~50 messages for efficiency)
        recent_messages = message_history[-50:] if len(message_history) > 50 else message_history
        
        message_examples = "\n".join([
            f"[{msg.get('sender', 'unknown')}]: {msg.get('content', '')}"
            for msg in recent_messages
            if msg.get('content', '').strip()
        ][:30])  # Cap at 30 examples
        
        # Build prompt
        prompt = f"""You are analyzing real text message history between the player and their contact "{contact_name}".

CONVERSATION METADATA:
- Total messages: {conversation_metadata.get('total_messages', 0)}
- Date range: {conversation_metadata.get('date_range', 'Unknown')}
- Message frequency: {conversation_metadata.get('message_frequency_per_day', 0)} per day

RECENT MESSAGE EXAMPLES:
{message_examples}

Based on this REAL message history, create a detailed character profile that captures {contact_name}'s personality, communication style, and interests. This will be used to simulate realistic conversations with them in a game.

Respond in JSON format:
{{
    "personality_summary": "A 2-3 sentence description of their personality based on how they communicate",
    "communication_style": "How they text/speak (casual, formal, uses emojis, short/long messages, etc.)",
    "interests": ["interest1", "interest2", "interest3"],
    "typical_topics": ["topic1", "topic2", "topic3"],
    "favorite_phrases": ["phrase1", "phrase2", "phrase3"]
}}

Make it authentic to their actual communication patterns. Capture their unique voice."""

        messages = [
            {"role": "system", "content": "You are an expert at analyzing communication patterns and creating authentic character profiles."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_api(messages, temperature=0.3)  # Lower temp for consistent analysis
        
        # Parse JSON response
        try:
            # Try to extract JSON from response (handles cases where model adds extra text)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"  ! Failed to parse personality JSON for {contact_name}: {e}")
            print(f"  Response was: {response[:200]}...")
            # Return fallback personality
            return {
                "personality_summary": f"{contact_name} is a friend who communicates regularly.",
                "communication_style": "casual and friendly",
                "interests": ["general topics"],
                "typical_topics": ["daily life", "plans", "updates"],
                "favorite_phrases": []
            }
    
    # ========================================================================
    # CONVERSATION GENERATION
    # ========================================================================
    
    def generate_character_response(
        self,
        character_name: str,
        character_personality: str,
        character_style: str,
        conversation_history: List[Dict[str, str]],
        player_message: str,
        relationship_level: str,
        context: Optional[str] = None
    ) -> str:
        """
        Generate a character's response to player input.
        
        Args:
            character_name: Name of the character
            character_personality: Their personality summary
            character_style: Their communication style
            conversation_history: Recent conversation messages
            player_message: What the player just said
            relationship_level: Current relationship level
            context: Optional context about current situation
            
        Returns:
            Character's response text
        """
        # Build conversation context (last 10 messages)
        recent_conv = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        conv_text = "\n".join([
            f"{msg['speaker']}: {msg['content']}"
            for msg in recent_conv
        ])
        
        context_text = f"\n\nCurrent situation: {context}" if context else ""
        
        prompt = f"""You are {character_name} texting with Arman (the player).

{context_text}

WHO YOU ARE:
{character_personality}

YOUR RELATIONSHIP:
{character_style}
Current strength: {relationship_level}

RECENT CONVERSATION:
{conv_text}

Arman just said: "{player_message}"

CRITICAL INSTRUCTIONS:
- Study the example messages above carefully
- Copy YOUR exact communication style from those examples
- Use YOUR phrases, YOUR emoji patterns, YOUR message length
- Use YOUR humor and tone
- Don't invent events - respond naturally to what Arman says
- Match how YOU actually text

Respond as {character_name} would (no labels):"""

        messages = [
            {"role": "system", "content": f"You are {character_name}. Respond naturally and authentically based on your personality."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_api(messages, temperature=0.8)  # Higher temp for creative conversation
        return response.strip()
    
    # ========================================================================
    # QUEST GENERATION
    # ========================================================================
    
    def generate_quest(
        self,
        character_name: str,
        relationship_level: str,
        relationship_strength: int,
        recent_topics: List[str],
        quest_type: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Generate a quest based on character and relationship state.
        
        Args:
            character_name: Name of the character
            relationship_level: Current relationship level
            relationship_strength: 0-100 strength score
            recent_topics: Topics discussed recently
            quest_type: Optional specific quest type to generate
            
        Returns:
            Dict with quest details (title, description, objectives, rewards)
        """
        topics_text = ", ".join(recent_topics) if recent_topics else "general conversation"
        type_hint = f"Focus on {quest_type} type quests." if quest_type else ""
        
        prompt = f"""Generate a quest/objective for the player involving their contact {character_name}.

CONTEXT:
- Relationship level: {relationship_level}
- Relationship strength: {relationship_strength}/100
- Recent conversation topics: {topics_text}
{type_hint}

Create a meaningful quest that:
1. Feels natural given their relationship and recent conversations
2. Involves meaningful interaction (not just "send a text")
3. Has clear objectives
4. Offers relationship progression as reward

Respond in JSON format:
{{
    "title": "Short quest title",
    "description": "1-2 sentence description of what this quest involves",
    "objectives": ["objective 1", "objective 2"],
    "time_cost": 60,
    "energy_cost": 10,
    "relationship_reward": 15
}}

Make it feel personal and grounded in reality."""

        messages = [
            {"role": "system", "content": "You are a quest designer creating meaningful social objectives based on real relationships."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_api(messages, temperature=0.6)
        
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"  ! Failed to parse quest JSON: {e}")
            # Return fallback quest
            return {
                "title": f"Catch up with {character_name}",
                "description": f"Have a meaningful conversation with {character_name}",
                "objectives": ["Start a conversation", "Talk about something meaningful"],
                "time_cost": 60,
                "energy_cost": 10,
                "relationship_reward": 10
            }
    
    # ========================================================================
    # UTILITY
    # ========================================================================
    
    def extract_sentiment_context(self, message: str) -> str:
        """
        Get brief context about message sentiment (used alongside vaderSentiment).
        
        Args:
            message: The message to analyze
            
        Returns:
            Brief sentiment context string
        """
        prompt = f"""Briefly characterize the emotional tone of this message in 3-5 words:

"{message}"

Examples: "enthusiastic and supportive", "frustrated but caring", "casual and friendly"

Keep it very brief."""

        messages = [
            {"role": "system", "content": "You are analyzing emotional tone in messages."},
            {"role": "user", "content": prompt}
        ]
        
        return self._call_api(messages, temperature=0.3, max_tokens=20).strip()


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the singleton LLM client"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


# Convenience functions
def generate_character(contact_name: str, message_history: List[Dict], metadata: Dict) -> Dict:
    """Convenience function for character generation"""
    return get_llm_client().generate_character_personality(contact_name, message_history, metadata)


def get_character_response(
    character_name: str,
    personality: str,
    style: str,
    history: List[Dict],
    player_msg: str,
    rel_level: str,
    context: Optional[str] = None
) -> str:
    """Convenience function for character responses"""
    return get_llm_client().generate_character_response(
        character_name, personality, style, history, player_msg, rel_level, context
    )

