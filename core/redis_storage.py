import os
import redis
import json
from datetime import datetime
from typing import Dict, List, Optional

class RedisStorage:
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        self.session_key = "travel_assistant_session"  # Single session as requested
    
    # SEPARATE STORAGE FOR USER QUERIES
    def save_user_query(self, query_data: dict):
        """Save user query with full classification data"""
        timestamp = datetime.utcnow().isoformat()
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
        # Also add to conversation order list
        self.redis_client.lpush(f"{self.session_key}:conversation_order", query_key)
    
    # SEPARATE STORAGE FOR ASSISTANT ANSWERS
    def save_assistant_answer(self, answer: str):
        """Save just the assistant answer"""
        timestamp = datetime.utcnow().isoformat()
        answer_key = f"{self.session_key}:assistant_answer:{timestamp}"
        
        answer_record = {
            "timestamp": timestamp,
            "assistant_answer": answer
        }
        
        self.redis_client.set(answer_key, json.dumps(answer_record))
        # Add to conversation order list
        self.redis_client.lpush(f"{self.session_key}:conversation_order", answer_key)
    
    # PRESERVE EXISTING FUNCTIONALITY
    def get_conversation_history(self) -> List[dict]:
        """Get full conversation in order"""
        conversation_keys = self.redis_client.lrange(f"{self.session_key}:conversation_order", 0, -1)
        conversation = []
        
        for key in reversed(conversation_keys):  # Reverse to get chronological order
            data = self.redis_client.get(key.decode())
            if data:
                conversation.append(json.loads(data))
        
        return conversation
    
    def save_user_profile_data(self, profile_type: str, key: str, value):
        """Save key information by type (vegetarian → dining, etc.)"""
        profile_key = f"{self.session_key}:profile:{profile_type}:{key}"
        self.redis_client.set(profile_key, json.dumps(value))
    
    def get_context_for_type(self, query_type: str) -> dict:
        """Get relevant context for specific query type"""
        context = {"profile": {}, "external_data": {}}
        
        # Get profile data for this type
        profile_keys = self.redis_client.keys(f"{self.session_key}:profile:{query_type}:*")
        for key in profile_keys:
            field_name = key.decode().split(':')[-1]
            data = self.redis_client.get(key)
            if data:
                context["profile"][field_name] = json.loads(data)
        
        # Get cached external data
        external_keys = self.redis_client.keys(f"{self.session_key}:external_data:*")
        for key in external_keys:
            data_type = key.decode().split(':')[-1]
            data = self.redis_client.get(key)
            if data:
                context["external_data"][data_type] = json.loads(data)
        
        return context
    
    def save_external_data(self, data_type: str, data: dict):
        """Save external API data with timestamp"""
        cache_key = f"{self.session_key}:external_data:{data_type}"
        cached_data = {
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "expires_in": 3600  # 1 hour default
        }
        self.redis_client.set(cache_key, json.dumps(cached_data))