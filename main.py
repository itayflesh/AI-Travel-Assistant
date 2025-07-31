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
from core.redis_storage import SmartRedisStorage

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
    """Initialize Smart Redis storage, Gemini client, and query classifier"""
    try:
        # Initialize Smart Redis storage
        storage = SmartRedisStorage()
        
        # Test Redis connection
        try:
            storage.redis_client.ping()
            st.success("✅ Smart Redis storage connection successful")
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
        
        # Initialize query classifier (SAME LOGIC AS BEFORE)
        classifier = QueryClassifier(gemini)
        
        return storage, gemini, classifier
        
    except Exception as e:
        st.error(f"❌ Initialization error: {str(e)}")
        return None, None, None

def extract_and_store_key_information(storage, query_type, key_information):
    """
    Extract and store key information by query type using smart storage.
    This is the improved version that uses separate storage areas.
    """
    try:
        if not key_information:
            logger.info(f"No key information extracted for {query_type}")
            return
        
        # Save key information to the appropriate type-specific storage
        storage.save_key_information_by_type(query_type, key_information)
        
        logger.info(f"Successfully stored key information for {query_type}: {list(key_information.keys())}")
        
    except Exception as e:
        logger.error(f"Error storing key information for {query_type}: {str(e)}")

def build_context_aware_prompt(storage, query_type, user_query):
    """
    Build a context-aware prompt using only relevant information for the query type.
    This demonstrates efficient prompt engineering!
    """
    try:
        # Get relevant context for this specific query type
        context = storage.get_relevant_context_for_query_type(query_type)
        
        key_info = context["key_information"]
        external_data = context["external_data"]
        
        # Build base prompt
        prompt_parts = [
            f"You are an expert travel assistant specializing in {query_type.replace('_', ' ')}.",
            f"User Query: {user_query}",
            "",
        ]
        
        # Add relevant context based on query type
        if query_type == "destination_recommendations":
            if any(key_info.get(k) for k in ["budget", "travel_style", "interests", "group_size"]):
                prompt_parts.append("USER PREFERENCES:")
                if key_info.get("budget"):
                    prompt_parts.append(f"- Budget: {key_info['budget']}")
                if key_info.get("travel_style"):
                    prompt_parts.append(f"- Travel Style: {key_info['travel_style']}")
                if key_info.get("interests"):
                    prompt_parts.append(f"- Interests: {', '.join(key_info['interests'])}")
                if key_info.get("group_size"):
                    prompt_parts.append(f"- Group Size: {key_info['group_size']}")
                if key_info.get("constraints"):
                    prompt_parts.append(f"- Constraints: {', '.join(key_info['constraints'])}")
                prompt_parts.append("")
        
        elif query_type == "packing_suggestions":
            if any(key_info.get(k) for k in ["destination", "travel_dates", "activities"]):
                prompt_parts.append("TRIP CONTEXT:")
                if key_info.get("destination"):
                    prompt_parts.append(f"- Destination: {key_info['destination']}")
                if key_info.get("travel_dates"):
                    prompt_parts.append(f"- Travel Dates: {key_info['travel_dates']}")
                if key_info.get("activities"):
                    prompt_parts.append(f"- Planned Activities: {', '.join(key_info['activities'])}")
                if key_info.get("duration"):
                    prompt_parts.append(f"- Duration: {key_info['duration']}")
                prompt_parts.append("")
            
            # Add weather data if available
            if external_data.get("weather"):
                weather = external_data["weather"]
                prompt_parts.append("CURRENT WEATHER DATA:")
                prompt_parts.append(f"- Weather: {weather}")
                prompt_parts.append("")
        
        elif query_type == "local_attractions":
            if any(key_info.get(k) for k in ["destination", "interests", "time_available"]):
                prompt_parts.append("PREFERENCES:")
                if key_info.get("destination"):
                    prompt_parts.append(f"- Destination: {key_info['destination']}")
                if key_info.get("interests"):
                    prompt_parts.append(f"- Interests: {', '.join(key_info['interests'])}")
                if key_info.get("time_available"):
                    prompt_parts.append(f"- Time Available: {key_info['time_available']}")
                if key_info.get("budget_per_activity"):
                    prompt_parts.append(f"- Budget per Activity: {key_info['budget_per_activity']}")
                prompt_parts.append("")
            
            # Add attractions data if available
            if external_data.get("attractions"):
                attractions = external_data["attractions"]
                prompt_parts.append("CURRENT ATTRACTIONS DATA:")
                prompt_parts.append(f"- Available Attractions: {attractions}")
                prompt_parts.append("")
        
        # Add missing information guidance
        missing_info = storage.get_missing_information_for_type(query_type)
        if missing_info:
            prompt_parts.append("MISSING INFORMATION (ask user if needed):")
            for field in missing_info[:3]:  # Only show top 3 missing fields
                prompt_parts.append(f"- {field.replace('_', ' ').title()}")
            prompt_parts.append("")
        
        # Final instruction
        prompt_parts.append("Provide helpful, specific advice. If important information is missing, politely ask the user for it.")
        
        final_prompt = "\n".join(prompt_parts)
        logger.info(f"Built context-aware prompt for {query_type} ({len(final_prompt)} chars)")
        
        return final_prompt
        
    except Exception as e:
        logger.error(f"Error building context-aware prompt: {str(e)}")
        # Fallback to simple prompt
        return f"You are a travel assistant. User asks: {user_query}. Please provide helpful advice."

def format_conversation_for_display(conversation_history):
    """Format conversation history for Streamlit display - SAME AS BEFORE"""
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

def main():
    """Main Streamlit application with Smart Storage"""
    
    # Title and description
    st.title("✈️ Smart Travel Assistant")
    st.markdown("*Navan Junior AI Engineer Assignment - Smart Context Management*")
    st.markdown("---")
    
    # Initialize components
    storage, gemini, classifier = init_components()
    
    if not storage or not gemini or not classifier:
        st.error("Failed to initialize components. Please check your configuration.")
        st.stop()
    
    # Enhanced sidebar with storage statistics
    with st.sidebar:
        st.markdown("### 📊 Smart Storage Stats")
        
        try:
            stats = storage.get_storage_stats()
            
            # Conversation stats
            conv_stats = stats.get("conversation", {})
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Queries", conv_stats.get("user_queries", 0))
            with col2:
                st.metric("Responses", conv_stats.get("assistant_responses", 0))
            
            # Key information completeness
            st.markdown("### 🎯 Profile Completeness")
            key_info_stats = stats.get("key_information", {})
            
            for query_type, info in key_info_stats.items():
                completeness = info.get("completeness_percent", 0)
                st.progress(completeness / 100, text=f"{query_type.replace('_', ' ').title()}: {completeness}%")
                
                # Show missing fields
                missing = info.get("missing_fields", [])
                if missing:
                    with st.expander(f"Missing for {query_type.replace('_', ' ')}", expanded=False):
                        for field in missing:
                            st.text(f"• {field.replace('_', ' ').title()}")
            
            # External data status
            st.markdown("### 🌐 External Data Cache")
            external_stats = stats.get("external_data", {})
            
            weather_status = "✅ Cached" if external_stats.get("weather_cached") else "❌ No Data"
            attractions_status = "✅ Cached" if external_stats.get("attractions_cached") else "❌ No Data"
            
            st.text(f"Weather: {weather_status}")
            st.text(f"Attractions: {attractions_status}")
            
        except Exception as e:
            st.error(f"Error loading stats: {str(e)}")
        
        # Clear conversation button
        if st.button("🗑️ Clear All Data"):
            try:
                storage.clear_all_data()
                st.success("✅ All data cleared!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error clearing data: {str(e)}")
        
        # Show supported query types
        st.markdown("### 🎯 Query Types")
        st.text("• Destination Recommendations")
        st.text("• Packing Suggestions")
        st.text("• Local Attractions & Activities")
        
        # Show current architecture
        st.markdown("### 🏗️ Smart Architecture")
        st.text("✅ Type-specific key info storage")
        st.text("✅ Context-aware prompt building")
        st.text("✅ External data caching")
        st.text("✅ Missing info detection")

        # Raw Gemini Response (debugging)
        if hasattr(st.session_state, 'last_raw_gemini') and st.session_state.last_raw_gemini:
            st.markdown("### 🤖 Raw Gemini Response")
            with st.expander("View Raw Classification", expanded=False):
                st.json(st.session_state.last_raw_gemini)
    
    # Main chat interface
    st.markdown("### 💬 Chat with Smart Travel Assistant")
    
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
                            with st.expander("🔍 Smart Query Analysis", expanded=False):
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
            
            # Step 1: Classify the query (SAME LOGIC AS BEFORE)
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
            
            # Step 2: Generate context-aware response
            with st.spinner("🤖 Generating smart response..."):
                try:
                    # Build context-aware prompt using smart storage
                    context_prompt = build_context_aware_prompt(
                        storage, 
                        classification_result["type"], 
                        user_input
                    )
                    
                    # Generate response using the context-aware prompt
                    response = gemini.generate_response(context_prompt, max_tokens=800)
                    
                    if not response or len(response.strip()) == 0:
                        response = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
                    
                except Exception as e:
                    st.error(f"❌ Response generation failed: {str(e)}")
                    response = f"I'm experiencing technical difficulties generating a response. Please try again. (Error: {str(e)})"
            
            # Display the response
            st.write(response)
            
            # Show classification results and context used
            if classification_result:
                with st.expander("🔍 Smart Query Analysis", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Query Type", classification_result["type"])
                        st.metric("Confidence", f"{classification_result.get('confidence_score', 0):.2f}")
                    
                    with col2:
                        st.metric("External Data", "Yes" if classification_result.get("external_data_needed") else "No")
                        st.metric("Source", classification_result.get("primary_source", "unknown"))
                    
                    # Show context used for this response
                    try:
                        context = storage.get_relevant_context_for_query_type(classification_result["type"])
                        st.markdown("**Context Used in Response:**")
                        
                        key_info_used = []
                        for key, value in context["key_information"].items():
                            if value and key != "other":
                                if isinstance(value, list) and len(value) > 0:
                                    key_info_used.append(f"{key.replace('_', ' ').title()}: {', '.join(value)}")
                                elif isinstance(value, str) and value.strip():
                                    key_info_used.append(f"{key.replace('_', ' ').title()}: {value}")
                        
                        if key_info_used:
                            for info in key_info_used:
                                st.text(f"• {info}")
                        else:
                            st.text("• No previous context available")
                        
                        # Show external data used
                        if context["external_data"]:
                            st.markdown("**External Data Used:**")
                            for data_type, data in context["external_data"].items():
                                st.text(f"• {data_type.title()}: Available")
                        
                    except Exception as e:
                        st.text(f"Error showing context: {str(e)}")
                    
                    # Key information extracted from this query
                    if classification_result.get("key_information"):
                        key_info = classification_result["key_information"]
                        st.markdown("**New Information Extracted:**")
                        for key, value in key_info.items():
                            if value:
                                if isinstance(value, list):
                                    st.text(f"• {key.title()}: {', '.join(value)}")
                                else:
                                    st.text(f"• {key.title()}: {value}")
                    
                    # Missing information that could improve responses
                    try:
                        missing_info = storage.get_missing_information_for_type(classification_result["type"])
                        if missing_info:
                            st.markdown("**Missing Information (for better responses):**")
                            for field in missing_info[:3]:  # Show only top 3
                                st.text(f"• {field.replace('_', ' ').title()}")
                    except Exception as e:
                        pass
                    
                    # Reasoning
                    st.markdown("**Classification Reasoning:**")
                    st.text(classification_result.get("reasoning", "No reasoning provided"))
                    
                    if classification_result.get("fallback_used"):
                        st.warning("⚠️ Fallback classification used due to LLM error")
        
        # Step 3: Save to Smart Storage
        if classification_result and response:
            try:
                # Extract and store key information by type (NEW SMART METHOD)
                extract_and_store_key_information(
                    storage, 
                    classification_result["type"], 
                    classification_result.get("key_information", {})
                )
                
                # Save user query with full classification data (SAME AS BEFORE)
                query_data = {
                    "query": user_input,
                    **classification_result
                }
                storage.save_user_query(query_data)
                
                # Save assistant answer (SAME AS BEFORE)
                storage.save_assistant_answer(response)
                
                logger.info(f"Successfully saved to smart storage - Type: {classification_result['type']}")
                
            except Exception as e:
                st.error(f"❌ Error saving to smart storage: {str(e)}")
                logger.error(f"Smart storage save error: {str(e)}")
        
        # Rerun to update the chat display and sidebar stats
        st.rerun()
    
    # Footer with enhanced status
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Smart Travel Assistant | Navan Junior AI Engineer Assignment<br>"
        "✅ Smart Context Management | ✅ Type-Specific Storage | ✅ Context-Aware Prompts | ✅ Missing Info Detection"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()