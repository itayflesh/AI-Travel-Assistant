import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import the new specialized handlers
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from handlers.destination_handler import DestinationHandler
from handlers.packing_handler import PackingHandler
from handlers.attractions_handler import AttractionsHandler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Main orchestrator that routes queries to specialized prompt handlers.
    
    UPDATED: Now uses advanced prompt engineering handlers instead of generic prompts.
    Each handler implements chain-of-thought reasoning and specialized prompt techniques.
    
    Demonstrates production-ready AI engineering architecture for Navan assignment.
    """
    
    def __init__(self, storage, gemini_client, query_classifier):
        self.storage = storage
        self.gemini = gemini_client
        self.classifier = query_classifier
        
        # Initialize specialized handlers
        self.destination_handler = DestinationHandler()
        self.packing_handler = PackingHandler()
        self.attractions_handler = AttractionsHandler()
        
        # Handler routing map
        self.handlers = {
            "destination_recommendations": self.destination_handler,
            "packing_suggestions": self.packing_handler,
            "local_attractions": self.attractions_handler
        }
        
        logger.info("ConversationManager initialized with specialized handlers")
    
    def route_to_handler(self, query_type: str, user_query: str, 
                        global_context: List[str], type_specific_context: List[str],
                        external_data: Dict[str, Any], recent_conversation: List[Dict[str, Any]]) -> str:
        """
        Route the query to the appropriate specialized handler.
        
        This replaces the old generic prompt building with advanced, type-specific prompts.
        
        Args:
            query_type: The classified query type
            user_query: Original user query
            global_context: Global context array
            type_specific_context: Type-specific context array  
            external_data: External API data
            recent_conversation: Recent conversation history
            
        Returns:
            Engineered prompt ready for Gemini
        """
        try:
            # Get the appropriate handler
            handler = self.handlers.get(query_type)
            
            if not handler:
                logger.warning(f"No handler found for query type: {query_type}, using fallback")
                return self._build_fallback_prompt(user_query, global_context, type_specific_context, external_data)
            
            # Use the specialized handler to build the prompt
            engineered_prompt = handler.build_final_prompt(
                user_query=user_query,
                global_context=global_context,
                type_specific_context=type_specific_context,
                external_data=external_data,
                recent_conversation=recent_conversation
            )
            
            logger.info(f"Successfully routed to {query_type} handler, prompt length: {len(engineered_prompt)} chars")
            return engineered_prompt
            
        except Exception as e:
            logger.error(f"Error routing to handler for {query_type}: {str(e)}")
            return self._build_fallback_prompt(user_query, global_context, type_specific_context, external_data)
    
    def _build_fallback_prompt(self, user_query: str, global_context: List[str], 
                              type_specific_context: List[str], external_data: Dict[str, Any]) -> str:
        """
        Fallback prompt when handlers fail or are unavailable.
        """
        context_info = ""
        if global_context or type_specific_context:
            context_info = f"Context available: {global_context + type_specific_context}"
        
        external_info = ""
        if external_data:
            external_info = f"External data: {list(external_data.keys())}"
        
        return f"""You are a helpful travel assistant.

User query: "{user_query}"

{context_info}
{external_info}

Please provide helpful travel advice based on the available information."""
    
    def get_external_data_for_query_type(self, query_type: str, classification_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get relevant external data based on query type and classification.
        
        This ensures handlers receive the right external data for their specialized prompts.
        """
        external_data = {}
        
        try:
            # Check if external data is needed based on classification
            if not classification_result.get("external_data_needed", False):
                return external_data
            
            external_data_type = classification_result.get("external_data_type", "none")
            
            # Get weather data for packing suggestions
            if query_type == "packing_suggestions" and external_data_type in ["weather", "both"]:
                weather_data = self.storage.get_external_data("weather_external_data")
                if weather_data:
                    external_data["weather"] = weather_data
                    logger.info("Added weather data for packing handler")
            
            # Get attractions data for local attractions
            elif query_type == "local_attractions" and external_data_type in ["attractions", "both"]:
                attractions_data = self.storage.get_external_data("attractions_external_data")
                if attractions_data:
                    external_data["attractions"] = attractions_data
                    logger.info("Added attractions data for attractions handler")
            
        except Exception as e:
            logger.error(f"Error getting external data for {query_type}: {str(e)}")
        
        return external_data
    
    def format_conversation_for_display(self, conversation_history):
        """
        Format conversation history for Streamlit display.
        UNCHANGED - still needed for UI
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
        UPDATED: Main processing logic now uses specialized handlers.
        
        This replaces the old generic prompt building with advanced handler routing.
        """
        classification_result = None
        response = None
        final_prompt = None
        
        # Step 1: Classify the query (UNCHANGED)
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
        
        # Step 2: Get external data if needed (UPDATED)
        external_data = self.get_external_data_for_query_type(
            classification_result["type"], 
            classification_result
        )
        
        # Step 3: Get context data (UNCHANGED)
        try:
            context = self.storage.get_complete_context_for_query_type(classification_result["type"])
            global_context = context["global"]
            type_specific_context = context["type_specific"]
            
            # Get recent conversation for context
            recent_conversation = self.storage.get_conversation_history()[-6:] if self.storage.get_conversation_history() else []
            
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            global_context = []
            type_specific_context = []
            recent_conversation = []
        
        # Step 4: Route to specialized handler (NEW!)
        try:
            final_prompt = self.route_to_handler(
                query_type=classification_result["type"],
                user_query=user_input,
                global_context=global_context,
                type_specific_context=type_specific_context,
                external_data=external_data,
                recent_conversation=recent_conversation
            )
            
            # Generate response using the specialized prompt
            response = self.gemini.generate_response(final_prompt, max_tokens=800)
            
            if not response or len(response.strip()) == 0:
                response = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            response = f"I'm experiencing technical difficulties generating a response. Please try again. (Error: {str(e)})"
        
        # Step 5: Save to context storage (UNCHANGED)
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
                logger.info(f"Used specialized {classification_result['type']} handler")
                
            except Exception as e:
                logger.error(f"Error saving to array-based context storage: {str(e)}")
        
        return {
            'classification_result': classification_result,
            'response': response,
            'final_prompt': final_prompt,
            'handler_used': classification_result["type"] if classification_result else "fallback"
        }