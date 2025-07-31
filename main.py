import streamlit as st
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm.gemini_client import GeminiClient
from core.query_classifier import QueryClassifier

# Page configuration
st.set_page_config(
    page_title="Travel Assistant - Navan Assignment",
    page_icon="✈️",
    layout="centered"
)

# Initialize components
@st.cache_resource
def init_components():
    """Initialize storage, Gemini client, and query classifier"""
    try:
        storage = NoSQLStorage()
        gemini = GeminiClient()
        
        # Test Gemini connection
        if not gemini.test_connection():
            st.error("Failed to connect to Gemini API. Check your API key.")
            return None, None, None
        
        # Initialize query classifier
        classifier = QueryClassifier(gemini)
        
        return storage, gemini, classifier
    except Exception as e:
        st.error(f"Initialization error: {str(e)}")
        return None, None, None

def main():
    """Main Streamlit application"""
    
    # Title and description
    st.title("✈️ Travel Assistant")
    st.markdown("*Navan Junior AI Engineer Assignment*")
    st.markdown("---")
    
    # Initialize components
    storage, gemini, classifier = init_components()
    
    if not storage or not gemini or not classifier:
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
        st.text("✅ core/query_classifier.py")
        st.text("⏳ Next: Data router & APIs")

        # Raw Gemini Response (for testing)
        if hasattr(st.session_state, 'last_raw_gemini') and st.session_state.last_raw_gemini:
            st.markdown("### 🤖 Raw Gemini Response")
            with st.expander("View Raw Classification", expanded=False):
                st.code(st.session_state.last_raw_gemini, language="text")
    
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
                
                # Show classification data if available
                if "classification" in message:
                    with st.expander("🔍 Query Analysis (Debug Info)"):
                        classification = message["classification"]
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Query Type", classification["type"])
                            st.metric("Confidence", f"{classification['confidence_score']:.2f}")
                        
                        with col2:
                            st.metric("External Data", "Yes" if classification["external_data_needed"] else "No")
                            st.metric("Source", classification["primary_source"])
                        
                        # Key information extracted
                        if classification.get("key_information"):
                            key_info = classification["key_information"]
                            st.markdown("**Key Information Extracted:**")
                            for key, value in key_info.items():
                                if value:
                                    st.text(f"• {key.title()}: {value}")
                        
                        # Reasoning
                        st.markdown("**Reasoning:**")
                        st.text(classification.get("reasoning", "No reasoning provided"))
    
    # Chat input
    user_input = st.chat_input("Ask me anything about travel...")
    
    if user_input:
        # Display user message immediately
        with st.chat_message("user"):
            st.write(user_input)
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing query..."):
                
                # Step 1: Classify the query (NEW!)
                try:
                    classification_result = classifier.classify_query(user_input)

                    # Store raw Gemini response for debugging
                    if hasattr(classifier, 'last_raw_gemini_response') and classifier.last_raw_gemini_response:
                        st.session_state.last_raw_gemini = classifier.last_raw_gemini_response
                    
                    # Show classification in sidebar for immediate feedback
                    with st.sidebar:
                        st.markdown("### Last Query Analysis")
                        st.json(classification_result, expanded=False)
                    
                except Exception as e:
                    st.error(f"Classification failed: {str(e)}")
                    classification_result = {
                        "type": "unknown",
                        "external_data_needed": False,
                        "key_information": {},
                        "error": str(e)
                    }
            
            with st.spinner("Generating response..."):
                # Step 2: Generate response (keeping it simple for now)
                response = gemini.generate_simple_chat_response(
                    user_input, 
                    conversation_history
                )
                
                st.write(response)
                
                # Show classification results in expandable section
                with st.expander("🔍 Query Analysis (Debug Info)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Query Type", classification_result["type"])
                        st.metric("Confidence", f"{classification_result.get('confidence_score', 0):.2f}")
                    
                    with col2:
                        st.metric("External Data", "Yes" if classification_result.get("external_data_needed") else "No")
                        st.metric("Source", classification_result.get("primary_source", "unknown"))
                    
                    # Key information extracted
                    if classification_result.get("key_information"):
                        key_info = classification_result["key_information"]
                        st.markdown("**Key Information Extracted:**")
                        for key, value in key_info.items():
                            if value:
                                st.text(f"• {key.title()}: {value}")
                    
                    # Reasoning
                    st.markdown("**Reasoning:**")
                    st.text(classification_result.get("reasoning", "No reasoning provided"))
        
        # Save the conversation turn WITH classification data
        try:
            # Get current context to save classification data
            context = storage.get_conversation(st.session_state.session_id)
            
            # Add classification to the message
            enhanced_response = response
            
            # Save basic message
            storage.save_message(st.session_state.session_id, user_input, enhanced_response)
            
            # Add classification data to the last message
            if context and "messages" in context:
                # Get the conversation again to access the saved message
                updated_context = storage.get_conversation(st.session_state.session_id)
                if updated_context["messages"]:
                    # Add classification to the last message
                    updated_context["messages"][-1]["classification"] = classification_result
                    
                    # Save updated context
                    storage._save_conversation(st.session_state.session_id, updated_context)
            
        except Exception as e:
            st.error(f"Error saving classification data: {str(e)}")
            # Still save the basic message
            storage.save_message(st.session_state.session_id, user_input, response)
        
        # Rerun to update the chat display
        st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Travel Assistant Demo | Navan Junior AI Engineer Assignment<br>"
        "✅ Query Classification Active - ready for data routing"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()