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
from core.conversation_manager import ConversationManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Smart Travel Assistant - Navan Assignment",
    page_icon="✈️",
    layout="wide"
)

@st.cache_resource
def init_components():
    """
    Set up all the pieces we need for the travel assistant.
    
    This gets called once when the app starts and sets up our Redis storage,
    Gemini client, query classifier, and conversation manager. If anything
    fails to connect, we show helpful error messages to the user.
    """
    try:
        # Set up our context storage (uses Redis under the hood)
        storage = GlobalContextStorage()
        
        # Make sure Redis is actually working
        try:
            storage.redis_client.ping()
            st.success("✅ Context storage connected successfully")
        except Exception as e:
            st.error(f"❌ Redis connection failed: {str(e)}")
            st.error("Make sure Redis is running and REDIS_URL is configured correctly")
            return None, None, None, None
        
        # Set up our AI client
        gemini = GeminiClient()
        
        # Test that we can actually talk to Gemini
        if not gemini.test_connection():
            st.error("❌ Failed to connect to Gemini API. Check your GOOGLE_AI_API_KEY.")
            return None, None, None, None
        else:
            st.success("✅ Gemini API connection successful")
        
        # Set up the smart query classifier
        classifier = QueryClassifier(gemini)
        
        # Wire everything together with the conversation manager
        conversation_manager = ConversationManager(storage, gemini, classifier)
        
        return storage, gemini, classifier, conversation_manager
        
    except Exception as e:
        st.error(f"❌ Initialization error: {str(e)}")
        return None, None, None, None

def display_array_context_analysis(classification_result, storage):
    """
    Show the user what our smart analysis figured out from their question.
    
    This is like showing your work - we break down what type of question it was,
    what information we extracted, and how confident we are. Super useful for
    debugging and helping users understand why they got certain recommendations.
    """
    if not classification_result:
        return
        
    with st.expander("🧠 Smart Query Analysis", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Query Type", classification_result["type"])
            st.metric("Confidence", f"{classification_result.get('confidence_score', 0):.2f}")
            # Show which specialized handler handled this
            handler_used = classification_result["type"].replace('_', ' ').title()
            st.metric("Handler Used", f"{handler_used} Handler")
        
        with col2:
            st.metric("External Data", "Yes" if classification_result.get("external_data_needed") else "No")
            st.metric("Source", classification_result.get("primary_source", "unknown"))
        
        # Show what useful info we pulled from this specific question
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
        
        # Show the complete picture we built up over the whole conversation
        try:
            context = storage.get_complete_context_for_query_type(classification_result["type"])
            
            # Everything we know about the user from all their questions
            all_global = context["global"]
            if all_global:
                st.markdown("**🌍 Complete Global Context Used:**")
                for info in all_global:
                    st.text(f"• {info}")
            
            # Type-specific stuff we've learned
            all_type_specific = context["type_specific"]
            if all_type_specific:
                st.markdown("**🎯 Complete Type-Specific Context Used:**")
                for info in all_type_specific:
                    st.text(f"• {info}")
            
            # External APIs we hit for current data
            if context["external_data"]:
                st.markdown("**🌐 External Data Used:**")
                for data_type, data in context["external_data"].items():
                    st.text(f"• {data_type.title()}: Available")
            
        except Exception as e:
            st.text(f"Error showing complete context: {str(e)}")
        
        # Why we classified it this way
        st.markdown("**🤖 Classification Reasoning:**")
        st.text(classification_result.get("reasoning", "No reasoning provided"))
        
        # Show off the cool features each handler brings
        handler_type = classification_result["type"]
        st.markdown("**🚀 Smart Features Active:**")
        
        if handler_type == "destination_recommendations":
            st.text("✓ Multi-criteria decision making")
            st.text("✓ Chain-of-thought destination analysis")
            st.text("✓ Smart information gathering")
        elif handler_type == "packing_suggestions":
            st.text("✓ Weather-aware reasoning")
            st.text("✓ Activity-based packing logic")
            st.text("✓ Structured output generation")
        elif handler_type == "local_attractions":
            st.text("✓ Interest-based filtering")
            st.text("✓ Time-constraint awareness")
            st.text("✓ Priority ranking system")
        
        if classification_result.get("fallback_used"):
            st.warning("⚠️ Fallback classification used due to AI service error")

def main():
    """
    The main Streamlit app.
    
    """
    
    # App header and description
    st.title("🚀 Smart Travel Assistant")
    st.markdown("*Navan Junior AI Engineer Assignment - Intelligent Conversation System*")
    st.markdown("**✨ Features: Smart Context Management • Weather Integration • Specialized Handlers • Chain-of-Thought Reasoning**")
    st.markdown("---")
    
    # Get all our components set up
    storage, gemini, classifier, conversation_manager = init_components()
    
    if not conversation_manager:
        st.error("Failed to initialize components. Please check your configuration.")
        st.stop()
    
    # Sidebar with context stats and controls
    with st.sidebar:
        st.markdown("### 🌍 Context Statistics")
        
        try:
            stats = storage.get_storage_stats()
            
            # Show global context info
            global_stats = stats.get("global_context", {})
            global_items = global_stats.get("total_items", 0)
            global_data = global_stats.get("current_data", [])
            
            st.metric("Global Context Items", global_items)
            
            # Preview current global context
            if global_data:
                st.markdown("**Current Global Context:**")
                for item in global_data[:5]:  # Show first 5 items
                    st.text(f"• {item}")
                if len(global_data) > 5:
                    st.text(f"... and {len(global_data) - 5} more items")
            else:
                st.text("No global context yet")
            
            st.markdown("### 🎯 Type-Specific Context")
            
            # Show context for each query type we've seen
            type_stats = stats.get("type_specific", {})
            for query_type, info in type_stats.items():
                total_items = info.get("total_items", 0)
                type_name = query_type.replace('_', ' ').title()
                
                st.metric(f"{type_name}", f"{total_items} items")
                
                # Let users peek at the type-specific data
                type_data = info.get("current_data", [])
                if type_data:
                    with st.expander(f"View {type_name} Context", expanded=False):
                        for item in type_data:
                            st.text(f"• {item}")
            
            # Conversation overview
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
        
        # Reset button for testing
        if st.button("🗑️ Clear All Data"):
            try:
                storage.clear_all_data()
                st.success("✅ All data cleared!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error clearing data: {str(e)}")
        
        # Show what handlers are available
        st.markdown("### 🚀 Specialized Handlers")
        st.text("🎯 Destination Handler")
        st.text("🎒 Packing Handler") 
        st.text("🏛️ Attractions Handler")
        st.text("✅ Chain-of-thought reasoning")
        st.text("✅ Context-aware prompts")
        st.text("✅ Smart data integration")

        # Debug info for developers
        if hasattr(st.session_state, 'last_raw_gemini') and st.session_state.last_raw_gemini:
            st.markdown("### 🤖 Raw Gemini Response")
            with st.expander("View Raw Classification", expanded=False):
                st.json(st.session_state.last_raw_gemini)
    
    # Main content area - split view
    chat_col, prompt_col = st.columns([1, 1])  # Equal width columns
    
    # LEFT SIDE: Chat interface
    with chat_col:
        st.markdown("### 💬 Chat Interface")
        
        # Load and display conversation history
        try:
            conversation_history = storage.get_conversation_history()
            formatted_messages = conversation_manager.format_conversation_for_display(conversation_history)
            
            # Chat container for messages
            chat_container = st.container()
            
            with chat_container:
                # Show all previous messages
                for message in formatted_messages:
                    if message["type"] == "user":
                        with st.chat_message("user"):
                            st.write(message["content"])
                            
                            # Show the smart analysis if we have it
                            if message.get("classification"):
                                classification = message["classification"]
                                
                                with st.expander("🔍 Smart Query Analysis", expanded=False):
                                    # Key metrics from our analysis
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.metric("Query Type", classification.get("type", "unknown"))
                                        st.metric("Confidence", f"{classification.get('confidence_score', 0):.2f}")
                                    
                                    with col2:
                                        st.metric("External Data", "Yes" if classification.get("external_data_needed") else "No")
                                        st.metric("Source", classification.get("primary_source", "unknown"))
                                    
                                    # What we learned from this question
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
                                    
                                    # Why we classified it this way
                                    st.markdown("**Classification Reasoning:**")
                                    st.text(classification.get("reasoning", "No reasoning provided"))
                            
                    elif message["type"] == "assistant":
                        with st.chat_message("assistant"):
                            st.write(message["content"])
            
        except Exception as e:
            st.error(f"❌ Error loading conversation history: {str(e)}")
            formatted_messages = []
            conversation_history = []
    
    # RIGHT SIDE: Show the engineered prompts
    with prompt_col:
        st.markdown("### 🤖 Engineered Prompt")
        
        # Display the last prompt we built if we have one
        if hasattr(st.session_state, 'last_final_prompt') and st.session_state.last_final_prompt:
            st.code(st.session_state.last_final_prompt, language="text")
        else:
            st.info("The smart prompt engineered by our specialized handlers will appear here after you ask a question.")
    
    # Chat input at the bottom
    user_input = st.chat_input("Ask me anything about travel planning...")
    
    if user_input:
        # Show user message immediately
        with chat_col:
            with st.chat_message("user"):
                st.write(user_input)
        
        # Process the message with our smart system
        with chat_col:
            with st.chat_message("assistant"):
                
                with st.spinner("🚀 Processing with specialized handlers..."):
                    result = conversation_manager.process_user_message(user_input)
                    
                    classification_result = result['classification_result']
                    response = result['response']
                    final_prompt = result['final_prompt']
                    handler_used = result.get('handler_used', 'unknown')
                
                # Save debug info for the sidebar
                if hasattr(classifier, 'last_raw_gemini_response') and classifier.last_raw_gemini_response:
                    st.session_state.last_raw_gemini = classifier.last_raw_gemini_response
                
                # Save the engineered prompt for display
                if final_prompt:
                    st.session_state.last_final_prompt = final_prompt
                
                # Show the AI's response
                st.write(response)
                
                # Let users know which handler helped them
                if handler_used != 'fallback':
                    handler_name = handler_used.replace('_', ' ').title()
                    st.success(f"✨ Powered by {handler_name} Handler with smart prompt engineering")
                
                # Show the detailed analysis
                display_array_context_analysis(classification_result, storage)
        
        # Refresh the page to update everything
        st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "🚀 Smart Travel Assistant | Navan Junior AI Engineer Assignment<br>"
        "✅ Specialized Handlers | ✅ Chain-of-Thought Reasoning | ✅ Weather-Aware Prompts | ✅ Smart Context Management"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()