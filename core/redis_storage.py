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
    Advanced storage system that handles both global context (shared across types)
    and type-specific context (unique to each query type).
    
    This solves the problem where key information like 'destination' is relevant
    to multiple query types but should be shared intelligently.
    
    Demonstrates production-ready AI engineering skills for Navan assignment.
    """
    
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        self.session_key = "travel_assistant_session"
        
        # Define which fields are "global" vs "type-specific"
        self.global_fields = {
            "destination",      # Shared across ALL types
            "travel_dates",     # Shared across packing + attractions
            "duration",         # Shared across destination + packing
            "budget",           # Can be overall budget OR per-activity budget
            "group_size",       # Affects destinations, attractions, and packing
            "interests"         # Affects destinations and attractions
        }
        
        # Type-specific schemas (only unique fields)
        self.type_specific_schemas = {
            "destination_recommendations": {
                "travel_style": None,           # Only for destinations
                "constraints": [],              # Only for destinations  
                "previous_destinations": [],    # Only for destinations
                "climate_preference": None,     # Only for destinations
                "other": {}
            },
            "packing_suggestions": {
                "activities": [],               # Only for packing
                "luggage_type": None,           # Only for packing
                "special_needs": [],            # Only for packing
                "laundry_availability": None,   # Only for packing
                "climate_preference": None,     # Only for packing
                "other": {}
            },
            "local_attractions": {
                "time_available": None,         # Only for attractions
                "mobility": None,               # Only for attractions
                "budget_per_activity": None,    # Only for attractions (different from global budget)
                "group_type": None,             # Only for attractions
                "age_group": None,              # Only for attractions
                "accessibility_needs": [],     # Only for attractions
                "other": {}
            }
        }
        
        # Global context schema
        self.global_schema = {
            "destination": None,        # Current/main destination
            "travel_dates": None,       # When they're traveling
            "duration": None,           # How long the trip is
            "budget": None,             # Overall trip budget
            "group_size": None,         # How many people
            "interests": []             # General interests
        }
    
    def extract_and_store_key_information(self, query_type: str, key_information: Dict[str, Any]):
        """
        Intelligently separate global vs type-specific information and store appropriately.
        This is the core method that handles the "super" key information problem!
        """
        if not key_information:
            logger.info(f"No key information to store for {query_type}")
            return
        
        try:
            # Separate global from type-specific information
            global_info = {}
            type_specific_info = {}
            
            for key, value in key_information.items():
                if key in self.global_fields:
                    global_info[key] = value
                else:
                    type_specific_info[key] = value
            
            # Store global information (shared across all types)
            if global_info:
                self._update_global_context(global_info)
                logger.info(f"Updated global context: {list(global_info.keys())}")
            
            # Store type-specific information
            if type_specific_info:
                self._update_type_specific_context(query_type, type_specific_info)
                logger.info(f"Updated {query_type} context: {list(type_specific_info.keys())}")
                
        except Exception as e:
            logger.error(f"Error storing key information: {str(e)}")
    
    def _update_global_context(self, new_info: Dict[str, Any]):
        """Update global context that's shared across all query types"""
        storage_key = f"{self.session_key}:global_context"
        
        # Get existing global context
        existing_context = self._get_global_context()
        
        # Merge intelligently
        updated_context = self._merge_context_data(existing_context, new_info)
        
        # Save updated global context
        self.redis_client.set(storage_key, json.dumps(updated_context))
        logger.info(f"Updated global context: {list(new_info.keys())}")
    
    def _update_type_specific_context(self, query_type: str, new_info: Dict[str, Any]):
        """Update type-specific context"""
        storage_key = f"{self.session_key}:{query_type}_specific_context"
        
        # Get existing type-specific context
        existing_context = self._get_type_specific_context(query_type)
        
        # Merge intelligently
        updated_context = self._merge_context_data(existing_context, new_info)
        
        # Save updated context
        self.redis_client.set(storage_key, json.dumps(updated_context))
        logger.info(f"Updated {query_type} specific context: {list(new_info.keys())}")
    
    def get_complete_context_for_query_type(self, query_type: str) -> Dict[str, Any]:
        """
        Get complete context for a query type by combining:
        1. Global context (shared across types)
        2. Type-specific context
        3. Relevant external data
        
        This is the magic method for context-aware prompt engineering!
        """
        try:
            # Start with global context (always relevant)
            global_context = self._get_global_context()
            
            # Add type-specific context
            type_specific_context = self._get_type_specific_context(query_type)
            
            # Combine contexts
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
            
            logger.info(f"Built complete context for {query_type}")
            return complete_context
            
        except Exception as e:
            logger.error(f"Error building complete context for {query_type}: {str(e)}")
            return {"global": {}, "type_specific": {}, "external_data": {}, "query_type": query_type}
    
    def _get_global_context(self) -> Dict[str, Any]:
        """Get global context shared across all query types"""
        storage_key = f"{self.session_key}:global_context"
        
        try:
            data = self.redis_client.get(storage_key)
            if data:
                return json.loads(data)
            else:
                return self.global_schema.copy()
        except Exception as e:
            logger.error(f"Error getting global context: {str(e)}")
            return self.global_schema.copy()
    
    def _get_type_specific_context(self, query_type: str) -> Dict[str, Any]:
        """Get type-specific context"""
        if query_type not in self.type_specific_schemas:
            return {}
            
        storage_key = f"{self.session_key}:{query_type}_specific_context"
        
        try:
            data = self.redis_client.get(storage_key)
            if data:
                return json.loads(data)
            else:
                return self.type_specific_schemas[query_type].copy()
        except Exception as e:
            logger.error(f"Error getting {query_type} specific context: {str(e)}")
            return self.type_specific_schemas[query_type].copy()
    
    def get_missing_information_for_type(self, query_type: str) -> Dict[str, List[str]]:
        """
        Get missing information categorized by global vs type-specific.
        This helps prompt engineering ask for the right missing info!
        """
        try:
            global_context = self._get_global_context()
            type_specific_context = self._get_type_specific_context(query_type)
            
            missing = {
                "global": [],
                "type_specific": []
            }
            
            # Check missing global fields
            for field in self.global_fields:
                if field in self.global_schema:
                    value = global_context.get(field)
                    if self._is_field_empty(value):
                        missing["global"].append(field)
            
            # Check missing type-specific fields
            if query_type in self.type_specific_schemas:
                schema = self.type_specific_schemas[query_type]
                for field, default_value in schema.items():
                    if field == "other":
                        continue
                    value = type_specific_context.get(field)
                    if self._is_field_empty(value):
                        missing["type_specific"].append(field)
            
            return missing
            
        except Exception as e:
            logger.error(f"Error getting missing information for {query_type}: {str(e)}")
            return {"global": [], "type_specific": []}
    
    def _is_field_empty(self, value) -> bool:
        """Check if a field value is considered empty"""
        if value is None or value == "":
            return True
        if isinstance(value, list) and len(value) == 0:
            return True
        return False
    
    def _merge_context_data(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Intelligently merge context data"""
        result = existing.copy()
        
        for key, value in new.items():
            if self._is_field_empty(value):
                continue  # Skip empty values
                
            if key == "other":
                # Merge other dict
                if isinstance(value, dict):
                    if "other" not in result:
                        result["other"] = {}
                    result["other"].update(value)
            elif isinstance(value, list):
                # Merge lists without duplicates
                if key not in result:
                    result[key] = []
                elif not isinstance(result[key], list):
                    result[key] = []
                
                for item in value:
                    if item not in result[key]:
                        result[key].append(item)
            else:
                # Update scalar values (latest wins)
                result[key] = value
        
        return result
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics"""
        try:
            global_context = self._get_global_context()
            
            # Calculate global context completeness
            global_fields_filled = sum(1 for field in self.global_fields 
                                     if not self._is_field_empty(global_context.get(field)))
            global_completeness = (global_fields_filled / len(self.global_fields)) * 100
            
            # Calculate type-specific completeness
            type_completeness = {}
            for query_type in self.type_specific_schemas.keys():
                type_context = self._get_type_specific_context(query_type)
                schema = self.type_specific_schemas[query_type]
                
                fields_to_check = [f for f in schema.keys() if f != "other"]
                filled_fields = sum(1 for field in fields_to_check 
                                  if not self._is_field_empty(type_context.get(field)))
                
                completeness = (filled_fields / len(fields_to_check)) * 100 if fields_to_check else 0
                type_completeness[query_type] = {
                    "completeness_percent": round(completeness, 1),
                    "filled_fields": filled_fields,
                    "total_fields": len(fields_to_check)
                }
            
            return {
                "global_context": {
                    "completeness_percent": round(global_completeness, 1),
                    "filled_fields": global_fields_filled,
                    "total_fields": len(self.global_fields),
                    "current_data": {k: v for k, v in global_context.items() if not self._is_field_empty(v)}
                },
                "type_specific": type_completeness,
                "external_data": {
                    "weather_cached": bool(self.get_external_data("weather_external_data")),
                    "attractions_cached": bool(self.get_external_data("attractions_external_data"))
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {"error": str(e)}
    
    # Include all the existing methods from previous storage
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
                "key_information": query_data["key_information"]
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
        """Clear all conversation and profile data"""
        try:
            keys_to_delete = self.redis_client.keys(f"{self.session_key}:*")
            if keys_to_delete:
                self.redis_client.delete(*keys_to_delete)
            logger.info("Cleared all session data")
        except Exception as e:
            logger.error(f"Error clearing data: {str(e)}")


