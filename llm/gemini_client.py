import google.generativeai as genai
import os
from typing import Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Simple Gemini API client for generating responses.
    Uses Gemini 1.5 Flash as requested.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client
        
        Args:
            api_key: Google AI API key. If None, will try to get from environment variable.
        """
        self.api_key = api_key or os.getenv('GOOGLE_AI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "Google AI API key is required. Set GOOGLE_AI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Configure the API
        genai.configure(api_key=self.api_key)
        
        # Initialize the model - using Gemini 1.5 Flash as requested
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        logger.info("Gemini client initialized successfully")
    
    def generate_response(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Generate a response using Gemini
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens in response (for cost control)
            
        Returns:
            Generated response text
        """
        try:
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,  # Balanced creativity vs consistency
                    top_p=0.9,
                    top_k=40
                )
            )
            
            # Extract text from response
            if response.text:
                logger.info(f"Generated response: {len(response.text)} characters")
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return "I apologize, but I couldn't generate a response right now. Please try again."
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"I'm experiencing technical difficulties. Please try again later. (Error: {str(e)})"
    
    def generate_simple_chat_response(self, user_message: str, conversation_history: list = None) -> str:
        """
        Generate a simple chat response for basic conversation
        
        Args:
            user_message: Current user message
            conversation_history: Previous conversation turns (optional)
            
        Returns:
            Chat response
        """
        # Build context from conversation history
        context = ""
        if conversation_history:
            # Only include last few messages to avoid token limits
            recent_messages = conversation_history[-10:]  # Last 10 turns
            for msg in recent_messages:
                context += f"User: {msg.get('user', '')}\nAssistant: {msg.get('assistant', '')}\n"
        
        # Simple chat prompt
        prompt = f"""You are a helpful travel assistant. Respond naturally and helpfully to the user's message.

{context}User: {user_message}
Assistant:"""
        
        return self.generate_response(prompt)
    
    def test_connection(self) -> bool:
        """
        Test if the Gemini API connection is working
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.generate_response("Hello, can you respond with 'Connection successful'?")
            return "connection successful" in response.lower()
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False