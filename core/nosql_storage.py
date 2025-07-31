import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

class NoSQLStorage:
    """
    Simple file-based NoSQL storage for conversation history and context management.
    In production, this would be Redis/MongoDB, but for assignment purposes, 
    we'll use JSON files to demonstrate the data structure.
    """
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = storage_dir
        self.conversations_dir = os.path.join(storage_dir, "conversations")
        
        # Create storage directories
        os.makedirs(self.conversations_dir, exist_ok=True)
    
    def _get_conversation_file(self, session_id: str) -> str:
        """Get the file path for a conversation session"""
        return os.path.join(self.conversations_dir, f"{session_id}.json")
    
    def create_new_session(self) -> str:
        """Create a new conversation session and return session ID"""
        session_id = str(uuid.uuid4())
        
        initial_context = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            
            # CONVERSATION HISTORY - Simple chat log
            "messages": [],
            
            # USER PROFILE - Key information for each query type
            "user_profile": {
                "destination_preferences": {},  # budget_range, travel_style, etc.
                "packing_preferences": {},      # dietary_restrictions, clothing_style, etc.
                "attractions_preferences": {}   # interests, activity_level, etc.
            },
            
            # CURRENT TRIP CONTEXT - Evolves during conversation
            "trip_context": {
                "destination": None,
                "dates": {"start": None, "end": None},
                "duration": None,
                "travelers": 1,
                "purpose": None
            },
            
            # EXTERNAL DATA CACHE - Store API responses
            "cached_data": {
                "weather": {"location": None, "data": None, "timestamp": None},
                "amadeus": {"location": None, "data": None, "timestamp": None}
            },
            
            # METADATA
            "metadata": {
                "query_count": 0,
                "last_query_type": None
            }
        }
        
        self._save_conversation(session_id, initial_context)
        return session_id
    
    def save_message(self, session_id: str, user_message: str, assistant_response: str) -> None:
        """Save a conversation turn (user message + assistant response)"""
        context = self.get_conversation(session_id)
        if not context:
            raise ValueError(f"Session {session_id} not found")
        
        # Add new message to history
        message_turn = {
            "timestamp": datetime.utcnow().isoformat(),
            "user": user_message,
            "assistant": assistant_response
        }
        
        context["messages"].append(message_turn)
        context["last_updated"] = datetime.utcnow().isoformat()
        context["metadata"]["query_count"] += 1
        
        self._save_conversation(session_id, context)
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get all messages for a session"""
        context = self.get_conversation(session_id)
        if not context:
            return []
        
        return context.get("messages", [])
    
    def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get full conversation context"""
        conversation_file = self._get_conversation_file(session_id)
        
        if not os.path.exists(conversation_file):
            return None
        
        try:
            with open(conversation_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    
    def _save_conversation(self, session_id: str, context: Dict[str, Any]) -> None:
        """Save conversation context to file"""
        conversation_file = self._get_conversation_file(session_id)
        
        with open(conversation_file, 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=2, ensure_ascii=False)
    
    def list_sessions(self) -> List[str]:
        """List all conversation sessions"""
        if not os.path.exists(self.conversations_dir):
            return []
        
        sessions = []
        for filename in os.listdir(self.conversations_dir):
            if filename.endswith('.json'):
                sessions.append(filename[:-5])  # Remove .json extension
        
        return sessions