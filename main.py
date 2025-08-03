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
    page_title="Travel Chat",
    page_icon="💬",
    layout="wide"
)

# Custom CSS for chat styling
st.markdown("""
<style>
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main app styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-height: none;
    }
    
    /* Chat area - invisible scrollable container */
    .chat-scroll-area {
        height: 60vh;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 20px 0 80px 0;
        width: 100%;
        box-sizing: border-box;
        margin-bottom: 20px;
    }
    
    /* Scrollbar styling for the invisible container */
    .chat-scroll-area::-webkit-scrollbar {
        width: 8px;
    }
    
    .chat-scroll-area::-webkit-scrollbar-track {
        background: transparent;
    }
    
    .chat-scroll-area::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 10px;
    }
    
    .chat-scroll-area::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
    }
    
    /* Message container to ensure proper containment */
    .message-container {
        width: 100%;
        display: flex;
        margin: 15px 0;
        box-sizing: border-box;
        clear: both;
    }
    
    .user-container {
        justify-content: flex-end;
        padding-left: 20%;
    }
    
    .assistant-container {
        justify-content: flex-start;
        padding-right: 20%;
    }
    
    /* Chat message styling */
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 5px 18px;
        max-width: 100%;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        word-wrap: break-word;
        overflow-wrap: break-word;
        box-sizing: border-box;
    }
    
    .assistant-message {
        background-color: #f8f9fa;
        color: #333;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 5px;
        max-width: 100%;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        word-wrap: break-word;
        overflow-wrap: break-word;
        box-sizing: border-box;
    }
    
    .external-data-info {
        font-size: 0.75em;
        color: #6c757d;
        font-style: italic;
        margin-top: 4px;
        margin-left: 16px;
        opacity: 0.8;
    }
    
    /* Sidebar styling */
    .context-item {
        background-color: #f8f9fa;
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        font-size: 0.85em;
        line-height: 1.3;
    }
    
    .global-context {
        border-left-color: #28a745;
        background-color: #f8fff9;
    }
    
    .type-context {
        border-left-color: #ffc107;
        background-color: #fffcf5;
    }
    
    /* Remove old auto-scroll script */
    
    /* Sidebar sections */
    .sidebar .element-container {
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_components():
    """Initialize all components for the travel assistant."""
    try:
        # Set up context storage
        storage = GlobalContextStorage()
        
        # Test Redis connection
        try:
            storage.redis_client.ping()
        except Exception as e:
            st.error(f"Redis connection failed: {str(e)}")
            return None, None, None, None
        
        # Set up AI client
        gemini = GeminiClient()
        
        # Test Gemini connection
        if not gemini.test_connection():
            st.error("Failed to connect to Gemini API. Check your GOOGLE_AI_API_KEY.")
            return None, None, None, None
        
        # Set up classifier and conversation manager
        classifier = QueryClassifier(gemini)
        conversation_manager = ConversationManager(storage, gemini, classifier)
        
        return storage, gemini, classifier, conversation_manager
        
    except Exception as e:
        st.error(f"Initialization error: {str(e)}")
        return None, None, None, None

def display_context_sidebar(storage):
    """Display clean context information in the sidebar."""
    try:
        stats = storage.get_storage_stats()
        
        # Global Context Section
        st.markdown("### 🌍 Global Information")
        global_data = stats.get("global_context", {}).get("current_data", [])
        
        if global_data:
            for item in global_data:
                st.markdown(f'<div class="context-item global-context">{item}</div>', 
                          unsafe_allow_html=True)
        else:
            st.info("No global information yet")
        
        st.markdown("---")
        
        # Type-Specific Context
        st.markdown("### 🎯 Specific Information")
        type_stats = stats.get("type_specific", {})
        
        has_type_data = False
        for query_type, info in type_stats.items():
            type_data = info.get("current_data", [])
            if type_data:
                has_type_data = True
                # Clean type name for display
                type_name = query_type.replace('_', ' ').replace('suggestions', '').replace('recommendations', '').title()
                st.markdown(f"**{type_name}:**")
                
                for item in type_data:
                    st.markdown(f'<div class="context-item type-context">{item}</div>', 
                              unsafe_allow_html=True)
                st.markdown("")
        
        if not has_type_data:
            st.info("No specific information yet")
        
        st.markdown("---")
        
        # Clear data button
        if st.button("🗑️ Clear Chat", help="Clear all conversation data"):
            storage.clear_all_data()
            st.success("Chat cleared!")
            st.rerun()
            
    except Exception as e:
        st.error(f"Error loading context: {str(e)}")
            
    except Exception as e:
        st.error(f"Error loading context: {str(e)}")

def get_external_data_info(classification_result):
    """Get simple external data usage information."""
    if not classification_result or not classification_result.get("external_data_needed", False):
        return None
    
    external_data_type = classification_result.get("external_data_type", "none")
    
    if external_data_type == "weather":
        return "Used current weather data"
    elif external_data_type == "attractions":
        return "Used current attractions data"
    elif external_data_type == "both":
        return "Used weather and attractions data"
    
    return None

def display_chat_message(message, is_user=True, external_info=None):
    """Display a single chat message with proper styling."""
    if is_user:
        # User messages on the right
        st.markdown(f'''
        <div class="message-container user-container">
            <div class="user-message">{message}</div>
        </div>
        ''', unsafe_allow_html=True)
    else:
        # Assistant messages on the left
        external_html = f'<div class="external-data-info">{external_info}</div>' if external_info else ''
        st.markdown(f'''
        <div class="message-container assistant-container">
            <div class="assistant-message">
                {message}
                {external_html}
            </div>
        </div>
        ''', unsafe_allow_html=True)

def main():
    """Main application."""
    
    # # Clean header
    # st.title("💬 Travel Chat")
    # st.markdown("---")
    
    # Initialize components
    storage, gemini, classifier, conversation_manager = init_components()
    
    if not conversation_manager:
        st.error("Failed to initialize. Please check your configuration.")
        st.stop()
    
    # Layout: sidebar + main chat area
    with st.sidebar:
        display_context_sidebar(storage)
    
    # Main chat area
    # st.markdown("### Chat")
    
    # Create chat container
    chat_container = st.container()
    
    with chat_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        try:
            conversation_history = storage.get_conversation_history()
            
            # Display conversation history
            for i in range(len(conversation_history)):
                message = conversation_history[i]
                
                if "user_query" in message:
                    display_chat_message(message["user_query"], is_user=True)
                
                elif "assistant_answer" in message:
                    # Check if external data was used for this response
                    external_info = None
                    if "classification" in message:
                        external_info = get_external_data_info(message.get("classification"))
                    
                    display_chat_message(message["assistant_answer"], is_user=False, external_info=external_info)
            
        except Exception as e:
            st.error(f"Error loading conversation: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input
    user_input = st.chat_input("Type your travel question here...")
    
    if user_input:
        # Process the message
        with st.spinner("Thinking..."):
            result = conversation_manager.process_user_message(user_input)
        
        # Refresh to show new messages
        st.rerun()

if __name__ == "__main__":
    main()