import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Main orchestrator that handles all business logic moved from main.py
    PURE BUSINESS LOGIC - No Streamlit/UI code here!
    """
    
    def __init__(self, storage, gemini_client, query_classifier):
        self.storage = storage
        self.gemini = gemini_client
        self.classifier = query_classifier
        logger.info("ConversationManager initialized")
    
    def build_array_context_aware_prompt(self, query_type, user_query):
        """
        MOVED FROM main.py - exact same function
        Build a context-aware prompt using array-based global + type-specific context.
        """
        try:
            # Get complete context (global + type-specific arrays + external data)
            context = self.storage.get_complete_context_for_query_type(query_type)
            
            global_info_array = context["global"]
            type_specific_info_array = context["type_specific"]
            external_data = context["external_data"]
            
            # Build base prompt
            prompt_parts = [
                f"You are an expert travel assistant specializing in {query_type.replace('_', ' ')}.",
                f"User Query: {user_query}",
                "",
            ]
            
            # Add GLOBAL context (shared across all query types)
            if global_info_array and len(global_info_array) > 0:
                prompt_parts.append("TRAVELER PROFILE (from previous conversations):")
                for info_item in global_info_array:
                    prompt_parts.append(f"- {info_item}")
                prompt_parts.append("")
            
            # Add TYPE-SPECIFIC context based on query type
            if type_specific_info_array and len(type_specific_info_array) > 0:
                type_name = query_type.replace('_', ' ').title()
                prompt_parts.append(f"{type_name.upper()} PREFERENCES:")
                for info_item in type_specific_info_array:
                    prompt_parts.append(f"- {info_item}")
                prompt_parts.append("")
            
            # Add EXTERNAL data if available
            if query_type == "packing_suggestions" and external_data.get("weather"):
                weather = external_data["weather"]
                prompt_parts.append("CURRENT WEATHER DATA:")
                prompt_parts.append(f"- Weather Forecast: {weather}")
                prompt_parts.append("")
            
            elif query_type == "local_attractions" and external_data.get("attractions"):
                attractions = external_data["attractions"]
                prompt_parts.append("CURRENT ATTRACTIONS DATA:")
                prompt_parts.append(f"- Available Attractions: {attractions}")
                prompt_parts.append("")
            
            # Final instruction with context awareness
            if global_info_array or type_specific_info_array:
                prompt_parts.append("Provide personalized advice based on their profile information above. If any important information is missing for better recommendations, politely ask for it.")
            else:
                prompt_parts.append("Provide helpful travel advice. Ask for key information that would help you give more personalized recommendations.")
            
            final_prompt = "\n".join(prompt_parts)
            logger.info(f"Built array context-aware prompt for {query_type} ({len(final_prompt)} chars)")
            logger.info(f"Used {len(global_info_array)} global + {len(type_specific_info_array)} type-specific context items")
            
            return final_prompt
            
        except Exception as e:
            logger.error(f"Error building array context-aware prompt: {str(e)}")
            # Fallback to simple prompt
            return f"You are a travel assistant. User asks: {user_query}. Please provide helpful advice."

    def format_conversation_for_display(self, conversation_history):
        """
        MOVED FROM main.py - exact same function
        Format conversation history for Streamlit display
        """
        formatted_messages = []
        
        for message in conversation_history:
            if "user_query" in message:
                formatted_messages.append({
                    "type": "user",
                    "content": message["user_query"],
                    "timestamp": message.get("timestamp"),
                    "classification": message.get("classification")
                })
            elif "assistant_answer" in message:
                formatted_messages.append({
                    "type": "assistant", 
                    "content": message["assistant_answer"],
                    "timestamp": message.get("timestamp")
                })
        
        return formatted_messages

    def process_user_message(self, user_input):
        """
        MOVED FROM main.py - the main processing logic that was in the chat input handler
        This contains the exact same steps that were in main.py
        """
        classification_result = None
        response = None
        final_prompt = None
        
        # Step 1: Classify the query (EXACT SAME LOGIC FROM main.py)
        try:
            classification_result = self.classifier.classify_query(user_input)
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            classification_result = {
                "type": "destination_recommendations",  # Safe fallback
                "external_data_needed": False,
                "external_data_type": "none",
                "key_Global_information": [],
                "key_specific_type_information": [],
                "confidence_score": 0.1,
                "primary_source": "fallback",
                "reasoning": f"Classification error - using fallback: {str(e)}",
                "fallback_used": True,
                "error": str(e)
            }
        
        # Step 2: Generate array context-aware response (EXACT SAME LOGIC FROM main.py)
        try:
            # Build array context-aware prompt
            final_prompt = self.build_array_context_aware_prompt(
                classification_result["type"], 
                user_input
            )
            
            # Generate response using the enhanced context-aware prompt
            response = self.gemini.generate_response(final_prompt, max_tokens=800)
            
            if not response or len(response.strip()) == 0:
                response = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            response = f"I'm experiencing technical difficulties generating a response. Please try again. (Error: {str(e)})"
        
        # Step 3: Save to Array-Based Context Storage (EXACT SAME LOGIC FROM main.py)
        if classification_result and response:
            try:
                # Extract and store using array-based method
                self.storage.extract_and_store_key_information(
                    classification_result["type"], 
                    classification_result.get("key_Global_information", []),
                    classification_result.get("key_specific_type_information", [])
                )
                
                # Save user query with full classification data
                query_data = {
                    "query": user_input,
                    **classification_result
                }
                self.storage.save_user_query(query_data)
                
                # Save assistant answer
                self.storage.save_assistant_answer(response)
                
                logger.info(f"Successfully saved to array-based context storage - Type: {classification_result['type']}")
                logger.info(f"Global items: {len(classification_result.get('key_Global_information', []))}")
                logger.info(f"Type-specific items: {len(classification_result.get('key_specific_type_information', []))}")
                
            except Exception as e:
                logger.error(f"Error saving to array-based context storage: {str(e)}")
        
        return {
            'classification_result': classification_result,
            'response': response,
            'final_prompt': final_prompt
        }