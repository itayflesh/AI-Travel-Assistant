import streamlit as st
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.nosql_storage import NoSQLStorage
from llm.gemini_client import GeminiClient

# Page configuration
st.set_page_config(
    page_title="Travel Assistant - Navan Assignment",
    page_icon="✈️",
    layout="centered"
)

# Initialize components
@st.cache_resource
def init_components():
    """Initialize storage and Gemini client"""
    try:
        storage = NoSQLStorage()
        gemini = GeminiClient()
        
        # Test Gemini connection
        if not gemini.test_connection():
            st.error("Failed to connect to Gemini API. Check your API key.")
            return None, None
        
        return storage, gemini
    except Exception as e:
        st.error(f"Initialization error: {str(e)}")
        return None, None

def main():
    """Main Streamlit application"""
    
    # Title and description
    st.title("✈️ Travel Assistant")
    st.markdown("*Navan Junior AI Engineer Assignment*")
    st.markdown("---")
    
    # Initialize components
    storage, gemini = init_components()
    
    if not storage or not gemini:
        st.stop()
    
    # Session management
    if "session_id" not in st.session_state:
        st.session_state.session_id = storage.create_new_session()
        st.success(f"New session created: {st.session_state.session_id[:8]}...")
    
    # Display session info
    with st.sidebar:
        st.markdown("### Session Info")
        st.text(f"Session: {st.session_state.session_id[:8]}...")
        
        # Get conversation stats
        context = storage.get_conversation(st.session_state.session_id)
        if context:
            st.text(f"Messages: {len(context['messages'])}")
            st.text(f"Created: {context['created_at'][:10]}")
        
        # New session button
        if st.button("Start New Session"):
            st.session_state.session_id = storage.create_new_session()
            st.rerun()
        
        # Show current structure (for development)
        st.markdown("### Project Structure")
        st.text("✅ core/nosql_storage.py")
        st.text("✅ llm/gemini_client.py") 
        st.text("⏳ Next: Query classification")
    
    # Chat interface
    st.markdown("### Chat with Travel Assistant")
    
    # Display conversation history
    conversation_history = storage.get_conversation_history(st.session_state.session_id)
    
    # Create chat container
    chat_container = st.container()
    
    with chat_container:
        # Display all previous messages
        for message in conversation_history:
            # User message
            with st.chat_message("user"):
                st.write(message["user"])
            
            # Assistant message
            with st.chat_message("assistant"):
                st.write(message["assistant"])
    
    # Chat input
    user_input = st.chat_input("Ask me anything about travel...")
    
    if user_input:
        # Display user message immediately
        with st.chat_message("user"):
            st.write(user_input)
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Generate response using conversation history for context
                response = gemini.generate_simple_chat_response(
                    user_input, 
                    conversation_history
                )
                
                st.write(response)
        
        # Save the conversation turn
        storage.save_message(st.session_state.session_id, user_input, response)
        
        # Rerun to update the chat display
        st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Travel Assistant Demo | Navan Junior AI Engineer Assignment<br>"
        "Basic foundation - ready for advanced features"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()