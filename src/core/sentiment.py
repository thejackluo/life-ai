"""
Sentiment Analysis Module

Uses vaderSentiment to analyze player messages and determine
their emotional impact on character relationships.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import Tuple, Dict


class SentimentAnalyzer:
    """
    Analyzes sentiment of player messages to determine relationship impact.
    
    Uses VADER (Valence Aware Dictionary and sEntiment Reasoner) which is
    specifically tuned for social media text and informal communication.
    """
    
    def __init__(self):
        """Initialize the sentiment analyzer"""
        self.analyzer = SentimentIntensityAnalyzer()
        
        # More granular and dynamic impact calculation
        # Base multiplier - will be scaled by actual sentiment score
        self.sentiment_scale = 20.0  # Max impact range: -20 to +20
        
        # Minimum threshold for impact
        self.neutral_threshold = 0.05
    
    def analyze(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text.
        
        Args:
            text: The message to analyze
            
        Returns:
            Dict with sentiment scores:
            - compound: Overall sentiment -1.0 to 1.0
            - pos: Positive proportion 0.0 to 1.0
            - neu: Neutral proportion 0.0 to 1.0
            - neg: Negative proportion 0.0 to 1.0
        """
        if not text or not text.strip():
            return {'compound': 0.0, 'pos': 0.0, 'neu': 1.0, 'neg': 0.0}
        
        return self.analyzer.polarity_scores(text)
    
    def get_relationship_impact(self, text: str) -> Tuple[float, str, str]:
        """
        Determine how a message impacts a relationship.
        Uses dynamic scaling based on actual sentiment strength.
        
        Args:
            text: The message to analyze
            
        Returns:
            Tuple of (impact_value, category, description)
            - impact_value: Float representing relationship points change (-20 to +20)
            - category: Sentiment category (very_positive, positive, neutral, negative, very_negative)
            - description: Human-readable description of the sentiment
        """
        scores = self.analyze(text)
        compound = scores['compound']
        
        # Dynamic impact calculation - scales with sentiment strength
        # Instead of fixed buckets, use continuous scaling
        if abs(compound) < self.neutral_threshold:
            # Truly neutral
            impact = compound * self.sentiment_scale * 0.5  # Reduced for neutral
            category = "neutral"
            description = "neutral and conversational"
        else:
            # Scale impact by compound score
            # This gives more granular responses:
            # 0.1 = +2, 0.3 = +6, 0.5 = +10, 0.8 = +16, 1.0 = +20
            impact = compound * self.sentiment_scale
            
            # Determine category for feedback
            if compound >= 0.5:
                category = "very_positive"
                if compound >= 0.8:
                    description = "extremely warm and loving"
                else:
                    description = "very positive and supportive"
            elif compound > self.neutral_threshold:
                category = "positive"
                if compound >= 0.3:
                    description = "genuinely friendly and caring"
                else:
                    description = "friendly and positive"
            elif compound <= -0.5:
                category = "very_negative"
                if compound <= -0.8:
                    description = "deeply hurtful and hostile"
                else:
                    description = "hostile or very negative"
            else:
                category = "negative"
                if compound <= -0.3:
                    description = "quite negative and dismissive"
                else:
                    description = "slightly negative or dismissive"
        
        # Round to 1 decimal place for cleaner display
        impact = round(impact, 1)
        
        return impact, category, description
    
    def get_sentiment_emoji(self, compound_score: float) -> str:
        """
        Get an emoji representing the sentiment.
        
        Args:
            compound_score: Compound sentiment score from -1.0 to 1.0
            
        Returns:
            Emoji character
        """
        if compound_score >= 0.5:
            return "😊"
        elif compound_score >= 0.05:
            return "🙂"
        elif compound_score > -0.05:
            return "😐"
        elif compound_score > -0.5:
            return "😕"
        else:
            return "😠"
    
    def is_question(self, text: str) -> bool:
        """
        Determine if text is a question.
        
        Args:
            text: The text to check
            
        Returns:
            True if text contains a question mark or starts with question words
        """
        text = text.strip().lower()
        
        # Check for question mark
        if '?' in text:
            return True
        
        # Check for question words at start
        question_words = ['who', 'what', 'when', 'where', 'why', 'how', 'is', 'are', 'do', 'does', 'can', 'could', 'would', 'should']
        first_word = text.split()[0] if text.split() else ""
        
        return first_word in question_words
    
    def analyze_conversation_tone(self, messages: list[str]) -> Dict[str, any]:
        """
        Analyze overall tone of a conversation from multiple messages.
        
        Args:
            messages: List of message strings
            
        Returns:
            Dict with:
            - average_sentiment: Mean compound score
            - tone: Overall tone description
            - sentiment_trend: "improving", "declining", or "stable"
        """
        if not messages:
            return {
                'average_sentiment': 0.0,
                'tone': 'neutral',
                'sentiment_trend': 'stable'
            }
        
        scores = [self.analyze(msg)['compound'] for msg in messages if msg.strip()]
        
        if not scores:
            return {
                'average_sentiment': 0.0,
                'tone': 'neutral',
                'sentiment_trend': 'stable'
            }
        
        avg = sum(scores) / len(scores)
        
        # Determine tone
        if avg >= 0.3:
            tone = "very positive"
        elif avg >= 0.1:
            tone = "positive"
        elif avg >= -0.1:
            tone = "neutral"
        elif avg >= -0.3:
            tone = "negative"
        else:
            tone = "very negative"
        
        # Determine trend (compare first half to second half)
        if len(scores) >= 4:
            mid = len(scores) // 2
            first_half_avg = sum(scores[:mid]) / len(scores[:mid])
            second_half_avg = sum(scores[mid:]) / len(scores[mid:])
            
            diff = second_half_avg - first_half_avg
            
            if diff > 0.1:
                trend = "improving"
            elif diff < -0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            'average_sentiment': round(avg, 2),
            'tone': tone,
            'sentiment_trend': trend
        }
    
    def get_contextual_feedback(self, text: str, character_name: str) -> str:
        """
        Get contextual feedback for player about their message.
        
        Args:
            text: The player's message
            character_name: Name of the character they're talking to
            
        Returns:
            Feedback string to show player
        """
        impact, category, description = self.get_relationship_impact(text)
        
        if category == "very_negative":
            if impact < -15:
                return f"💔 That's really hurtful... (Relationship {impact:+.1f})"
            else:
                return f"⚠️  That might hurt {character_name}'s feelings. (Relationship {impact:+.1f})"
        elif category == "negative":
            return f"😕 That came across a bit harsh. (Relationship {impact:+.1f})"
        elif category == "very_positive":
            if impact > 15:
                return f"💚💚 {character_name} will feel so loved! (Relationship {impact:+.1f})"
            else:
                return f"💚 {character_name} will really appreciate that! (Relationship {impact:+.1f})"
        elif category == "positive":
            return f"😊 Nice and friendly. (Relationship {impact:+.1f})"
        else:
            return f"💬 Neutral. (Relationship {impact:+.1f})"


# Singleton instance
_analyzer: SentimentAnalyzer = None


def get_analyzer() -> SentimentAnalyzer:
    """Get or create the singleton sentiment analyzer"""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer


# Convenience functions
def analyze_message(text: str) -> Dict[str, float]:
    """Convenience function to analyze a single message"""
    return get_analyzer().analyze(text)


def get_impact(text: str) -> Tuple[float, str, str]:
    """Convenience function to get relationship impact"""
    return get_analyzer().get_relationship_impact(text)


def is_question(text: str) -> bool:
    """Convenience function to check if text is a question"""
    return get_analyzer().is_question(text)

