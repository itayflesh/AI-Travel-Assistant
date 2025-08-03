import os
import redis
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GlobalContextStorage:
    """
    Main storage system that keeps track of what users tell us over time.
    
    """
    
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        self.session_key = "travel_assistant_session"
        
        # The three types of travel questions we handle
        self.valid_query_types = [
            "destination_recommendations",
            "packing_suggestions", 
            "local_attractions"
        ]
    
    def extract_and_store_key_information(self, query_type: str, key_Global_information: List[str], 
                                        key_specific_destination_recommendations_information: List[str],
                                        key_specific_packing_suggestions_information: List[str],
                                        key_specific_local_attractions_information: List[str]):
        """
        Saves all the useful info we extract from user queries.
        
        
        Save info for ALL types, not just the primary query type, because travel
        planning is interconnected. Someone asking about destinations might mention
        packing constraints, and we want to remember that.

        """
        try:
            # Store global stuff that applies to all travel questions
            if key_Global_information and len(key_Global_information) > 0:
                self._update_global_context(key_Global_information)
                logger.info(f"Updated global context with {len(key_Global_information)} items")
            
            # Store type-specific info for each category
            if key_specific_destination_recommendations_information and len(key_specific_destination_recommendations_information) > 0:
                self._update_type_specific_context("destination_recommendations", key_specific_destination_recommendations_information)
                logger.info(f"Updated destination_recommendations context with {len(key_specific_destination_recommendations_information)} items")
            
            if key_specific_packing_suggestions_information and len(key_specific_packing_suggestions_information) > 0:
                self._update_type_specific_context("packing_suggestions", key_specific_packing_suggestions_information)
                logger.info(f"Updated packing_suggestions context with {len(key_specific_packing_suggestions_information)} items")
            
            if key_specific_local_attractions_information and len(key_specific_local_attractions_information) > 0:
                self._update_type_specific_context("local_attractions", key_specific_local_attractions_information)
                logger.info(f"Updated local_attractions context with {len(key_specific_local_attractions_information)} items")
                
        except Exception as e:
            logger.error(f"Error storing key information: {str(e)}")
    
    def _update_global_context(self, new_info: List[str]):
        """
        Add new global context while being smart about duplicates and updates.
        
        Example: If someone mentions "budget: $2000" and later says "budget: $3000", we want
        to update the budget, not have two conflicting entries.

        """
        storage_key = f"{self.session_key}:global_context"
        
        # Get what we already know
        existing_context = self._get_global_context()
        
        # Merge intelligently - no duplicates, update existing keys
        updated_context = self._merge_context_arrays(existing_context, new_info)
        
        # Save it back
        self.redis_client.set(storage_key, json.dumps(updated_context))
        logger.info(f"Updated global context: now has {len(updated_context)} total items")
    
    def _update_type_specific_context(self, query_type: str, new_info: List[str]):
        """
        Update context for a specific travel question type.
        
        """
        if query_type not in self.valid_query_types:
            logger.warning(f"Invalid query type: {query_type}")
            return
            
        storage_key = f"{self.session_key}:{query_type}_specific_context"
        
        # Get existing context for this type
        existing_context = self._get_type_specific_context(query_type)
        
        # Merge intelligently
        updated_context = self._merge_context_arrays(existing_context, new_info)
        
        # Save it back
        self.redis_client.set(storage_key, json.dumps(updated_context))
        logger.info(f"Updated {query_type} specific context: now has {len(updated_context)} total items")
    
    def _merge_context_arrays(self, existing: List[str], new: List[str]) -> List[str]:
        """
        Smart merging of two arrays of "key: value" strings.
        
        - If someone updates a value (like changing their budget), we use the new one
        - If they add new info to an existing key, we combine the values
        - We avoid duplicates but preserve useful variations
        
        """
        if not new:
            return existing
        
        if not existing:
            return new.copy()
        
        # Parse existing items into a dict for easier manipulation
        existing_dict = {}
        remaining_items = []  # Stuff that doesn't follow "key: value" format
        
        for item in existing:
            if ":" in item:
                key, value = item.split(":", 1)
                key = key.strip()
                value = value.strip()
                existing_dict[key] = value
            else:
                remaining_items.append(item)  # Keep these as-is
        
        # Process new items
        for item in new:
            if item and item.strip():  # Skip empty stuff
                if ":" in item:
                    key, value = item.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key in existing_dict:
                        # If we already have this key, combine values if they're different
                        existing_values = existing_dict[key].split(", ")
                        if value not in existing_values:
                            existing_dict[key] = f"{existing_dict[key]}, {value}"
                    else:
                        # Brand new key-value pair
                        existing_dict[key] = value
                else:
                    # Non-structured info - add if not already there
                    if item not in remaining_items:
                        remaining_items.append(item)
        
        # Put it all back together
        result = [f"{key}: {value}" for key, value in existing_dict.items()] + remaining_items
        
        logger.debug(f"Merged arrays: {len(existing)} + {len(new)} = {len(result)} items")
        return result
    
    def get_complete_context_for_query_type(self, query_type: str) -> Dict[str, Any]:
        """
        Gather all the relevant context for answering a specific type of travel question.
        
        This combines:
        - Global context (always relevant - budget, dates, etc.)
        - Type-specific context (relevant to this question type)
        - Any cached external data that might help
        
        """
        try:
            # Global context is always relevant
            global_context = self._get_global_context()
            
            # Get context specific to this question type
            type_specific_context = self._get_type_specific_context(query_type)
            
            # Build the complete picture
            complete_context = {
                "global": global_context,
                "type_specific": type_specific_context,
                "external_data": {},
                "query_type": query_type
            }
            
            # Add relevant external data based on what type of question this is
            if query_type == "packing_suggestions":
                weather_data = self.get_external_data("weather_external_data")
                if weather_data:
                    complete_context["external_data"]["weather"] = weather_data
                    
            elif query_type == "local_attractions":
                attractions_data = self.get_external_data("attractions_external_data")
                if attractions_data:
                    complete_context["external_data"]["attractions"] = attractions_data
            
            logger.info(f"Built complete context for {query_type}: {len(global_context)} global + {len(type_specific_context)} type-specific items")
            return complete_context
            
        except Exception as e:
            logger.error(f"Error building complete context for {query_type}: {str(e)}")
            return {"global": [], "type_specific": [], "external_data": {}, "query_type": query_type}
    
    def _get_global_context(self) -> List[str]:
        """Get the global context that applies to all travel questions"""
        storage_key = f"{self.session_key}:global_context"
        
        try:
            data = self.redis_client.get(storage_key)
            if data:
                context = json.loads(data)
                return context if isinstance(context, list) else []
            else:
                return []
        except Exception as e:
            logger.error(f"Error getting global context: {str(e)}")
            return []
    
    def _get_type_specific_context(self, query_type: str) -> List[str]:
        """Get context specific to one type of travel question"""
        if query_type not in self.valid_query_types:
            return []
            
        storage_key = f"{self.session_key}:{query_type}_specific_context"
        
        try:
            data = self.redis_client.get(storage_key)
            if data:
                context = json.loads(data)
                return context if isinstance(context, list) else []
            else:
                return []
        except Exception as e:
            logger.error(f"Error getting {query_type} specific context: {str(e)}")
            return []
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get a complete overview of what we know about the user.
        
        This is mainly for debugging and the UI

        """
        try:
            global_context = self._get_global_context()
            
            # Global context stats
            global_stats = {
                "total_items": len(global_context),
                "current_data": global_context
            }
            
            # Type-specific context stats
            type_stats = {}
            for query_type in self.valid_query_types:
                type_context = self._get_type_specific_context(query_type)
                type_stats[query_type] = {
                    "total_items": len(type_context),
                    "current_data": type_context
                }
            
            return {
                "global_context": global_stats,
                "type_specific": type_stats,
                "external_data": {
                    "weather_cached": bool(self.get_external_data("weather_external_data")),
                    "attractions_cached": bool(self.get_external_data("attractions_external_data"))
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {"error": str(e)}
    
    def parse_context_for_display(self, context_array: List[str]) -> Dict[str, str]:
        """
        Convert our "key: value" strings into a dict for easier display in the UI.
        
        """
        parsed = {}
        for item in context_array:
            if ":" in item:
                key, value = item.split(":", 1)
                parsed[key.strip()] = value.strip()
            else:
                # Handle items that don't follow the key:value format
                parsed[f"info_{len(parsed)}"] = item.strip()
        
        return parsed
    
    def search_context_by_key(self, key: str, query_type: Optional[str] = None) -> List[str]:
        """
        Find all the info we have about a specific topic across both global and type-specific storage.

        """
        matches = []
        
        try:
            # Search global context
            global_context = self._get_global_context()
            for item in global_context:
                if item.lower().startswith(f"{key.lower()}:"):
                    matches.append(item)
            
            # Search type-specific context if requested
            if query_type and query_type in self.valid_query_types:
                type_context = self._get_type_specific_context(query_type)
                for item in type_context:
                    if item.lower().startswith(f"{key.lower()}:"):
                        matches.append(item)
                        
        except Exception as e:
            logger.error(f"Error searching context for key '{key}': {str(e)}")
        
        return matches
    
    def save_user_query(self, query_data: Dict[str, Any]):
        """Save a user's question along with all the classification metadata"""
        timestamp = datetime.now(timezone.utc).isoformat()
        query_key = f"{self.session_key}:user_query:{timestamp}"
        
        query_record = {
            "timestamp": timestamp,
            "user_query": query_data["query"],
            "classification": {
                "type": query_data["type"],
                "external_data_needed": query_data["external_data_needed"],
                "external_data_type": query_data.get("external_data_type"),
                "confidence_score": query_data["confidence_score"],
                "primary_source": query_data["primary_source"],
                "reasoning": query_data["reasoning"],
                "fallback_used": query_data.get("fallback_used", False),
                "external_data_reason": query_data.get("external_data_reason"),
                "key_Global_information": query_data.get("key_Global_information", []),
                "key_specific_destination_recommendations_information": query_data.get("key_specific_destination_recommendations_information", []),
                "key_specific_packing_suggestions_information": query_data.get("key_specific_packing_suggestions_information", []),
                "key_specific_local_attractions_information": query_data.get("key_specific_local_attractions_information", [])
            }
        }
        
        self.redis_client.set(query_key, json.dumps(query_record))
        self.redis_client.lpush(f"{self.session_key}:conversation_order", query_key)
        logger.info(f"Saved user query: {query_data['type']}")
    
    def save_assistant_answer(self, answer: str, classification_result: Dict[str, Any] = None):
        """Save our response to the user"""
        timestamp = datetime.now(timezone.utc).isoformat()
        answer_key = f"{self.session_key}:assistant_answer:{timestamp}"
        
        answer_record = {
            "timestamp": timestamp,
            "assistant_answer": answer
        }
        
        # Include classification info for external data display
        if classification_result:
            answer_record["classification"] = {
                "external_data_needed": classification_result.get("external_data_needed", False),
                "external_data_type": classification_result.get("external_data_type", "none")
            }
        
        self.redis_client.set(answer_key, json.dumps(answer_record))
        self.redis_client.lpush(f"{self.session_key}:conversation_order", answer_key)
        logger.info("Saved assistant answer")
    
    def save_external_data(self, data_type: str, data: Dict[str, Any]):
        """
        Cache external API data so we don't hammer the APIs on every request.
        
        We set a 1-hour TTL on this stuff since weather and attractions don't
        change that frequently.

        """
        valid_types = ["weather_external_data", "attractions_external_data"]
        
        if data_type not in valid_types:
            logger.error(f"Invalid external data type: {data_type}")
            return
        
        storage_key = f"{self.session_key}:{data_type}"
        
        # 1 hour TTL seems reasonable for this kind of data
        ttl_seconds = 3600
        
        cached_data = {
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expires_in": ttl_seconds  # Keep as metadata for manual checking
        }
        
        # Use setex() to set both value and TTL atomically
        self.redis_client.setex(storage_key, ttl_seconds, json.dumps(cached_data))
        
        logger.info(f"Saved external data: {data_type} with {ttl_seconds}s TTL")
    
    def get_external_data(self, data_type: str) -> Optional[Dict[str, Any]]:
        """
        Get cached external API data if it's still fresh.
        
        Returns None if the data is expired or doesn't exist.

        """
        storage_key = f"{self.session_key}:{data_type}"
        
        try:
            data = self.redis_client.get(storage_key)
            if not data:
                return None
            
            cached_data = json.loads(data)
            
            # Check if expired (backup check - Redis TTL should handle this)
            timestamp = datetime.fromisoformat(cached_data["timestamp"].replace('Z', '+00:00'))
            expires_in = cached_data.get("expires_in", 3600)
            
            if (datetime.now(timezone.utc) - timestamp).total_seconds() > expires_in:
                logger.info(f"External data expired: {data_type}")
                return None
            
            return cached_data["data"]
            
        except Exception as e:
            logger.error(f"Error getting external data {data_type}: {str(e)}")
            return None
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the full conversation history in chronological order.
        
        """
        conversation_keys = self.redis_client.lrange(f"{self.session_key}:conversation_order", 0, -1)
        conversation = []
        
        for key in reversed(conversation_keys):
            data = self.redis_client.get(key.decode())
            if data:
                conversation.append(json.loads(data))
        
        return conversation
    
    def clear_all_data(self):
        """
        wipe everything for this session.
        
        """
        try:
            keys_to_delete = self.redis_client.keys(f"{self.session_key}:*")
            if keys_to_delete:
                self.redis_client.delete(*keys_to_delete)
            logger.info("Cleared all session data")
        except Exception as e:
            logger.error(f"Error clearing data: {str(e)}")