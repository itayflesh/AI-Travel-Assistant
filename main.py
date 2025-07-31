import streamlit as st
import os
import sys
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Add project root to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm.gemini_client import GeminiClient
from core.query_classifier import QueryClassifier
from core.redis_storage import RedisStorage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Travel Assistant - Navan Assignment",
    page_icon="✈️",
    layout="centered"
)

# Initialize components with proper error handling
@st.cache_resource
def init_components():
    """Initialize Redis storage, Gemini client, and query classifier"""
    try:
        # Initialize Redis storage
        storage = RedisStorage()
        
        # Test Redis connection
        try:
            storage.redis_client.ping()
            st.success("✅ Redis connection successful")
        except Exception as e:
            st.error(f"❌ Redis connection failed: {str(e)}")
            st.error("Make sure Redis is running and REDIS_URL is configured correctly")
            return None, None, None
        
        # Initialize Gemini client
        gemini = GeminiClient()
        
        # Test Gemini connection
        if not gemini.test_connection():
            st.error("❌ Failed to connect to Gemini API. Check your GOOGLE_AI_API_KEY.")
            return None, None, None
        else:
            st.success("✅ Gemini API connection successful")
        
        # Initialize query classifier
        classifier = QueryClassifier(gemini)
        
        return storage, gemini, classifier
        
    except Exception as e:
        st.error(f"❌ Initialization error: {str(e)}")
        return None, None, None

def store_key_information(storage, query_type, key_information):
    """Store key information by type for future use"""
    try:
        if not key_information:
            return
            
        # Use ORIGINAL query types, not mapped ones
        profile_type = query_type  # Keep original: destination_recommendations, etc.
        
        # Store each piece of key information
        for key, value in key_information.items():
            if value:  # Only store non-empty values
                if isinstance(value, list) and len(value) > 0:
                    storage.save_user_profile_data(profile_type, key, value)
                elif isinstance(value, str) and value.strip():
                    storage.save_user_profile_data(profile_type, key, value.strip())
                    
        logger.info(f"Stored key information for {profile_type}: {key_information}")
        
    except Exception as e:
        logger.error(f"Error storing key information: {str(e)}")

def format_conversation_for_display(conversation_history):
    """Format Redis conversation history for Streamlit display"""
    formatted_messages = []
    
    for message in conversation_history:
        if "user_query" in message:
            formatted_messages.append({
                "type": "user",
                "content": message["user_query"],
                "timestamp": message.get("timestamp"),
                "classification": message.get("classification")
            })
        elif "assistant_answer" in message:
            formatted_messages.append({
                "type": "assistant", 
                "content": message["assistant_answer"],
                "timestamp": message.get("timestamp")
            })
    
    return formatted_messages

def format_conversation_for_gemini(conversation_history):
    """Format Redis conversation history for Gemini API"""
    gemini_history = []
    current_turn = {}
    
    for message in conversation_history:
        if "user_query" in message:
            current_turn = {"user": message["user_query"], "assistant": ""}
        elif "assistant_answer" in message and current_turn:
            current_turn["assistant"] = message["assistant_answer"]
            gemini_history.append(current_turn)
            current_turn = {}
    
    return gemini_history

def main():
    """Main Streamlit application"""
    
    # Title and description
    st.title("✈️ Travel Assistant")
    st.markdown("*Navan Junior AI Engineer Assignment - Redis Storage Demo*")
    st.markdown("---")
    
    # Initialize components
    storage, gemini, classifier = init_components()
    
    if not storage or not gemini or not classifier:
        st.error("Failed to initialize components. Please check your configuration.")
        st.stop()
    
    # Sidebar with session info and controls
    with st.sidebar:
        st.markdown("### 📊 Session Info")
        st.text("Single Redis session mode")
        
        # Get conversation stats
        try:
            history = storage.get_conversation_history()
            user_queries = sum(1 for msg in history if "user_query" in msg)
            assistant_responses = sum(1 for msg in history if "assistant_answer" in msg)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("User Queries", user_queries)
            with col2:
                st.metric("Responses", assistant_responses)
                
        except Exception as e:
            st.error(f"Error getting stats: {str(e)}")
        
        # Clear conversation button
        if st.button("🗑️ Clear Conversation"):
            try:
                # Clear Redis data for this session
                storage.redis_client.delete(f"{storage.session_key}:conversation_order")
                # Clear all user query and assistant answer keys
                keys_to_delete = storage.redis_client.keys(f"{storage.session_key}:*")
                if keys_to_delete:
                    storage.redis_client.delete(*keys_to_delete)
                st.success("✅ Conversation cleared!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error clearing conversation: {str(e)}")
        
        # Show current structure (for development)
        st.markdown("### 🏗️ Project Status")
        st.text("✅ core/redis_storage.py")
        st.text("✅ llm/gemini_client.py") 
        st.text("✅ core/query_classifier.py")
        st.text("⏳ Next: External APIs")

        # Show supported query types
        st.markdown("### 🎯 Supported Query Types")
        st.text("• Destination Recommendations")
        st.text("• Packing Suggestions")
        st.text("• Local Attractions & Activities")

        # Raw Gemini Response (for debugging)
        if hasattr(st.session_state, 'last_raw_gemini') and st.session_state.last_raw_gemini:
            st.markdown("### 🤖 Raw Gemini Response")
            with st.expander("View Raw Classification", expanded=False):
                st.json(st.session_state.last_raw_gemini)
    
    # Main chat interface
    st.markdown("### 💬 Chat with Travel Assistant")
    
    # Get and display conversation history
    try:
        conversation_history = storage.get_conversation_history()
        formatted_messages = format_conversation_for_display(conversation_history)
        
        # Create chat container
        chat_container = st.container()
        
        with chat_container:
            # Display all previous messages
            for message in formatted_messages:
                if message["type"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                        
                        # Show classification data if available
                        if message.get("classification"):
                            with st.expander("🔍 Query Analysis", expanded=False):
                                classification = message["classification"]
                                
                                # Main metrics
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Query Type", classification.get("type", "unknown"))
                                    st.metric("Confidence", f"{classification.get('confidence_score', 0):.2f}")
                                
                                with col2:
                                    st.metric("External Data", "Yes" if classification.get("external_data_needed") else "No")
                                    st.metric("Source", classification.get("primary_source", "unknown"))
                                
                                # Key information extracted
                                if classification.get("key_information"):
                                    key_info = classification["key_information"]
                                    st.markdown("**Key Information Extracted:**")
                                    for key, value in key_info.items():
                                        if value:
                                            if isinstance(value, list):
                                                st.text(f"• {key.title()}: {', '.join(value)}")
                                            else:
                                                st.text(f"• {key.title()}: {value}")
                                
                                # Reasoning
                                st.markdown("**Classification Reasoning:**")
                                st.text(classification.get("reasoning", "No reasoning provided"))
                                
                                # External data reasoning
                                if classification.get("external_data_reason"):
                                    st.markdown("**External Data Reasoning:**")
                                    st.text(classification["external_data_reason"])
                        
                elif message["type"] == "assistant":
                    with st.chat_message("assistant"):
                        st.write(message["content"])
        
    except Exception as e:
        st.error(f"❌ Error loading conversation history: {str(e)}")
        formatted_messages = []
        conversation_history = []
    
    # Chat input
    user_input = st.chat_input("Ask me anything about travel planning...")
    
    if user_input:
        # Display user message immediately
        with st.chat_message("user"):
            st.write(user_input)
        
        # Process and respond
        with st.chat_message("assistant"):
            classification_result = None
            response = None
            
            # Step 1: Classify the query
            with st.spinner("🔍 Analyzing your query..."):
                try:
                    classification_result = classifier.classify_query(user_input)

                    # Store raw Gemini response for debugging
                    if hasattr(classifier, 'last_raw_gemini_response') and classifier.last_raw_gemini_response:
                        st.session_state.last_raw_gemini = classifier.last_raw_gemini_response
                    
                    # Show real-time classification in sidebar
                    with st.sidebar:
                        st.markdown("### 🎯 Last Query Analysis")
                        st.json({
                            "type": classification_result["type"],
                            "external_data_needed": classification_result["external_data_needed"],
                            "confidence": classification_result.get("confidence_score", 0)
                        })
                    
                except Exception as e:
                    st.error(f"❌ Classification failed: {str(e)}")
                    classification_result = {
                        "type": "destination_recommendations",  # Safe fallback
                        "external_data_needed": False,
                        "external_data_type": "none",
                        "key_information": {},
                        "confidence_score": 0.1,
                        "primary_source": "fallback",
                        "reasoning": f"Classification error - using fallback: {str(e)}",
                        "fallback_used": True,
                        "error": str(e)
                    }
            
            # Step 2: Generate response
            with st.spinner("🤖 Generating response..."):
                try:
                    # Get relevant context for this query type
                    context = storage.get_context_for_type(classification_result["type"])
                    
                    # Format conversation history for Gemini
                    gemini_history = format_conversation_for_gemini(conversation_history)
                    
                    # Generate response with context
                    response = gemini.generate_simple_chat_response(
                        user_input, 
                        gemini_history
                    )
                    
                    if not response or len(response.strip()) == 0:
                        response = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
                    
                except Exception as e:
                    st.error(f"❌ Response generation failed: {str(e)}")
                    response = f"I'm experiencing technical difficulties generating a response. Please try again. (Error: {str(e)})"
            
            # Display the response
            st.write(response)
            
            # Show classification results in expandable section
            if classification_result:
                with st.expander("🔍 Query Analysis", expanded=False):
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
                                if isinstance(value, list):
                                    st.text(f"• {key.title()}: {', '.join(value)}")
                                else:
                                    st.text(f"• {key.title()}: {value}")
                    
                    # Reasoning
                    st.markdown("**Classification Reasoning:**")
                    st.text(classification_result.get("reasoning", "No reasoning provided"))
                    
                    if classification_result.get("fallback_used"):
                        st.warning("⚠️ Fallback classification used due to LLM error")
        
        # Step 3: Save to Redis
        if classification_result and response:
            try:
                # Store key information by type (as required)
                store_key_information(
                    storage, 
                    classification_result["type"], 
                    classification_result.get("key_information", {})
                )
                
                # Save user query with full classification data
                query_data = {
                    "query": user_input,
                    **classification_result
                }
                storage.save_user_query(query_data)
                
                # Save assistant answer separately
                storage.save_assistant_answer(response)
                
                logger.info(f"Successfully saved conversation turn - Type: {classification_result['type']}")
                
            except Exception as e:
                st.error(f"❌ Error saving conversation: {str(e)}")
                logger.error(f"Save error: {str(e)}")
        
        # Rerun to update the chat display
        st.rerun()
    
    # Footer with status
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Travel Assistant Demo | Navan Junior AI Engineer Assignment<br>"
        "✅ Redis Storage Active | ✅ Query Classification | ✅ Key Information Extraction"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()