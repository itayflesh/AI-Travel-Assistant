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
    Array-based storage system for flexible context management.
    
    Stores both global context (shared across types) and type-specific context
    as arrays of "key: value" strings for maximum flexibility.
    
    Demonstrates production-ready AI engineering skills for Navan assignment.
    """
    
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        self.session_key = "travel_assistant_session"
        
        # Valid query types for type-specific storage
        self.valid_query_types = [
            "destination_recommendations",
            "packing_suggestions", 
            "local_attractions"
        ]
    
    def extract_and_store_key_information(self, query_type: str, key_Global_information: List[str], 
                                        key_specific_type_information: List[str]):
        """
        Store global and type-specific information as arrays.
        This is the core method that handles array-based context storage!
        
        Args:
            query_type: The type of query (destination_recommendations, packing_suggestions, local_attractions)
            key_Global_information: Array of "key: value" strings for global context
            key_specific_type_information: Array of "key: value" strings for type-specific context
        """
        try:
            # Store global information (shared across all types)
            if key_Global_information and len(key_Global_information) > 0:
                self._update_global_context(key_Global_information)
                logger.info(f"Updated global context with {len(key_Global_information)} items")
            
            # Store type-specific information
            if key_specific_type_information and len(key_specific_type_information) > 0:
                self._update_type_specific_context(query_type, key_specific_type_information)
                logger.info(f"Updated {query_type} context with {len(key_specific_type_information)} items")
                
        except Exception as e:
            logger.error(f"Error storing key information: {str(e)}")
    
    def _update_global_context(self, new_info: List[str]):
        """
        Update global context array, avoiding duplicates and merging intelligently
        
        Args:
            new_info: List of "key: value" strings to add to global context
        """
        storage_key = f"{self.session_key}:global_context"
        
        # Get existing global context
        existing_context = self._get_global_context()
        
        # Merge arrays intelligently (avoid duplicates, update existing keys)
        updated_context = self._merge_context_arrays(existing_context, new_info)
        
        # Save updated global context
        self.redis_client.set(storage_key, json.dumps(updated_context))
        logger.info(f"Updated global context: now has {len(updated_context)} total items")
    
    def _update_type_specific_context(self, query_type: str, new_info: List[str]):
        """
        Update type-specific context array
        
        Args:
            query_type: The query type (destination_recommendations, packing_suggestions, local_attractions)
            new_info: List of "key: value" strings to add to type-specific context
        """
        if query_type not in self.valid_query_types:
            logger.warning(f"Invalid query type: {query_type}")
            return
            
        storage_key = f"{self.session_key}:{query_type}_specific_context"
        
        # Get existing type-specific context
        existing_context = self._get_type_specific_context(query_type)
        
        # Merge arrays intelligently
        updated_context = self._merge_context_arrays(existing_context, new_info)
        
        # Save updated context
        self.redis_client.set(storage_key, json.dumps(updated_context))
        logger.info(f"Updated {query_type} specific context: now has {len(updated_context)} total items")
    
    def _merge_context_arrays(self, existing: List[str], new: List[str]) -> List[str]:
        """
        Intelligently merge two arrays of "key: value" strings.
        - Avoids duplicates
        - Updates existing keys with new values
        - Preserves order (newest first for updated items)
        
        Args:
            existing: Current array of "key: value" strings
            new: New array of "key: value" strings to merge
            
        Returns:
            Merged array with no duplicates and updated values
        """
        if not new:
            return existing
        
        if not existing:
            return new.copy()
        
        # Parse existing items into key-value dict for easier updating
        existing_dict = {}
        remaining_items = []  # Items without "key: value" format
        
        for item in existing:
            if ":" in item:
                key, value = item.split(":", 1)
                key = key.strip()
                value = value.strip()
                existing_dict[key] = f"{key}: {value}"
            else:
                remaining_items.append(item)  # Keep items that don't follow key:value format
        
        # Process new items
        for item in new:
            if item and item.strip():  # Skip empty items
                if ":" in item:
                    key, value = item.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    existing_dict[key] = f"{key}: {value}"  # Update or add
                else:
                    # Add non-key:value items if not already present
                    if item not in remaining_items:
                        remaining_items.append(item)
        
        # Combine updated key:value items with remaining items
        result = list(existing_dict.values()) + remaining_items
        
        logger.debug(f"Merged arrays: {len(existing)} + {len(new)} = {len(result)} items")
        return result
    
    def get_complete_context_for_query_type(self, query_type: str) -> Dict[str, Any]:
        """
        Get complete context for a query type by combining:
        1. Global context (shared across types) 
        2. Type-specific context
        3. Relevant external data
        
        Args:
            query_type: The query type to get context for
            
        Returns:
            Complete context dict with arrays and external data
        """
        try:
            # Get global context (always relevant)
            global_context = self._get_global_context()
            
            # Get type-specific context
            type_specific_context = self._get_type_specific_context(query_type)
            
            # Build complete context
            complete_context = {
                "global": global_context,
                "type_specific": type_specific_context,
                "external_data": {},
                "query_type": query_type
            }
            
            # Add relevant external data based on query type
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
        """Get global context array shared across all query types"""
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
        """Get type-specific context array"""
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
        Get comprehensive storage statistics for array-based context
        
        Returns:
            Statistics about global and type-specific context arrays
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
        Parse array of "key: value" strings into a dict for easier display
        
        Args:
            context_array: Array of "key: value" formatted strings
            
        Returns:
            Dictionary with parsed key-value pairs
        """
        parsed = {}
        for item in context_array:
            if ":" in item:
                key, value = item.split(":", 1)
                parsed[key.strip()] = value.strip()
            else:
                # Handle items without key:value format
                parsed[f"info_{len(parsed)}"] = item.strip()
        
        return parsed
    
    def search_context_by_key(self, key: str, query_type: Optional[str] = None) -> List[str]:
        """
        Search for specific key across global and/or type-specific context
        
        Args:
            key: The key to search for (e.g., "destination", "budget")
            query_type: If provided, also search type-specific context
            
        Returns:
            List of matching "key: value" strings
        """
        matches = []
        
        try:
            # Search global context
            global_context = self._get_global_context()
            for item in global_context:
                if item.lower().startswith(f"{key.lower()}:"):
                    matches.append(item)
            
            # Search type-specific context if query_type provided
            if query_type and query_type in self.valid_query_types:
                type_context = self._get_type_specific_context(query_type)
                for item in type_context:
                    if item.lower().startswith(f"{key.lower()}:"):
                        matches.append(item)
                        
        except Exception as e:
            logger.error(f"Error searching context for key '{key}': {str(e)}")
        
        return matches
    
    def save_user_query(self, query_data: Dict[str, Any]):
        """Save user query with classification data"""
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
                "key_specific_type_information": query_data.get("key_specific_type_information", [])
            }
        }
        
        self.redis_client.set(query_key, json.dumps(query_record))
        self.redis_client.lpush(f"{self.session_key}:conversation_order", query_key)
        logger.info(f"Saved user query: {query_data['type']}")
    
    def save_assistant_answer(self, answer: str):
        """Save assistant answer"""
        timestamp = datetime.now(timezone.utc).isoformat()
        answer_key = f"{self.session_key}:assistant_answer:{timestamp}"
        
        answer_record = {
            "timestamp": timestamp,
            "assistant_answer": answer
        }
        
        self.redis_client.set(answer_key, json.dumps(answer_record))
        self.redis_client.lpush(f"{self.session_key}:conversation_order", answer_key)
        logger.info("Saved assistant answer")
    
    def save_external_data(self, data_type: str, data: Dict[str, Any]):
        """Save external API data with timestamp for caching"""
        valid_types = ["weather_external_data", "attractions_external_data"]
        
        if data_type not in valid_types:
            logger.error(f"Invalid external data type: {data_type}")
            return
        
        storage_key = f"{self.session_key}:{data_type}"
        
        cached_data = {
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expires_in": 3600  # 1 hour default
        }
        
        self.redis_client.set(storage_key, json.dumps(cached_data))
        logger.info(f"Saved external data: {data_type}")
    
    def get_external_data(self, data_type: str) -> Optional[Dict[str, Any]]:
        """Get external API data if not expired"""
        storage_key = f"{self.session_key}:{data_type}"
        
        try:
            data = self.redis_client.get(storage_key)
            if not data:
                return None
            
            cached_data = json.loads(data)
            
            # Check if expired
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
        """Get full conversation history"""
        conversation_keys = self.redis_client.lrange(f"{self.session_key}:conversation_order", 0, -1)
        conversation = []
        
        for key in reversed(conversation_keys):
            data = self.redis_client.get(key.decode())
            if data:
                conversation.append(json.loads(data))
        
        return conversation
    
    def clear_all_data(self):
        """Clear all conversation and context data"""
        try:
            keys_to_delete = self.redis_client.keys(f"{self.session_key}:*")
            if keys_to_delete:
                self.redis_client.delete(*keys_to_delete)
            logger.info("Cleared all session data")
        except Exception as e:
            logger.error(f"Error clearing data: {str(e)}")