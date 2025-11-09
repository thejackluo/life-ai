"""
Message Sampler

Intelligently samples representative messages from conversation history
to provide authentic examples for LLM character simulation.
"""

import random
from typing import List, Dict
from datetime import datetime
from dateutil.parser import parse


def sample_messages(
    messages: List[Dict],
    target_count: int = 40,
    min_length: int = 10
) -> List[Dict]:
    """
    Sample representative messages from conversation history.
    
    Strategy:
    - Distribute samples across the timeline (early, middle, recent)
    - Prioritize substantive messages (skip very short ones)
    - Include variety of emotional tones
    - Ensure mix of both sender types
    
    Args:
        messages: Full message history
        target_count: How many samples to take
        min_length: Minimum message length to consider
        
    Returns:
        List of sampled messages with good coverage
    """
    if not messages:
        return []
    
    # Filter out very short or empty messages
    substantive = [
        msg for msg in messages
        if msg.get('content', '').strip() and len(msg.get('content', '')) >= min_length
    ]
    
    if not substantive:
        # Fallback to all messages if filtering too aggressive
        substantive = [msg for msg in messages if msg.get('content', '').strip()]
    
    if len(substantive) <= target_count:
        # Not enough messages, return all
        return substantive
    
    # Sample strategy: temporal distribution
    samples = []
    
    # 1. Recent messages (last 20% of timeline) - 40% of samples
    recent_count = int(target_count * 0.4)
    recent_start = int(len(substantive) * 0.8)
    recent_pool = substantive[recent_start:]
    samples.extend(_random_sample(recent_pool, min(recent_count, len(recent_pool))))
    
    # 2. Middle period (40-80% of timeline) - 30% of samples
    middle_count = int(target_count * 0.3)
    middle_start = int(len(substantive) * 0.4)
    middle_end = int(len(substantive) * 0.8)
    middle_pool = substantive[middle_start:middle_end]
    samples.extend(_random_sample(middle_pool, min(middle_count, len(middle_pool))))
    
    # 3. Early messages (first 40% of timeline) - 30% of samples
    early_count = target_count - len(samples)
    early_pool = substantive[:int(len(substantive) * 0.4)]
    samples.extend(_random_sample(early_pool, min(early_count, len(early_pool))))
    
    # Sort by timestamp to maintain chronological sense
    samples.sort(key=lambda m: m.get('timestamp', ''))
    
    return samples


def _random_sample(pool: List[Dict], count: int) -> List[Dict]:
    """Randomly sample from pool"""
    if len(pool) <= count:
        return pool
    return random.sample(pool, count)


def sample_character_messages(
    messages: List[Dict],
    target_count: int = 40,
    use_full_history: bool = True
) -> Dict[str, any]:
    """
    Sample messages or use full history.
    
    Args:
        messages: Full message history
        target_count: Number of message samples (if not using full history)
        use_full_history: If True, use ALL messages instead of sampling
        
    Returns:
        Dict with samples and basic stats
    """
    if use_full_history:
        # Use all messages, just filter very short ones
        samples = [
            msg for msg in messages
            if msg.get('content', '').strip() and len(msg.get('content', '')) >= 5
        ]
    else:
        samples = sample_messages(messages, target_count)
    
    # Calculate basic stats from samples
    contact_messages = [m for m in samples if m.get('sender') == 'contact']
    player_messages = [m for m in samples if m.get('sender') == 'me']
    
    avg_contact_length = (
        sum(len(m.get('content', '')) for m in contact_messages) / len(contact_messages)
        if contact_messages else 0
    )
    
    avg_player_length = (
        sum(len(m.get('content', '')) for m in player_messages) / len(player_messages)
        if player_messages else 0
    )
    
    return {
        'samples': samples,
        'sample_count': len(samples),
        'contact_message_count': len(contact_messages),
        'player_message_count': len(player_messages),
        'avg_contact_length': round(avg_contact_length, 1),
        'avg_player_length': round(avg_player_length, 1),
        'total_messages_in_history': len(messages)
    }


def format_examples_for_prompt(samples: List[Dict], max_examples: int = 30) -> str:
    """
    Format message samples for inclusion in LLM prompt.
    
    Args:
        samples: Sampled messages
        max_examples: Maximum examples to include
        
    Returns:
        Formatted string ready for prompt
    """
    formatted = []
    
    for i, msg in enumerate(samples[:max_examples], 1):
        sender = "YOU" if msg.get('sender') == 'contact' else "ARMAN"
        content = msg.get('content', '').strip()
        
        if content:
            # Clean up very long messages
            if len(content) > 200:
                content = content[:197] + "..."
            
            formatted.append(f"--- EXAMPLE {i} ---\n{sender}: \"{content}\"")
    
    return "\n\n".join(formatted)

