import google.generativeai as genai
import os
from typing import Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Simple wrapper around Google's Gemini API.
    
    We're using Gemini 1.5 Flash.
    
    if something goes wrong,we return a friendly 
    error message instead of crashing the whole app.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Set up the Gemini client.
  
        """
        self.api_key = api_key or os.getenv('GOOGLE_AI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "You need a Google AI API key to use this. Either set the GOOGLE_AI_API_KEY "
                "environment variable or pass it directly when creating the client."
            )
        
        # Set up the API connection
        genai.configure(api_key=self.api_key)
        
        # We're using Gemini 1.5 Flash - good balance of speed and quality
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        logger.info("Gemini client ready to go")
    
    def generate_response(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Send a prompt to Gemini and get a response back.
        
        """
        try:
            # Send the prompt to Gemini
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,  # Sweet spot for travel advice - creative but not crazy
                    top_p=0.9,
                    top_k=40
                )
            )
            
            # Make sure we actually got a response
            if response.text:
                logger.info(f"Got response from Gemini: {len(response.text)} characters")
                return response.text.strip()
            else:
                logger.warning("Gemini returned an empty response")
                return "Sorry, I couldn't generate a response right now. Please try asking again."
                
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return f"I'm having some technical difficulties right now. Please try again in a moment. (Error: {str(e)})"
    
    def generate_simple_chat_response(self, user_message: str, conversation_history: list = None) -> str:
        """
        Quick way to get a chat response without building a complex prompt.
        
        """
        # Build context from recent conversation
        context = ""
        if conversation_history:
            # Only use recent messages to avoid hitting token limits
            recent_messages = conversation_history[-10:]
            for msg in recent_messages:
                context += f"User: {msg.get('user', '')}\nAssistant: {msg.get('assistant', '')}\n"
        
        # Keep the prompt simple for basic chat
        prompt = f"""You are a helpful travel assistant. Respond naturally and helpfully to the user's message.

{context}User: {user_message}
Assistant:"""
        
        return self.generate_response(prompt)
    
    def test_connection(self) -> bool:
        """
        Quick way to check if everything's working.
       
        """
        try:
            response = self.generate_response("Hello, can you respond with 'Connection successful'?")
            return "connection successful" in response.lower()
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False