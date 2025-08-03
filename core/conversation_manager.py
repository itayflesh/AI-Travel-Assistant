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

# Import external APIs
from external_apis.attraction_api import get_attractions_for_destination
from external_apis.weather_api import get_weather_for_destination

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationManager:
    """
    The main coordinator that routes user queries to the right specialized handlers.
    
    figures out what type of travel question the user is asking and sends it to the handler that knows how to deal with it best.
    """
    
    def __init__(self, storage, gemini_client, query_classifier):
        self.storage = storage
        self.gemini = gemini_client
        self.classifier = query_classifier
        
        # Set up our specialized handlers for different query types
        self.destination_handler = DestinationHandler()
        self.packing_handler = PackingHandler()
        self.attractions_handler = AttractionsHandler()
        
        # Map query types to their handlers
        self.handlers = {
            "destination_recommendations": self.destination_handler,
            "packing_suggestions": self.packing_handler,
            "local_attractions": self.attractions_handler
        }
        
        logger.info("ConversationManager initialized with specialized handlers and Gemini geocoding support")
    

    def route_to_handler(self, query_type: str, user_query: str, 
                    global_context: List[str], type_specific_context: List[str],
                    external_data: Dict[str, Any], recent_conversation: List[Dict[str, Any]], 
                    classification_result: Dict[str, Any]) -> str:
        """
        Send the query to the right handler to build a specialized prompt.
                """
        try:
            # Get the appropriate handler
            handler = self.handlers.get(query_type)
            
            if not handler:
                logger.warning(f"No handler found for query type: {query_type}, using fallback")
                return self._build_fallback_prompt(user_query, global_context, type_specific_context, external_data)
            
            # Gather context from all handler types so handlers can cross-reference
            all_type_specific_contexts = {}
            
            try:
                for handler_type in self.storage.valid_query_types:
                    type_context = self.storage._get_type_specific_context(handler_type)
                    all_type_specific_contexts[handler_type] = type_context
            except Exception as e:
                logger.warning(f"Could not get all type-specific contexts: {str(e)}")
                # Fallback to just the current type
                all_type_specific_contexts[query_type] = type_specific_context
            
            # Start with the primary context for this handler
            handler_specific_context = type_specific_context.copy()
            
            # For destination recommendations, also pull in relevant info from other areas
            if query_type == "destination_recommendations":
                # Add constraints from packing that might affect destination choice
                packing_context = all_type_specific_contexts.get("packing_suggestions", [])
                for item in packing_context:
                    if any(keyword in item.lower() for keyword in ["luggage_type", "constraints", "accessibility"]):
                        if item not in handler_specific_context:
                            handler_specific_context.append(item)
                
                # Add time/mobility info from attractions planning
                attractions_context = all_type_specific_contexts.get("local_attractions", [])
                for item in attractions_context:
                    if any(keyword in item.lower() for keyword in ["time_available", "mobility", "accessibility"]):
                        if item not in handler_specific_context:
                            handler_specific_context.append(item)
            
            # Let the handler build the specialized prompt
            # FOR BOTH DESTINATION AND ATTRACTIONS HANDLERS: Pass classification_result
            if query_type in ["destination_recommendations", "local_attractions"]:
                engineered_prompt = handler.build_final_prompt(
                    user_query=user_query,
                    global_context=global_context,
                    type_specific_context=handler_specific_context,
                    external_data=external_data,
                    recent_conversation=recent_conversation,
                    classification_result=classification_result  # Pass classification result
                )
            else:
                # Other handlers (packing) use the original signature
                engineered_prompt = handler.build_final_prompt(
                    user_query=user_query,
                    global_context=global_context,
                    type_specific_context=handler_specific_context,
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
        """Basic prompt when our specialized handlers aren't available."""
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
    
    def _extract_destination_from_context(self, classification_result: Dict[str, Any]) -> Optional[str]:
        """
        Figure out what destination the user is asking about.
        
        """
        try:
            logger.info(f"=== Looking for destination in classification ===")
            logger.info(f"Full classification result: {classification_result}")
            
            # First check the new information from this query
            global_info = classification_result.get("key_Global_information", [])
            logger.info(f"New global info: {global_info}")
            
            for i, info in enumerate(global_info):
                logger.info(f"Checking new global info {i}: '{info}'")
                if info.lower().startswith("destination:"):
                    destination = info.split(":", 1)[1].strip()
                    if destination:
                        logger.info(f"Found destination in new classification: {destination}")
                        return destination
            
            # Check type-specific information from the classification
            for type_key in ["key_specific_destination_recommendations_information", 
                           "key_specific_packing_suggestions_information", 
                           "key_specific_local_attractions_information"]:
                type_info = classification_result.get(type_key, [])
                logger.info(f"New {type_key}: {type_info}")
                
                for info in type_info:
                    logger.info(f"Checking type-specific item: '{info}'")
                    if info.lower().startswith("destination:"):
                        destination = info.split(":", 1)[1].strip()
                        if destination:
                            logger.info(f"Found destination in type-specific context: {destination}")
                            return destination
            
            # If nothing in the new classification, check what we've stored from earlier
            logger.info("No destination in new classification - checking stored context...")
            try:
                accumulated_global_context = self.storage._get_global_context()
                logger.info(f"Stored global context: {accumulated_global_context}")
                
                for item in accumulated_global_context:
                    logger.info(f"Checking stored item: '{item}'")
                    if item.lower().startswith("destination:"):
                        destination = item.split(":", 1)[1].strip()
                        if destination:
                            logger.info(f"Found destination in stored context: {destination}")
                            return destination
                            
            except Exception as e:
                logger.error(f"Error checking stored context: {str(e)}")
            
            # Last resort: try to parse it from the user's actual query
            query = classification_result.get("query", "")
            logger.info(f"Final fallback: parsing from query: '{query}'")
            
            import re
            
            # Common patterns we see in travel queries
            patterns = [
                r"(?:fly|travel|go|visit)\s+to\s+([A-Za-z\s]+?)(?:\s*(?:but|and|,|\.|$))",
                r"in\s+([A-Za-z\s]+?)(?:\s*[,.]|$)",
                r"visit\s+([A-Za-z\s]+?)(?:\s*[,.]|$)",
                r"go\s+to\s+([A-Za-z\s]+?)(?:\s*[,.]|$)"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    destination = match.group(1).strip()
                    if len(destination) > 2:  # Avoid single words
                        logger.info(f"Regex extraction found: {destination}")
                        return destination
            
            logger.warning("Could not find destination anywhere")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting destination: {str(e)}")
            return None
    
    def get_external_data_for_query_type(self, query_type: str, classification_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch weather and/or attractions data if the query needs it.
       
        """
        external_data = {}
        
        try:
            # Skip if the classifier said we don't need external data
            if not classification_result.get("external_data_needed", False):
                return external_data
            
            external_data_type = classification_result.get("external_data_type", "none")
            
            # Get weather data if needed
            if external_data_type in ["weather", "both"]:
                # Check cache first
                weather_data = self.storage.get_external_data("weather_external_data")
                
                if weather_data:
                    external_data["weather"] = weather_data
                    logger.info(f"Using cached weather data for {query_type} handler")
                else:
                    # Cache miss - hit the API
                    destination = self._extract_destination_from_context(classification_result)
                    
                    if destination:
                        logger.info(f"Fetching fresh weather data for {query_type}: {destination}")
                        # Pass Gemini client for better geocoding
                        weather_result = get_weather_for_destination(destination, self.gemini)
                        
                        if weather_result.get("success"):
                            # Cache it for an hour
                            self.storage.save_external_data("weather_external_data", weather_result)
                            external_data["weather"] = weather_result
                            
                            # Log what geocoding method worked
                            geocoding_method = weather_result.get("geocoding_method", "unknown")
                            temp = weather_result.get('current_weather', {}).get('temperature', 'N/A')
                            
                            if geocoding_method == "gemini_tourism_center":
                                tourism_center = weather_result.get('tourism_center', 'Unknown area')
                                logger.info(f"Got weather via Gemini tourism center for {query_type} - {destination} ({tourism_center}): {temp}°C")
                            else:
                                logger.info(f"Got weather via city lookup for {query_type} - {destination}: {temp}°C")
                        else:
                            logger.error(f"Weather API failed for {query_type}: {weather_result.get('error')}")
                    else:
                        logger.warning(f"No destination found for {query_type} weather query - skipping API call")
            
            # Get attractions data if needed
            if external_data_type in ["attractions", "both"]:
                # Check cache first
                attractions_data = self.storage.get_external_data("attractions_external_data")
                
                if attractions_data:
                    external_data["attractions"] = attractions_data
                    logger.info(f"Using cached attractions data for {query_type} handler")
                else:
                    # Cache miss - hit the API
                    destination = self._extract_destination_from_context(classification_result)
                    
                    if destination:
                        logger.info(f"Fetching fresh attractions data for {query_type}: {destination}")
                        # Pass Gemini client for better geocoding
                        attractions_result = get_attractions_for_destination(destination, self.gemini)
                        
                        if attractions_result.get("success"):
                            # Cache it for an hour
                            self.storage.save_external_data("attractions_external_data", attractions_result)
                            external_data["attractions"] = attractions_result
                            
                            # Log what geocoding method worked
                            geocoding_method = attractions_result.get("geocoding_method", "unknown")
                            total_found = attractions_result.get('total_found', 0)
                            
                            if geocoding_method == "gemini_tourism_center":
                                tourism_center = attractions_result.get('tourism_center', 'Unknown area')
                                logger.info(f"Got {total_found} attractions via Gemini tourism center for {query_type} - {destination} ({tourism_center})")
                            else:
                                logger.info(f"Got {total_found} attractions via Amadeus geocoding for {query_type} - {destination}")
                        else:
                            logger.error(f"Attractions API failed for {query_type}: {attractions_result.get('error')}")
                    else:
                        logger.warning(f"No destination found for {query_type} attractions query - skipping API call")
            
        except Exception as e:
            logger.error(f"Error getting external data for {query_type}: {str(e)}")
            # Don't crash - return whatever we managed to get
        
        return external_data
    
    def format_conversation_for_display(self, conversation_history):
        """Format conversation history for the Streamlit UI."""
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
        The main workflow that handles a user's message from start to finish.
        
        Now passes classification_result to route_to_handler.
        """
        classification_result = None
        response = None
        final_prompt = None
        
        # Step 1: Figure out what type of travel question this is
        try:
            # Get recent conversation for better classification context
            recent_conversation = self.storage.get_conversation_history()[-6:] if self.storage.get_conversation_history() else []
            classification_result = self.classifier.classify_query(user_input, recent_conversation)
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            # Safe fallback when classification breaks
            classification_result = {
                "type": "destination_recommendations",
                "external_data_needed": False,
                "external_data_type": "none",
                "key_Global_information": [],
                "key_specific_destination_recommendations_information": [],
                "key_specific_packing_suggestions_information": [],
                "key_specific_local_attractions_information": [],
                "confidence_score": 0.1,
                "primary_source": "fallback",
                "reasoning": f"Classification error - using fallback: {str(e)}",
                "fallback_used": True,
                "error": str(e)
            }
        
        # Step 2: Get external data if the query needs it
        external_data = self.get_external_data_for_query_type(
            classification_result["type"], 
            classification_result
        )
        
        # Step 3: Save the extracted information to our context storage
        if classification_result:
            try:
                # Store all the arrays we extracted
                self.storage.extract_and_store_key_information(
                    classification_result["type"], 
                    classification_result.get("key_Global_information", []),
                    classification_result.get("key_specific_destination_recommendations_information", []),
                    classification_result.get("key_specific_packing_suggestions_information", []),
                    classification_result.get("key_specific_local_attractions_information", [])
                )
                
                # Save the full query with classification
                query_data = {
                    "query": user_input,
                    **classification_result
                }
                self.storage.save_user_query(query_data)
                
                logger.info(f"Saved to context storage - Type: {classification_result['type']}")
                
            except Exception as e:
                logger.error(f"Error saving to context storage: {str(e)}")
        
        # Step 4: Get relevant context for this query type
        try:
            context = self.storage.get_complete_context_for_query_type(classification_result["type"])
            global_context = context["global"]
            type_specific_context = context["type_specific"]
            
            # Get recent conversation for additional context
            recent_conversation = self.storage.get_conversation_history()[-6:] if self.storage.get_conversation_history() else []
            
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            global_context = []
            type_specific_context = []
            recent_conversation = []
        
        # Step 5: Route to the specialized handler and generate response
        try:
            final_prompt = self.route_to_handler(
                query_type=classification_result["type"],
                user_query=user_input,
                global_context=global_context,
                type_specific_context=type_specific_context,
                external_data=external_data,
                recent_conversation=recent_conversation,
                classification_result=classification_result  
            )
            
            # Generate the actual response
            response = self.gemini.generate_response(final_prompt, max_tokens=800)
            
            if not response or len(response.strip()) == 0:
                response = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            response = f"I'm experiencing technical difficulties generating a response. Please try again. (Error: {str(e)})"
        
        # Step 6: Save the assistant's response
        if response:
            try:
                self.storage.save_assistant_answer(response)
                logger.info(f"Used specialized {classification_result['type']} handler")
                
            except Exception as e:
                logger.error(f"Error saving assistant answer: {str(e)}")
        
        return {
            'classification_result': classification_result,
            'response': response,
            'final_prompt': final_prompt,
            'handler_used': classification_result["type"] if classification_result else "fallback"
        }