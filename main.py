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
from core.redis_storage import GlobalContextStorage  

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Smart Travel Assistant - Navan Assignment",
    page_icon="✈️",
    layout="centered"
)

# Initialize components with proper error handling
@st.cache_resource
def init_components():
    """Initialize Global Context Storage, Gemini client, and query classifier"""
    try:
        # Initialize Global Context Storage (NEW!)
        storage = GlobalContextStorage()
        
        # Test Redis connection
        try:
            storage.redis_client.ping()
            st.success("✅ Global Context Storage connection successful")
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

def build_global_context_aware_prompt(storage, query_type, user_query):
    """
    Build a context-aware prompt using global + type-specific context.
    This is the enhanced version that handles shared "super" key information!
    """
    try:
        # Get complete context (global + type-specific + external data)
        context = storage.get_complete_context_for_query_type(query_type)
        
        global_info = context["global"]
        type_specific_info = context["type_specific"]
        external_data = context["external_data"]
        
        # Build base prompt
        prompt_parts = [
            f"You are an expert travel assistant specializing in {query_type.replace('_', ' ')}.",
            f"User Query: {user_query}",
            "",
        ]
        
        # Add GLOBAL context (shared across all query types)
        global_context_added = False
        if any(global_info.get(k) for k in ["destination", "travel_dates", "duration", "budget", "group_size", "interests"]):
            prompt_parts.append("TRAVELER PROFILE (from previous conversations):")
            global_context_added = True
            
            if global_info.get("destination"):
                prompt_parts.append(f"- Destination: {global_info['destination']}")
            if global_info.get("travel_dates"):
                prompt_parts.append(f"- Travel Dates: {global_info['travel_dates']}")
            if global_info.get("duration"):
                prompt_parts.append(f"- Trip Duration: {global_info['duration']}")
            if global_info.get("budget"):
                prompt_parts.append(f"- Budget: {global_info['budget']}")
            if global_info.get("group_size"):
                prompt_parts.append(f"- Group Size: {global_info['group_size']}")
            if global_info.get("interests") and len(global_info['interests']) > 0:
                prompt_parts.append(f"- Interests: {', '.join(global_info['interests'])}")
            
            prompt_parts.append("")
        
        # Add TYPE-SPECIFIC context based on query type
        if query_type == "destination_recommendations":
            if any(type_specific_info.get(k) for k in ["travel_style", "constraints", "climate_preference"]):
                prompt_parts.append("DESTINATION PREFERENCES:")
                if type_specific_info.get("travel_style"):
                    prompt_parts.append(f"- Travel Style: {type_specific_info['travel_style']}")
                if type_specific_info.get("constraints") and len(type_specific_info['constraints']) > 0:
                    prompt_parts.append(f"- Constraints: {', '.join(type_specific_info['constraints'])}")
                if type_specific_info.get("climate_preference"):
                    prompt_parts.append(f"- Climate Preference: {type_specific_info['climate_preference']}")
                prompt_parts.append("")
        
        elif query_type == "packing_suggestions":
            if any(type_specific_info.get(k) for k in ["activities", "luggage_type", "special_needs", "laundry_availability"]):
                prompt_parts.append("PACKING PREFERENCES:")
                if type_specific_info.get("activities") and len(type_specific_info['activities']) > 0:
                    prompt_parts.append(f"- Planned Activities: {', '.join(type_specific_info['activities'])}")
                if type_specific_info.get("luggage_type"):
                    prompt_parts.append(f"- Luggage Type: {type_specific_info['luggage_type']}")
                if type_specific_info.get("special_needs") and len(type_specific_info['special_needs']) > 0:
                    prompt_parts.append(f"- Special Needs: {', '.join(type_specific_info['special_needs'])}")
                if type_specific_info.get("laundry_availability"):
                    prompt_parts.append(f"- Laundry Availability: {type_specific_info['laundry_availability']}")
                prompt_parts.append("")
            
            # Add weather data if available
            if external_data.get("weather"):
                weather = external_data["weather"]
                prompt_parts.append("CURRENT WEATHER DATA:")
                prompt_parts.append(f"- Weather Forecast: {weather}")
                prompt_parts.append("")
        
        elif query_type == "local_attractions":
            if any(type_specific_info.get(k) for k in ["time_available", "mobility", "budget_per_activity", "accessibility_needs"]):
                prompt_parts.append("ATTRACTION PREFERENCES:")
                if type_specific_info.get("time_available"):
                    prompt_parts.append(f"- Time Available: {type_specific_info['time_available']}")
                if type_specific_info.get("mobility"):
                    prompt_parts.append(f"- Mobility: {type_specific_info['mobility']}")
                if type_specific_info.get("budget_per_activity"):
                    prompt_parts.append(f"- Budget per Activity: {type_specific_info['budget_per_activity']}")
                if type_specific_info.get("accessibility_needs") and len(type_specific_info['accessibility_needs']) > 0:
                    prompt_parts.append(f"- Accessibility Needs: {', '.join(type_specific_info['accessibility_needs'])}")
                prompt_parts.append("")
            
            # Add attractions data if available
            if external_data.get("attractions"):
                attractions = external_data["attractions"]
                prompt_parts.append("CURRENT ATTRACTIONS DATA:")
                prompt_parts.append(f"- Available Attractions: {attractions}")
                prompt_parts.append("")
        
        # Add missing information guidance (SMART!)
        missing_info = storage.get_missing_information_for_type(query_type)
        
        important_missing = []
        if missing_info.get("global"):
            important_missing.extend(missing_info["global"][:2])  # Top 2 global missing
        if missing_info.get("type_specific"):
            important_missing.extend(missing_info["type_specific"][:2])  # Top 2 type-specific missing
        
        if important_missing:
            prompt_parts.append("IMPORTANT MISSING INFORMATION (politely ask user if relevant):")
            for field in important_missing:
                prompt_parts.append(f"- {field.replace('_', ' ').title()}")
            prompt_parts.append("")
        
        # Final instruction with context awareness
        if global_context_added:
            prompt_parts.append("Provide personalized advice based on their traveler profile. If important information is missing, politely ask for it to give better recommendations.")
        else:
            prompt_parts.append("Provide helpful travel advice. Ask for key information to personalize recommendations.")
        
        final_prompt = "\n".join(prompt_parts)
        logger.info(f"Built global context-aware prompt for {query_type} ({len(final_prompt)} chars)")
        
        return final_prompt
        
    except Exception as e:
        logger.error(f"Error building global context-aware prompt: {str(e)}")
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
    """Main Streamlit application with Global Context Management"""
    
    # Title and description
    st.title("🧠 Global Context Travel Assistant")
    st.markdown("*Navan Junior AI Engineer Assignment - Global + Type-Specific Context Management*")
    st.markdown("---")
    
    # Initialize components
    storage, gemini, classifier = init_components()
    
    if not storage or not gemini or not classifier:
        st.error("Failed to initialize components. Please check your configuration.")
        st.stop()
    
    # Enhanced sidebar with global context statistics
    with st.sidebar:
        st.markdown("### 🌍 Global Context Stats")
        
        try:
            stats = storage.get_storage_stats()
            
            # Global context completeness
            global_stats = stats.get("global_context", {})
            global_completeness = global_stats.get("completeness_percent", 0)
            
            st.progress(global_completeness / 100, text=f"Global Profile: {global_completeness}%")
            
            # Show current global data
            current_global = global_stats.get("current_data", {})
            if current_global:
                st.markdown("**Current Global Context:**")
                for key, value in current_global.items():
                    if isinstance(value, list):
                        st.text(f"• {key.title()}: {', '.join(value)}")
                    else:
                        st.text(f"• {key.title()}: {value}")
            else:
                st.text("No global context yet")
            
            st.markdown("### 🎯 Type-Specific Completeness")
            
            # Type-specific completeness
            type_stats = stats.get("type_specific", {})
            for query_type, info in type_stats.items():
                completeness = info.get("completeness_percent", 0)
                st.progress(completeness / 100, text=f"{query_type.replace('_', ' ').title()}: {completeness}%")
            
            # Conversation stats
            st.markdown("### 💬 Conversation Stats")
            # Get conversation history for stats
            history = storage.get_conversation_history()
            user_queries = sum(1 for msg in history if "user_query" in msg)
            assistant_responses = sum(1 for msg in history if "assistant_answer" in msg)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Queries", user_queries)
            with col2:
                st.metric("Responses", assistant_responses)
            
            # External data status
            st.markdown("### 🌐 External Data")
            external_stats = stats.get("external_data", {})
            
            weather_status = "✅" if external_stats.get("weather_cached") else "❌"
            attractions_status = "✅" if external_stats.get("attractions_cached") else "❌"
            
            st.text(f"Weather: {weather_status} | Attractions: {attractions_status}")
            
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
        
        # Show architecture info
        st.markdown("### 🏗️ Smart Architecture")
        st.text("✅ Global context sharing")
        st.text("✅ Type-specific contexts")
        st.text("✅ Missing info detection")
        st.text("✅ Context-aware prompts")

        # Raw Gemini Response (debugging)
        if hasattr(st.session_state, 'last_raw_gemini') and st.session_state.last_raw_gemini:
            st.markdown("### 🤖 Raw Gemini Response")
            with st.expander("View Raw Classification", expanded=False):
                st.json(st.session_state.last_raw_gemini)
    
    # Main chat interface
    st.markdown("### 💬 Chat with Global Context Assistant")
    
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
                                
                                # Show how information was categorized
                                if classification.get("key_information"):
                                    key_info = classification["key_information"]
                                    
                                    # Separate global from type-specific for display
                                    global_fields = {"destination", "travel_dates", "duration", "budget", "group_size", "interests"}
                                    
                                    global_info = {k: v for k, v in key_info.items() if k in global_fields and v}
                                    type_specific_info = {k: v for k, v in key_info.items() if k not in global_fields and v}
                                    
                                    if global_info:
                                        st.markdown("**Global Information Extracted:**")
                                        for key, value in global_info.items():
                                            if isinstance(value, list):
                                                st.text(f"🌍 {key.title()}: {', '.join(value)}")
                                            else:
                                                st.text(f"🌍 {key.title()}: {value}")
                                    
                                    if type_specific_info:
                                        st.markdown("**Type-Specific Information Extracted:**")
                                        for key, value in type_specific_info.items():
                                            if isinstance(value, list):
                                                st.text(f"🎯 {key.title()}: {', '.join(value)}")
                                            else:
                                                st.text(f"🎯 {key.title()}: {value}")
                                
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
            
            # Step 2: Generate global context-aware response
            with st.spinner("🧠 Generating globally context-aware response..."):
                try:
                    # Build global context-aware prompt
                    context_prompt = build_global_context_aware_prompt(
                        storage, 
                        classification_result["type"], 
                        user_input
                    )
                    
                    # Generate response using the enhanced context-aware prompt
                    response = gemini.generate_response(context_prompt, max_tokens=800)
                    
                    if not response or len(response.strip()) == 0:
                        response = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
                    
                except Exception as e:
                    st.error(f"❌ Response generation failed: {str(e)}")
                    response = f"I'm experiencing technical difficulties generating a response. Please try again. (Error: {str(e)})"
            
            # Display the response
            st.write(response)
            
            # Show enhanced context analysis
            if classification_result:
                with st.expander("🧠 Global Context Analysis", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Query Type", classification_result["type"])
                        st.metric("Confidence", f"{classification_result.get('confidence_score', 0):.2f}")
                    
                    with col2:
                        st.metric("External Data", "Yes" if classification_result.get("external_data_needed") else "No")
                        st.metric("Source", classification_result.get("primary_source", "unknown"))
                    
                    # Show complete context used for this response
                    try:
                        context = storage.get_complete_context_for_query_type(classification_result["type"])
                        
                        # Global context used
                        global_context_used = []
                        for key, value in context["global"].items():
                            if value:
                                if isinstance(value, list) and len(value) > 0:
                                    global_context_used.append(f"{key.replace('_', ' ').title()}: {', '.join(value)}")
                                elif isinstance(value, str) and value.strip():
                                    global_context_used.append(f"{key.replace('_', ' ').title()}: {value}")
                        
                        if global_context_used:
                            st.markdown("**🌍 Global Context Used:**")
                            for info in global_context_used:
                                st.text(f"• {info}")
                        
                        # Type-specific context used
                        type_context_used = []
                        for key, value in context["type_specific"].items():
                            if value and key != "other":
                                if isinstance(value, list) and len(value) > 0:
                                    type_context_used.append(f"{key.replace('_', ' ').title()}: {', '.join(value)}")
                                elif isinstance(value, str) and value.strip():
                                    type_context_used.append(f"{key.replace('_', ' ').title()}: {value}")
                        
                        if type_context_used:
                            st.markdown("**🎯 Type-Specific Context Used:**")
                            for info in type_context_used:
                                st.text(f"• {info}")
                        
                        # External data used
                        if context["external_data"]:
                            st.markdown("**🌐 External Data Used:**")
                            for data_type, data in context["external_data"].items():
                                st.text(f"• {data_type.title()}: Available")
                        
                        # Missing information analysis
                        missing = storage.get_missing_information_for_type(classification_result["type"])
                        if missing["global"] or missing["type_specific"]:
                            st.markdown("**❓ Missing Information for Better Responses:**")
                            for field in (missing["global"] + missing["type_specific"])[:3]:
                                st.text(f"• {field.replace('_', ' ').title()}")
                        
                    except Exception as e:
                        st.text(f"Error showing context: {str(e)}")
                    
                    if classification_result.get("fallback_used"):
                        st.warning("⚠️ Fallback classification used due to LLM error")
        
        # Step 3: Save to Global Context Storage (NEW METHOD!)
        if classification_result and response:
            try:
                # Extract and store using global context method (NEW!)
                storage.extract_and_store_key_information(
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
                
                logger.info(f"Successfully saved to global context storage - Type: {classification_result['type']}")
                
            except Exception as e:
                st.error(f"❌ Error saving to global context storage: {str(e)}")
                logger.error(f"Global context storage save error: {str(e)}")
        
        # Rerun to update the chat display and sidebar stats
        st.rerun()
    
    # Footer with enhanced status
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Global Context Travel Assistant | Navan Junior AI Engineer Assignment<br>"
        "✅ Global Context Sharing | ✅ Type-Specific Storage | ✅ Context-Aware Prompts | ✅ Missing Info Detection"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()