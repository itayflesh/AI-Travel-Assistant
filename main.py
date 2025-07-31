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
        # Initialize Global Context Storage
        storage = GlobalContextStorage()
        
        # Test Redis connection
        try:
            storage.redis_client.ping()
            st.success("✅ Array-Based Context Storage connection successful")
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

def build_array_context_aware_prompt(storage, query_type, user_query):
    """
    Build a context-aware prompt using array-based global + type-specific context.
    This is the enhanced version that handles array-based "key: value" information!
    """
    try:
        # Get complete context (global + type-specific arrays + external data)
        context = storage.get_complete_context_for_query_type(query_type)
        
        global_info_array = context["global"]
        type_specific_info_array = context["type_specific"]
        external_data = context["external_data"]
        
        # Build base prompt
        prompt_parts = [
            f"You are an expert travel assistant specializing in {query_type.replace('_', ' ')}.",
            f"User Query: {user_query}",
            "",
        ]
        
        # Add GLOBAL context (shared across all query types)
        if global_info_array and len(global_info_array) > 0:
            prompt_parts.append("TRAVELER PROFILE (from previous conversations):")
            for info_item in global_info_array:
                prompt_parts.append(f"- {info_item}")
            prompt_parts.append("")
        
        # Add TYPE-SPECIFIC context based on query type
        if type_specific_info_array and len(type_specific_info_array) > 0:
            type_name = query_type.replace('_', ' ').title()
            prompt_parts.append(f"{type_name.upper()} PREFERENCES:")
            for info_item in type_specific_info_array:
                prompt_parts.append(f"- {info_item}")
            prompt_parts.append("")
        
        # Add EXTERNAL data if available
        if query_type == "packing_suggestions" and external_data.get("weather"):
            weather = external_data["weather"]
            prompt_parts.append("CURRENT WEATHER DATA:")
            prompt_parts.append(f"- Weather Forecast: {weather}")
            prompt_parts.append("")
        
        elif query_type == "local_attractions" and external_data.get("attractions"):
            attractions = external_data["attractions"]
            prompt_parts.append("CURRENT ATTRACTIONS DATA:")
            prompt_parts.append(f"- Available Attractions: {attractions}")
            prompt_parts.append("")
        
        # Final instruction with context awareness
        if global_info_array or type_specific_info_array:
            prompt_parts.append("Provide personalized advice based on their profile information above. If any important information is missing for better recommendations, politely ask for it.")
        else:
            prompt_parts.append("Provide helpful travel advice. Ask for key information that would help you give more personalized recommendations.")
        
        final_prompt = "\n".join(prompt_parts)
        logger.info(f"Built array context-aware prompt for {query_type} ({len(final_prompt)} chars)")
        logger.info(f"Used {len(global_info_array)} global + {len(type_specific_info_array)} type-specific context items")
        
        return final_prompt
        
    except Exception as e:
        logger.error(f"Error building array context-aware prompt: {str(e)}")
        # Fallback to simple prompt
        return f"You are a travel assistant. User asks: {user_query}. Please provide helpful advice."

def format_conversation_for_display(conversation_history):
    """Format conversation history for Streamlit display"""
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

def display_array_context_analysis(classification_result, storage):
    """Display enhanced context analysis for array-based storage"""
    if not classification_result:
        return
        
    with st.expander("🧠 Array-Based Context Analysis", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Query Type", classification_result["type"])
            st.metric("Confidence", f"{classification_result.get('confidence_score', 0):.2f}")
        
        with col2:
            st.metric("External Data", "Yes" if classification_result.get("external_data_needed") else "No")
            st.metric("Source", classification_result.get("primary_source", "unknown"))
        
        # Show information extracted in this query
        global_info = classification_result.get("key_Global_information", [])
        type_specific_info = classification_result.get("key_specific_type_information", [])
        
        if global_info:
            st.markdown("**🌍 Global Information Extracted (This Query):**")
            for info in global_info:
                st.text(f"• {info}")
        
        if type_specific_info:
            st.markdown("**🎯 Type-Specific Information Extracted (This Query):**")
            for info in type_specific_info:
                st.text(f"• {info}")
        
        # Show complete context used for response
        try:
            context = storage.get_complete_context_for_query_type(classification_result["type"])
            
            # All global context (accumulated)
            all_global = context["global"]
            if all_global:
                st.markdown("**🌍 Complete Global Context Used:**")
                for info in all_global:
                    st.text(f"• {info}")
            
            # All type-specific context (accumulated)
            all_type_specific = context["type_specific"]
            if all_type_specific:
                st.markdown("**🎯 Complete Type-Specific Context Used:**")
                for info in all_type_specific:
                    st.text(f"• {info}")
            
            # External data used
            if context["external_data"]:
                st.markdown("**🌐 External Data Used:**")
                for data_type, data in context["external_data"].items():
                    st.text(f"• {data_type.title()}: Available")
            
        except Exception as e:
            st.text(f"Error showing complete context: {str(e)}")
        
        # Classification reasoning
        st.markdown("**🤖 Classification Reasoning:**")
        st.text(classification_result.get("reasoning", "No reasoning provided"))
        
        if classification_result.get("fallback_used"):
            st.warning("⚠️ Fallback classification used due to LLM error")

def main():
    """Main Streamlit application with Array-Based Context Management"""
    
    # Title and description
    st.title("🧠 Array-Based Context Travel Assistant")
    st.markdown("*Navan Junior AI Engineer Assignment - Flexible Array-Based Context Storage*")
    st.markdown("---")
    
    # Initialize components
    storage, gemini, classifier = init_components()
    
    if not storage or not gemini or not classifier:
        st.error("Failed to initialize components. Please check your configuration.")
        st.stop()
    
    # Enhanced sidebar with array-based context statistics
    with st.sidebar:
        st.markdown("### 🌍 Array-Based Context Stats")
        
        try:
            stats = storage.get_storage_stats()
            
            # Global context stats
            global_stats = stats.get("global_context", {})
            global_items = global_stats.get("total_items", 0)
            global_data = global_stats.get("current_data", [])
            
            st.metric("Global Context Items", global_items)
            
            # Show current global data
            if global_data:
                st.markdown("**Current Global Context:**")
                for item in global_data[:5]:  # Show first 5 items
                    st.text(f"• {item}")
                if len(global_data) > 5:
                    st.text(f"... and {len(global_data) - 5} more items")
            else:
                st.text("No global context yet")
            
            st.markdown("### 🎯 Type-Specific Context")
            
            # Type-specific stats
            type_stats = stats.get("type_specific", {})
            for query_type, info in type_stats.items():
                total_items = info.get("total_items", 0)
                type_name = query_type.replace('_', ' ').title()
                
                st.metric(f"{type_name}", f"{total_items} items")
                
                # Show some type-specific data
                type_data = info.get("current_data", [])
                if type_data:
                    with st.expander(f"View {type_name} Context", expanded=False):
                        for item in type_data:
                            st.text(f"• {item}")
            
            # Conversation stats
            st.markdown("### 💬 Conversation Stats")
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
        st.markdown("### 🏗️ Array-Based Architecture")
        st.text("✅ Flexible array storage")
        st.text("✅ Key: value format")
        st.text("✅ No predefined schemas")
        st.text("✅ Intelligent merging")
        st.text("✅ Context-aware prompts")

        # Raw Gemini Response (debugging)
        if hasattr(st.session_state, 'last_raw_gemini') and st.session_state.last_raw_gemini:
            st.markdown("### 🤖 Raw Gemini Response")
            with st.expander("View Raw Classification", expanded=False):
                st.json(st.session_state.last_raw_gemini)
    
    # Main chat interface
    st.markdown("### 💬 Chat with Array-Based Context Assistant")
    
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
                            classification = message["classification"]
                            
                            with st.expander("🔍 Smart Query Analysis", expanded=False):
                                # Main metrics
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Query Type", classification.get("type", "unknown"))
                                    st.metric("Confidence", f"{classification.get('confidence_score', 0):.2f}")
                                
                                with col2:
                                    st.metric("External Data", "Yes" if classification.get("external_data_needed") else "No")
                                    st.metric("Source", classification.get("primary_source", "unknown"))
                                
                                # Show array-based information extracted
                                global_info = classification.get("key_Global_information", [])
                                type_info = classification.get("key_specific_type_information", [])
                                
                                if global_info:
                                    st.markdown("**🌍 Global Information Extracted:**")
                                    for info in global_info:
                                        st.text(f"• {info}")
                                
                                if type_info:
                                    st.markdown("**🎯 Type-Specific Information Extracted:**")
                                    for info in type_info:
                                        st.text(f"• {info}")
                                
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
            
            # Step 1: Classify the query
            with st.spinner("🔍 Analyzing your query with array-based extraction..."):
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
                        "key_Global_information": [],
                        "key_specific_type_information": [],
                        "confidence_score": 0.1,
                        "primary_source": "fallback",
                        "reasoning": f"Classification error - using fallback: {str(e)}",
                        "fallback_used": True,
                        "error": str(e)
                    }
            
            # Step 2: Generate array context-aware response
            with st.spinner("🧠 Generating array context-aware response..."):
                try:
                    # Build array context-aware prompt
                    context_prompt = build_array_context_aware_prompt(
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
            
            # Show enhanced array-based context analysis
            display_array_context_analysis(classification_result, storage)
        
        # Step 3: Save to Array-Based Context Storage
        if classification_result and response:
            try:
                # Extract and store using array-based method
                storage.extract_and_store_key_information(
                    classification_result["type"], 
                    classification_result.get("key_Global_information", []),
                    classification_result.get("key_specific_type_information", [])
                )
                
                # Save user query with full classification data
                query_data = {
                    "query": user_input,
                    **classification_result
                }
                storage.save_user_query(query_data)
                
                # Save assistant answer
                storage.save_assistant_answer(response)
                
                logger.info(f"Successfully saved to array-based context storage - Type: {classification_result['type']}")
                logger.info(f"Global items: {len(classification_result.get('key_Global_information', []))}")
                logger.info(f"Type-specific items: {len(classification_result.get('key_specific_type_information', []))}")
                
            except Exception as e:
                st.error(f"❌ Error saving to array-based context storage: {str(e)}")
                logger.error(f"Array-based context storage save error: {str(e)}")
        
        # Rerun to update the chat display and sidebar stats
        st.rerun()
    
    # Footer with enhanced status
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Array-Based Context Travel Assistant | Navan Junior AI Engineer Assignment<br>"
        "✅ Flexible Array Storage | ✅ Key:Value Format | ✅ No Schema Limits | ✅ Smart Context Merging"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()