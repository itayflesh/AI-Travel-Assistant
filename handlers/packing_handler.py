import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PackingHandler:
    """
    Simplified prompt engineering for packing suggestions.
    
    Passes ALL data directly to the prompt without complex analysis.
    Demonstrates clean, straightforward AI engineering for Navan assignment.
    """
    
    def __init__(self):
        logger.info("PackingHandler initialized")
    
    def build_final_prompt(self, user_query: str, global_context: List[str], 
                          type_specific_context: List[str], external_data: Dict[str, Any],
                          recent_conversation: List[Dict[str, Any]]) -> str:
        """
        Build the final engineered prompt for packing suggestions.
        
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
                type_specific_context_section = "PACKING-SPECIFIC PREFERENCES:\n"
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
                "You are an expert packing consultant with deep knowledge of travel gear, weather considerations, and activity-specific equipment.",
                "",
                f"USER QUERY: \"{user_query}\"",
                "",
                conversation_context,
                global_context_section,
                type_specific_context_section,
                external_data_section,
                "PACKING RECOMMENDATION INSTRUCTIONS:",
                "",
                "Chain-of-thought reasoning process:",
                "1. First, analyze the destination, weather data (if available), planned activities, and trip duration",
                "2. Consider the traveler's specific needs, luggage type, and any special requirements",
                "3. If you have sufficient information, provide a detailed, categorized packing list",
                "4. If key information is missing (destination, dates, activities), ask for the most important details",
                "",
                "Response guidelines:",
                "• Use ALL available information from the context above",
                "• Be practical and specific with packing advice",
                "• Use weather data when available for precise recommendations",
                "• Organize suggestions in clear categories (clothing, gear, essentials)",
                "• Consider the specific activities and trip duration mentioned",
                "• Provide helpful packing tips and space-saving techniques",
                "• Keep the tone helpful and encouraging",
                "• Use bullet points and emojis for easy scanning",
                "",
                "Generate your packing recommendation response:"
            ]
            
            final_prompt = "\n".join(final_prompt_parts)
            
            logger.info(f"Built packing prompt: {len(final_prompt)} chars")
            return final_prompt
            
        except Exception as e:
            logger.error(f"Error building packing prompt: {str(e)}")
            # Fallback prompt
            return f"""You are a helpful packing expert. 
            
User asks: "{user_query}"

Global context: {global_context}
Type-specific context: {type_specific_context}
Weather data: {external_data.get('weather', 'Not available')}

Provide helpful packing suggestions based on all available information."""
        """
        Build the packing recommendation strategy based on analysis.
        """
        if analysis["can_give_specific_advice"]:
            return self._build_specific_packing_advice(analysis, external_data)
        else:
            return self._build_information_gathering_strategy(analysis["missing_critical"])
    
    def _build_specific_packing_advice(self, analysis: Dict[str, Any], 
                                     external_data: Dict[str, Any]) -> str:
        """Build specific packing recommendations when we have enough information"""
        available = analysis["available"]
        sections = []
        
        sections.extend([
            "Based on your trip details, here's your personalized packing guide:",
            ""
        ])
        
        # Weather-specific recommendations
        if analysis["weather_available"]:
            sections.extend([
                "🌤️ WEATHER-BASED RECOMMENDATIONS:",
                "• [Provide temperature-appropriate clothing layers]",
                "• [Include weather protection gear if needed]",
                "• [Mention seasonal considerations]",
                ""
            ])
        
        # Activity-specific gear
        if "activities" in available:
            sections.extend([
                "🎯 ACTIVITY-SPECIFIC ITEMS:",
                "• [List gear for planned activities]",
                "• [Include any safety or specialized equipment]",
                ""
            ])
        
        # Structured packing list
        sections.extend([
            "📦 ORGANIZED PACKING LIST:",
            "",
            "CLOTHING & LAYERS:",
            "• [Weather-appropriate clothing items]",
            "",
            "WEATHER PROTECTION:",
            "• [Rain gear, sun protection, etc. based on forecast]",
            "",
            "ACTIVITY GEAR:",
            "• [Items specific to planned activities]",
            "",
            "ESSENTIALS:",
            "• [Personal care, documents, electronics]"
        ])
        
        # Pro tips based on their situation
        sections.extend([
            "",
            "💡 PACKING TIPS FOR YOUR TRIP:",
            "• [Provide personalized packing strategies]",
            "• [Mention any space-saving techniques]",
            "• [Include last-minute reminders]"
        ])
        
        return "\n".join(sections)
    
    def _build_information_gathering_strategy(self, missing_critical: List[Dict[str, str]]) -> str:
        """Build information gathering when we need more details for packing advice"""
        sections = []
        
        sections.extend([
            "I'd love to create a personalized packing list for you! To give you the most accurate",
            "recommendations, I need a few key details:",
            ""
        ])
        
        # Ask for most critical missing information
        for i, missing in enumerate(missing_critical[:3], 1):
            sections.append(f"{i}. {missing['question']}")
        
        sections.extend([
            "",
            "With these details, I can provide weather-appropriate clothing suggestions,",
            "activity-specific gear recommendations, and a well-organized packing checklist! 🎒"
        ])
        
        return "\n".join(sections)
    
    def build_final_prompt(self, user_query: str, global_context: List[str], 
                          type_specific_context: List[str], external_data: Dict[str, Any],
                          recent_conversation: List[Dict[str, Any]]) -> str:
        """
        Build the final engineered prompt for packing suggestions.
        
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
                type_specific_context_section = "PACKING-SPECIFIC PREFERENCES:\n"
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
                "You are an expert packing consultant with deep knowledge of travel gear, weather considerations, and activity-specific equipment.",
                "",
                f"USER QUERY: \"{user_query}\"",
                "",
                conversation_context,
                global_context_section,
                type_specific_context_section,
                external_data_section,
                "PACKING RECOMMENDATION INSTRUCTIONS:",
                "",
                "Chain-of-thought reasoning process:",
                "1. First, analyze the destination, weather data (if available), planned activities, and trip duration",
                "2. Consider the traveler's specific needs, luggage type, and any special requirements",
                "3. If you have sufficient information, provide a detailed, categorized packing list",
                "4. If key information is missing (destination, dates, activities), ask for the most important details",
                "",
                "Response guidelines:",
                "• Use ALL available information from the context above",
                "• Be practical and specific with packing advice",
                "• Use weather data when available for precise recommendations",
                "• Organize suggestions in clear categories (clothing, gear, essentials)",
                "• Consider the specific activities and trip duration mentioned",
                "• Provide helpful packing tips and space-saving techniques",
                "• Keep the tone helpful and encouraging",
                "• Use bullet points and emojis for easy scanning",
                "",
                "Generate your packing recommendation response:"
            ]
            
            final_prompt = "\n".join(final_prompt_parts)
            
            logger.info(f"Built packing prompt: {len(final_prompt)} chars")
            return final_prompt
            
        except Exception as e:
            logger.error(f"Error building packing prompt: {str(e)}")
            # Fallback prompt
            return f"""You are a helpful packing expert. 
            
User asks: "{user_query}"

Global context: {global_context}
Type-specific context: {type_specific_context}
Weather data: {external_data.get('weather', 'Not available')}

Provide helpful packing suggestions based on all available information."""