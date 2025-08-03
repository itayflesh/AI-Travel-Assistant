# AI Travel Assistant 🧳✈️

> **A production-ready conversational AI system demonstrating advanced prompt engineering, multi-agent architecture, and intelligent data routing for travel planning.**

## 🎯 Project Overview

This project is a **conversational AI travel assistant** built to demonstrate advanced AI engineering skills including sophisticated prompt engineering, context management, external data integration, and production-ready architecture. The system intelligently handles three types of travel queries through specialized handlers while maintaining conversation context and integrating real-time external data.

### 🏆 Key AI Engineering Highlights

- **Intelligent Query Classification**: LLM-powered classification with pattern matching fallbacks
- **Multi-Agent Architecture**: Specialized handlers for different travel query types
- **Advanced Prompt Engineering**: Context-aware, strategy-driven prompt construction
- **Smart Data Routing**: Intelligent decision-making between LLM knowledge and external APIs
- **Production Context Management**: Redis-based persistent storage with intelligent caching
- **Graceful Error Handling**: Comprehensive fallback mechanisms and error recovery

---

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │────│ Conversation     │────│ Query           │
│                 │    │ Manager          │    │ Classifier      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Redis Storage   │    │ Specialized      │    │ Gemini LLM      │
│ (Context)       │    │ Handlers         │    │ Client          │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌──────────────────────────┐
                    │ External APIs            │
                    │ • Weather (OpenWeather)  │
                    │ • Attractions (Amadeus)  │
                    └──────────────────────────┘
```

---

## 🔧 Core Components

### 1. **Query Classification System** (`core/query_classifier.py`)
- **Hybrid Classification**: Combines LLM reasoning with pattern matching
- **Information Extraction**: Extracts and categorizes user preferences across all query types
- **Confidence Scoring**: Implements fallback mechanisms for classification reliability
- **Cross-Type Intelligence**: Extracts information for all travel types, not just the primary query

### 2. **Specialized Handler Architecture** (`handlers/`)
- **Destination Handler**: Advanced prompt engineering for destination recommendations
- **Packing Handler**: Weather-aware packing suggestions with gear optimization  
- **Attractions Handler**: Real-time activity recommendations with preference matching
- **Completeness Analysis**: Each handler analyzes information quality and adjusts strategy accordingly

### 3. **Intelligent Context Management** (`core/redis_storage.py`)
- **Persistent Storage**: Redis-based session management with TTL
- **Smart Merging**: Intelligent context array merging avoiding duplicates
- **Cache Strategy**: External API data caching with automatic expiration
- **Cross-Query Context**: Information sharing between different query types

### 4. **Smart Data Routing** (`core/conversation_manager.py`)
- **API Decision Logic**: Classifier-driven external data usage
- **Fallback Mechanisms**: Graceful degradation when APIs fail
- **Geocoding Intelligence**: Gemini-enhanced location resolution for tourism centers
- **Response Orchestration**: Coordinates between multiple data sources

---

## 🧠 Advanced Prompt Engineering

### Strategic Prompt Construction
Each specialized handler implements sophisticated prompt engineering techniques:

#### **Information Completeness Analysis**
```python
# Analyzes available vs. required information
completeness_score = sum(category_scores) / total_categories
strategy = determine_response_strategy(completeness_score)
```

#### **Context-Aware Response Strategies**
- **Minimal Info**: Focus on clarifying questions while providing helpful suggestions
- **Partial Info**: Hybrid approach balancing recommendations with information gathering
- **Sufficient Info**: Confident recommendations with clear reasoning
- **Complete Info**: Detailed planning with comprehensive insights

#### **Chain-of-Thought Implementation**
```
Step 1: Analyze what the user really needs
Step 2: Consider their constraints and preferences  
Step 3: Provide specific, actionable advice
```

### **Dynamic Prompt Adaptation**
- **Conversation Context**: Avoids repetition by tracking previous exchanges
- **External Data Integration**: Seamlessly incorporates real-time weather and attractions
- **Response Length Optimization**: Adjusts verbosity based on information quality
- **Error Recovery**: Intelligent fallbacks when components fail

---

## 🌐 External Data Integration

### **Weather API Integration** (`external_apis/weather_api.py`)
- **Smart Geocoding**: Uses Gemini to identify tourism centers for precise weather data
- **Dual-Source Strategy**: OpenWeather city lookup with tourism center enhancement
- **Forecast Processing**: Filters 5-day forecast to relevant time periods
- **Error Handling**: Graceful fallbacks with informative error messages

### **Attractions API Integration** (`external_apis/attraction_api.py`)  
- **Tourism Center Mapping**: Gemini-powered identification of main tourist areas
- **Amadeus Integration**: Professional travel industry API for current attractions
- **Data Quality Filtering**: Cleans and formats attraction data for optimal presentation
- **Radius Optimization**: Balanced search radius for comprehensive yet relevant results

### **Intelligent Data Usage**
The system makes smart decisions about when to use external data:
- **Classification-Driven**: Classifier determines external data necessity
- **Quality Verification**: Validates data completeness before usage
- **Caching Strategy**: Prevents redundant API calls with intelligent TTL
- **Fallback Logic**: LLM knowledge when external data unavailable

---

## 🎛️ Technical Implementation

### **Multi-Level Error Handling**
```python
# Example: Robust classification with fallbacks
try:
    gemini_result = classify_with_gemini(query)
    pattern_result = classify_with_patterns(query)
    final_result = combine_classifications(gemini_result, pattern_result)
except Exception:
    return safe_fallback_classification()
```

### **Production-Ready Features**
- **Session Management**: Persistent user sessions with Redis
- **Rate Limiting**: Intelligent caching reduces API calls
- **Logging**: Comprehensive logging for debugging and monitoring
- **Configuration**: Environment-based configuration for different deployments
- **Input Validation**: Robust validation and sanitization

### **Performance Optimizations**
- **Context Filtering**: Only relevant context sent to LLM to optimize tokens
- **Strategic Caching**: 1-hour TTL for external data with quality validation
- **Prompt Efficiency**: Optimized prompt length while maintaining quality
- **Lazy Loading**: On-demand initialization of expensive resources

---

## 🚀 Getting Started

### **Prerequisites**
- Python 3.8+
- Redis server
- Google AI API key (Gemini)
- OpenWeatherMap API key
- Amadeus API credentials

### **Installation**

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/AI-Travel-Assistant.git
cd AI-Travel-Assistant
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
# Create .env file
GOOGLE_AI_API_KEY=your_gemini_api_key
WEATHER_API_KEY=your_openweather_api_key
AMADEUS_API_KEY=your_amadeus_api_key
AMADEUS_API_SECRET=your_amadeus_api_secret
REDIS_URL=redis://localhost:6379
```

4. **Run the application**
```bash
streamlit run main.py
```

---

## 💡 Usage Examples

### **Destination Recommendations**
```
User: "I want to go somewhere warm in March with a $3000 budget"
Assistant: [Analyzes budget, timeframe, climate preference]
          [Provides 3-4 specific destinations with reasoning]
          [Explains why each fits their criteria]
```

### **Smart Packing Suggestions**  
```
User: "What should I pack for Tokyo in March?"
Assistant: [Fetches real-time Tokyo weather]
          [Provides weather-informed packing list]
          [Categorizes by clothing, gear, essentials]
```

### **Local Attractions**
```
User: "Things to do in Paris for 3 days"
Assistant: [Gets current Paris attractions]
          [Filters by time constraints]
          [Prioritizes based on interests]
```

---

## 📁 Project Structure

```
AI-Travel-Assistant/
├── core/                          # Core system components
│   ├── conversation_manager.py    # Main orchestration logic
│   ├── query_classifier.py       # Intelligent query classification
│   └── redis_storage.py          # Context management & caching
├── handlers/                      # Specialized prompt handlers
│   ├── destination_handler.py    # Destination recommendations
│   ├── packing_handler.py        # Weather-aware packing advice
│   └── attractions_handler.py    # Activity recommendations
├── external_apis/                # External data integration
│   ├── weather_api.py            # OpenWeather integration
│   └── attraction_api.py         # Amadeus attractions API
├── llm/                          # LLM client management
│   └── gemini_client.py          # Google Gemini integration
├── main.py                       # Streamlit application
├── requirements.txt              # Dependencies
└── README.md                     # This file
```

---

*This project demonstrates advanced AI engineering skills including intelligent prompt engineering, multi-agent systems, external data integration, and production-ready architecture - all essential skills for building next-generation AI-powered applications.*