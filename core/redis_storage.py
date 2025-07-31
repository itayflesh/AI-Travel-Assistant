import os
import redis
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartRedisStorage:
    """
    Smart Redis storage with separated data types for efficient context management.
    Demonstrates production-ready AI engineering skills for Navan assignment.
    """
    
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        self.session_key = "travel_assistant_session"
        
        # Define key information fields for each query type
        self.key_info_schemas = {
            "destination_recommendations": {
                "budget": None,
                "travel_style": None,  # budget, luxury, adventure, cultural, relaxation
                "group_size": None,
                "interests": [],  # history, food, nature, nightlife, culture, adventure
                "travel_dates": None,
                "duration": None,
                "constraints": [],  # no_flights, visa_free, warm_weather, etc.
                "previous_destinations": [],
                "other": {}
            },
            "packing_suggestions": {
                "destination": None,
                "travel_dates": None,
                "duration": None,
                "activities": [],  # sightseeing, hiking, business, beach, nightlife
                "climate_preference": None,  # hot, mild, cold, any
                "luggage_type": None,  # carry_on, checked, backpack
                "special_needs": [],  # formal_wear, sports_gear, medical_items
                "laundry_availability": None,  # yes, no, limited
                "other": {}
            },
            "local_attractions": {
                "destination": None,
                "interests": [],  # museums, temples, food, shopping, nature, nightlife
                "time_available": None,  # 1 day, 3 days, 1 week, etc.
                "mobility": None,  # walking, driving, public_transport, limited_mobility
                "budget_per_activity": None,
                "group_type": None,  # solo, couple, family, friends
                "age_group": None,  # young, adult, senior, mixed
                "accessibility_needs": [],
                "other": {}
            }
        }
    
    def save_user_query(self, query_data: Dict[str, Any]):
        """Save user query with classification data - SAME AS BEFORE"""
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
        """Save assistant answer - SAME AS BEFORE"""
        timestamp = datetime.now(timezone.utc).isoformat()
        answer_key = f"{self.session_key}:assistant_answer:{timestamp}"
        
        answer_record = {
            "timestamp": timestamp,
            "assistant_answer": answer
        }
        
        self.redis_client.set(answer_key, json.dumps(answer_record))
        self.redis_client.lpush(f"{self.session_key}:conversation_order", answer_key)
        logger.info("Saved assistant answer")
    
    def save_key_information_by_type(self, query_type: str, key_information: Dict[str, Any]):
        """
        Save key information by query type in separate storage areas.
        Merges with existing data to build user profile over time.
        """
        if query_type not in self.key_info_schemas:
            logger.warning(f"Unknown query type: {query_type}")
            return
        
        if not key_information:
            logger.info(f"No key information to save for {query_type}")
            return
        
        storage_key = f"{self.session_key}:{query_type}_key_info"
        
        try:
            # Get existing data
            existing_data = self.get_key_information_by_type(query_type)
            
            # Merge with new data intelligently
            updated_data = self._merge_key_information(existing_data, key_information)
            
            # Save updated data
            self.redis_client.set(storage_key, json.dumps(updated_data))
            logger.info(f"Updated {query_type} key information: {list(key_information.keys())}")
            
        except Exception as e:
            logger.error(f"Error saving key information for {query_type}: {str(e)}")
    
    def get_key_information_by_type(self, query_type: str) -> Dict[str, Any]:
        """Get key information for specific query type"""
        if query_type not in self.key_info_schemas:
            return {}
        
        storage_key = f"{self.session_key}:{query_type}_key_info"
        
        try:
            data = self.redis_client.get(storage_key)
            if data:
                return json.loads(data)
            else:
                # Return empty schema if no data exists
                return self.key_info_schemas[query_type].copy()
                
        except Exception as e:
            logger.error(f"Error getting key information for {query_type}: {str(e)}")
            return self.key_info_schemas[query_type].copy()
    
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
    
    def get_relevant_context_for_query_type(self, query_type: str) -> Dict[str, Any]:
        """
        Get only relevant context for specific query type.
        This is the key method for efficient prompt engineering!
        """
        context = {
            "key_information": {},
            "external_data": {},
            "query_type": query_type
        }
        
        # Always get key information for this query type
        context["key_information"] = self.get_key_information_by_type(query_type)
        
        # Get relevant external data based on query type
        if query_type == "packing_suggestions":
            weather_data = self.get_external_data("weather_external_data")
            if weather_data:
                context["external_data"]["weather"] = weather_data
                
        elif query_type == "local_attractions":
            attractions_data = self.get_external_data("attractions_external_data")
            if attractions_data:
                context["external_data"]["attractions"] = attractions_data
        
        # destination_recommendations doesn't need external data usually
        
        logger.info(f"Retrieved context for {query_type}: {list(context['key_information'].keys())}")
        return context
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get full conversation history - SAME AS BEFORE"""
        conversation_keys = self.redis_client.lrange(f"{self.session_key}:conversation_order", 0, -1)
        conversation = []
        
        for key in reversed(conversation_keys):
            data = self.redis_client.get(key.decode())
            if data:
                conversation.append(json.loads(data))
        
        return conversation
    
    def _merge_key_information(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Intelligently merge key information"""
        result = existing.copy()
        
        for key, value in new.items():
            if value is None or value == "":
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
    
    def get_missing_information_for_type(self, query_type: str) -> List[str]:
        """
        Get list of missing key information for a query type.
        This helps prompt engineering to ask for missing data!
        """
        if query_type not in self.key_info_schemas:
            return []
        
        current_data = self.get_key_information_by_type(query_type)
        schema = self.key_info_schemas[query_type]
        missing = []
        
        for field, default_value in schema.items():
            if field == "other":
                continue  # Skip "other" field
                
            current_value = current_data.get(field)
            
            if isinstance(default_value, list):
                if not current_value or len(current_value) == 0:
                    missing.append(field)
            else:
                if not current_value:
                    missing.append(field)
        
        return missing
    
    def clear_all_data(self):
        """Clear all conversation and profile data"""
        try:
            keys_to_delete = self.redis_client.keys(f"{self.session_key}:*")
            if keys_to_delete:
                self.redis_client.delete(*keys_to_delete)
            logger.info("Cleared all session data")
        except Exception as e:
            logger.error(f"Error clearing data: {str(e)}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about stored data"""
        try:
            history = self.get_conversation_history()
            user_queries = sum(1 for msg in history if "user_query" in msg)
            assistant_responses = sum(1 for msg in history if "assistant_answer" in msg)
            
            # Check key information completeness
            key_info_status = {}
            for query_type in self.key_info_schemas.keys():
                missing = self.get_missing_information_for_type(query_type)
                total_fields = len(self.key_info_schemas[query_type]) - 1  # Exclude "other"
                filled_fields = total_fields - len(missing)
                completeness = (filled_fields / total_fields) * 100 if total_fields > 0 else 0
                
                key_info_status[query_type] = {
                    "completeness_percent": round(completeness, 1),
                    "missing_fields": missing,
                    "filled_fields": filled_fields,
                    "total_fields": total_fields
                }
            
            return {
                "conversation": {
                    "user_queries": user_queries,
                    "assistant_responses": assistant_responses,
                    "total_turns": user_queries + assistant_responses
                },
                "key_information": key_info_status,
                "external_data": {
                    "weather_cached": bool(self.get_external_data("weather_external_data")),
                    "attractions_cached": bool(self.get_external_data("attractions_external_data"))
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {"error": str(e)}