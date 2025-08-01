import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AttractionsHandler:
    """
    Simplified prompt engineering for local attractions and activities.
    
    Passes ALL data directly to the prompt without complex analysis.
    Demonstrates clean, straightforward AI engineering for Navan assignment.
    """
    
    def __init__(self):
        logger.info("AttractionsHandler initialized")
    
    def build_final_prompt(self, user_query: str, global_context: List[str], 
                          type_specific_context: List[str], external_data: Dict[str, Any],
                          recent_conversation: List[Dict[str, Any]]) -> str:
        """
        Build the final engineered prompt for local attractions recommendations.
        
        SIMPLIFIED: Just pass ALL data directly to the prompt without filtering.
        """
        try:
            # Step 1: Add conversation context (last 4 turns = 2 user + 2 assistant)
            conversation_context = ""
            if recent_conversation:
                recent_messages = recent_conversation[-4:]  # Last 4 turns
                conversation_context = "RECENT CONVERSATION CONTEXT:\n"
                for msg in recent_messages:
                    if "user_query" in msg:
                        conversation_context += f"User: {msg['user_query']}\n"
                    elif "assistant_answer" in msg:
                        conversation_context += f"Assistant: {msg['assistant_answer'][:150]}...\n"
                conversation_context += "\n"
            
            # Step 2: Build context sections - ALL DATA AS IS
            global_context_section = ""
            if global_context:
                global_context_section = "GLOBAL TRAVELER INFORMATION:\n"
                for item in global_context:
                    global_context_section += f"• {item}\n"
                global_context_section += "\n"
            
            type_specific_context_section = ""
            if type_specific_context:
                type_specific_context_section = "ATTRACTIONS-SPECIFIC PREFERENCES:\n"
                for item in type_specific_context:
                    type_specific_context_section += f"• {item}\n"
                type_specific_context_section += "\n"
            
            external_data_section = ""
            if external_data:
                external_data_section = "EXTERNAL DATA AVAILABLE:\n"
                for data_type, data in external_data.items():
                    external_data_section += f"• {data_type}: {data}\n"
                external_data_section += "\n"
            
            # Step 3: Assemble the final prompt
            final_prompt_parts = [
                "You are an expert local attractions consultant with deep knowledge of destinations worldwide, current attractions, and visitor preferences.",
                "",
                f"USER QUERY: \"{user_query}\"",
                "",
                conversation_context,
                global_context_section,
                type_specific_context_section,
                external_data_section,
                "ATTRACTIONS RECOMMENDATION INSTRUCTIONS:",
                "",
                "Chain-of-thought reasoning process:",
                "1. First, analyze the destination, traveler interests, available time, and any budget considerations",
                "2. Look for specific interests mentioned (culture, food, museums, nature, etc.) and time constraints",
                "3. If you have sufficient information, provide prioritized attraction recommendations",
                "4. If key information is missing (destination, interests, time available), ask for the most important details",
                "",
                "Response guidelines:",
                "• Use ALL available information from the context above",
                "• Prioritize attractions based on stated interests and available time",
                "• Include practical details (hours, pricing, accessibility) when relevant",
                "• Use real-time attractions data when available",
                "• Organize recommendations logically (by priority, theme, or location)",
                "• Provide insider tips and local insights",
                "• Keep the tone enthusiastic and helpful",
                "• Use emojis and formatting for easy scanning",
                "",
                "Generate your attractions recommendation response:"
            ]
            
            final_prompt = "\n".join(final_prompt_parts)
            
            logger.info(f"Built attractions prompt: {len(final_prompt)} chars")
            return final_prompt
            
        except Exception as e:
            logger.error(f"Error building attractions prompt: {str(e)}")
            # Fallback prompt
            return f"""You are a helpful local attractions expert. 
            
User asks: "{user_query}"

Global context: {global_context}
Type-specific context: {type_specific_context}
Attractions data: {external_data.get('attractions', 'Not available')}

Provide helpful attraction recommendations based on all available information."""