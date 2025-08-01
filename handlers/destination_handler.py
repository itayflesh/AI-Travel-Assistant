import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DestinationHandler:
    """
    Simplified prompt engineering for destination recommendations.
    
    Passes ALL data directly to the prompt without complex analysis.
    Demonstrates clean, straightforward AI engineering for Navan assignment.
    """
    
    def __init__(self):
        logger.info("DestinationHandler initialized")
    
    def build_final_prompt(self, user_query: str, global_context: List[str], 
                          type_specific_context: List[str], external_data: Dict[str, Any],
                          recent_conversation: List[Dict[str, Any]]) -> str:
        """
        Build the final engineered prompt for destination recommendations.
        
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
                type_specific_context_section = "DESTINATION-SPECIFIC PREFERENCES:\n"
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
                "You are an expert destination recommendation specialist with deep knowledge of global travel.",
                "",
                f"USER QUERY: \"{user_query}\"",
                "",
                conversation_context,
                global_context_section,
                type_specific_context_section,
                external_data_section,
                "DESTINATION RECOMMENDATION INSTRUCTIONS:",
                "",
                "Chain-of-thought reasoning process:",
                "1. First, analyze what information is available about the traveler's preferences, constraints, and requirements",
                "2. Determine if you have enough information to provide specific destination recommendations",
                "3. If you have sufficient information, provide personalized destination suggestions with clear reasoning",
                "4. If key information is missing, ask for the most important details first",
                "",
                "Response guidelines:",
                "• Use ALL available information from the context above",
                "• Be conversational and enthusiastic about travel",
                "• Provide specific destination recommendations when possible",
                "• Explain why each recommendation matches their stated preferences",
                "• If asking for more information, limit to 3-4 key questions",
                "• Keep the response focused and actionable",
                "• Use emojis sparingly but effectively",
                "",
                "Generate your destination recommendation response:"
            ]
            
            final_prompt = "\n".join(final_prompt_parts)
            
            logger.info(f"Built destination prompt: {len(final_prompt)} chars")
            return final_prompt
            
        except Exception as e:
            logger.error(f"Error building destination prompt: {str(e)}")
            # Fallback prompt
            return f"""You are a helpful travel destination expert. 
            
User asks: "{user_query}"

Global context: {global_context}
Type-specific context: {type_specific_context}
External data: {external_data}

Provide helpful destination recommendations based on all available information."""