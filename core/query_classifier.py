import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KeyInformation(BaseModel):
    """Simple structure for the key info we extract from user queries"""
    key_Global_information: List[str] = []
    key_specific_destination_recommendations_information: List[str] = []
    key_specific_packing_suggestions_information: List[str] = []
    key_specific_local_attractions_information: List[str] = []


class GeminiClassificationResult(BaseModel):
    """What we expect back from Gemini when it classifies a query"""
    reasoning_for_type: str
    type: str
    external_data_needed: bool
    external_data_reason: str
    key_Global_information: List[str] = []
    key_specific_destination_recommendations_information: List[str] = []
    key_specific_packing_suggestions_information: List[str] = []
    key_specific_local_attractions_information: List[str] = []

class QueryClassifier:
    """
    Figures out what type of travel question someone is asking and pulls out useful info.
    
    We use both Gemini and some basic pattern matching (as backup).
    The goal is to categorize queries into destination_recommendations, packing_suggestions,
    or local_attractions, plus extract any useful details for personalization.
    """
    
    def __init__(self, gemini_client):
        """Set up the classifier with our Gemini client and some pattern matching rules"""
        self.gemini_client = gemini_client
        
        # Basic keyword patterns for when Gemini isn't available
        self.type_patterns = {
            "destination_recommendations": {
                "keywords": [
                    "where to go", "destination", "recommend", "visit", "travel to",
                    "best places", "suggestions", "trip ideas", "vacation spots",
                    "cities", "countries", "places to visit", "travel recommendations"
                ],
                "phrases": [
                    "where should i go", "recommend a destination", "best place to visit",
                    "travel suggestions", "vacation ideas"
                ]
            },
            "packing_suggestions": {
                "keywords": [
                    "pack", "packing", "bring", "luggage", "suitcase", "clothes",
                    "clothing", "what to wear", "items", "essentials", "bag"
                ],
                "phrases": [
                    "what should i pack", "what to bring", "packing list",
                    "what clothes", "what items"
                ]
            },
            "local_attractions": {
                "keywords": [
                    "attractions", "activities", "things to do", "sightseeing",
                    "museums", "restaurants", "landmarks", "tours", "experiences",
                    "entertainment", "culture", "local", "places to see"
                ],
                "phrases": [
                    "things to do", "what to see", "attractions in", "activities in",
                    "places to visit in"
                ]
            }
        }
        
        # Words that suggest we need to hit external APIs
        self.external_data_patterns = {
            "weather_needed": [
                "weather", "temperature", "rain", "snow", "climate", "season",
                "pack", "packing", "clothes", "clothing", "what to wear"
            ],
            "location_specific": [
                "current", "now", "today", "this week", "real-time", "latest",
                "activities", "attractions", "things to do", "restaurants"
            ]
        }

        self.last_raw_gemini_response = None
    
    def classify_with_gemini(self, query: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Use Gemini to classify the query and extract useful info.
        
        We give Gemini a detailed prompt that asks it to:
        1. Figure out what type of travel question this is
        2. Decide if we need to fetch external data (weather/attractions)
        3. Pull out any useful details for future personalization
        
        We extract info for ALL query types, not just the primary one. 
        So if someone asks "where can I go that doesn't require much packing",
        that's primarily a destination question, but we also save the packing preference.

        """
        # Build conversation context if we have chat history
        conversation_context = ""
        if conversation_history and len(conversation_history) > 0:
            # Keep it recent to avoid overwhelming the prompt
            recent_messages = conversation_history[-8:]
            
            conversation_context = "\nCONVERSATION CONTEXT:\n"
            for msg in recent_messages:
                if "user_query" in msg:
                    conversation_context += f"User: {msg['user_query']}\n"
                elif "assistant_answer" in msg:
                    answer = msg['assistant_answer']
                    conversation_context += f"Assistant: {answer}\n"
            conversation_context += "\n"

        # This is our main prompt - it's long but very specific about what we want
        prompt = f"""You are an expert travel query classifier. Analyze this travel query and provide a structured response.

        {conversation_context}QUERY: "{query}"

        MANDATORY CLASSIFICATION TYPES (you MUST choose exactly one):
        1. "destination_recommendations" - asking where to go, travel suggestions, destination advice
        2. "packing_suggestions" - asking what to pack, bring, or wear for travel
        3. "local_attractions" - asking about things to do, see, or experience at a destination

        ANALYSIS FRAMEWORK:
        Step 1: What is the user's primary intent?
        Step 2: Which of the 3 mandatory types best matches this intent?
        Step 3: Does answering this query require external data? We ONLY have 2 external data sources: Right NOW + 5 days forecast WEATHER data and LOCAL ATTRACTIONS data. If the query doesn't need right now weather information OR current attractions information, then external_data_needed should be False and external_data_type should be "none".
        Step 4: What key user preferences or information can be extracted for future personalization?

        KEY INFORMATION EXTRACTION:
        Extract information as "key: value" formatted strings and categorize into:

        **key_Global_information** (shared across ALL query types):
        ONLY if you found information that is relevant to all the 3 above types, such as:
        - A particular region of the world or continent (e.g., "region: Southeast Asia", "continent: Europe")
        - destination: [location name] (e.g., "destination: Tokyo", "destination: France" - Country / Region / Continent)  
        - travel_dates: [when traveling] (e.g., "travel_dates: March 2025", "travel_dates: next summer")
        - duration: [trip length] (e.g., "duration: 2 weeks", "duration: long weekend")
        - budget: [money available] (e.g., "budget: $3000", "budget: tight budget")
        - group_size: [number of people] (e.g., "group_size: 2 people", "group_size: solo travel")
        - interests: [general interests] (e.g., "interests: culture and food", "interests: adventure sports")

        **key_specific_destination_recommendations_information** (for destination recommendations):
        - travel_style: [how they like to travel] (e.g., "travel_style: luxury", "travel_style: backpacking", "travel_style: romantic getaway")
        - constraints: [limitations] (e.g., "constraints: no long flights", "constraints: visa-free countries", "constraints: minimal luggage needed")
        - climate_preference: [weather preference] (e.g., "climate_preference: warm beaches", "climate_preference: cool mountains")
        - other: [additional destination_recommendations key information] (e.g., "composition of group: family-friendly")

        **key_specific_packing_suggestions_information** (for packing suggestions):
        - activities: [planned activities] (e.g., "activities: hiking and swimming", "activities: business meetings")
        - luggage_type: [bag preference] (e.g., "luggage_type: backpack", "luggage_type: suitcase", "luggage_type: minimal luggage")
        - special_needs: [special requirements] (e.g., "special_needs: cold weather gear", "special_needs: formal clothes")
        - laundry_availability: [washing clothes] (e.g., "laundry_availability: hotel service", "laundry_availability: none")
        - other: [additional packing_suggestions key information] (e.g., "other: traveling with kids", "other: long-term travel")

        **key_specific_local_attractions_information** (for local attractions):
        - time_available: [how much time] (e.g., "time_available: 3 days", "time_available: half day")
        - mobility: [physical capability] (e.g., "mobility: wheelchair accessible", "mobility: loves walking")
        - budget_per_activity: [spending per activity] (e.g., "budget_per_activity: $50", "budget_per_activity: free activities")
        - accessibility_needs: [special access needs] (e.g., "accessibility_needs: wheelchair ramps", "accessibility_needs: audio guides")
        - other: [additional local_attractions key information])

        CROSS-TYPE EXTRACTION:
        IMPORTANT: Extract information for ALL relevant types, not just the primary classified type. For example:
        - If someone asks "I want to go somewhere I don't need big luggage" - this is primarily destination_recommendations, but ALSO extract "luggage_type: minimal luggage" for packing_suggestions
        - If someone asks "What to pack for hiking in mountains" - this is primarily packing_suggestions, but ALSO extract "activities: hiking" for local_attractions

        CRITICAL EXTRACTION RULES:
        - Format each item as "key: value" (never just the value alone)
        - ONLY extract information that is explicitly mentioned by the user
        - DO NOT extract "unknown", "not specified", or similar placeholder values
        - DO NOT make assumptions about missing information
        - If the user doesn't mention something, DO NOT include it in the arrays
        - Leave arrays completely empty if no relevant information is actually provided
        - Example: If user says "I want to go to Asia" - only extract "destination: Asia", don't add travel_style, constraints, etc.

        Respond with this specific JSON:
        {{
            "type": "one of the three types",
            "reasoning for type": "brief explanation of why this classification",
            "external_data_needed": true/false,
            "external_data_type": "weather/attractions/both/none",
            "external_data_reason": "explanation of why external data is/isn't needed",
            "key_Global_information": [
                "key: value format strings that apply to all query types"
            ],
            "key_specific_destination_recommendations_information": [
                "key: value format strings specific to destination recommendations"
            ],
            "key_specific_packing_suggestions_information": [
                "key: value format strings specific to packing suggestions"
            ],
            "key_specific_local_attractions_information": [
                "key: value format strings specific to local attractions"
            ]
        }}"""
        try:
            response = self.gemini_client.generate_response(prompt)
            
            # Clean up the response - sometimes it comes wrapped in markdown
            response_clean = response.strip()
            
            if "```json" in response_clean:
                json_start = response_clean.find("```json") + 7
                json_end = response_clean.find("```", json_start)
                response_clean = response_clean[json_start:json_end].strip()
            elif "```" in response_clean:
                json_start = response_clean.find("```") + 3
                json_end = response_clean.find("```", json_start)
                response_clean = response_clean[json_start:json_end].strip()
            
            result = json.loads(response_clean)

            # Keep the raw response for debugging
            self.last_raw_gemini_response = result
            
            # Make sure we got all the fields we need
            required_fields = ["type", "reasoning for type", "external_data_needed", "external_data_type", 
                             "key_Global_information", "key_specific_destination_recommendations_information", 
                             "key_specific_packing_suggestions_information", "key_specific_local_attractions_information"]
            if not all(key in result for key in required_fields):
                raise ValueError(f"Missing required fields in LLM response. Got: {list(result.keys())}")
            
            # Validate the type is one we recognize
            valid_types = ["destination_recommendations", "packing_suggestions", "local_attractions"]
            if result["type"] not in valid_types:
                logger.warning(f"LLM returned invalid type: {result['type']}, defaulting to destination_recommendations")
                result["type"] = "destination_recommendations"
            
            # Validate external data type
            valid_external_types = ["weather", "attractions", "both", "none"]
            if result.get("external_data_type") not in valid_external_types:
                logger.warning(f"LLM returned invalid external_data_type: {result.get('external_data_type')}, defaulting to 'none'")
                result["external_data_type"] = "none"
                result["external_data_needed"] = False
            
            # Make sure all the arrays are actually arrays
            array_fields = ["key_Global_information", "key_specific_destination_recommendations_information", 
                          "key_specific_packing_suggestions_information", "key_specific_local_attractions_information"]
            for field in array_fields:
                if not isinstance(result.get(field), list):
                    result[field] = []
            
            logger.info(f"Gemini classification successful: {result['type']}")
            logger.info(f"Global info extracted: {len(result['key_Global_information'])} items")
            logger.info(f"Destination info extracted: {len(result['key_specific_destination_recommendations_information'])} items")
            logger.info(f"Packing info extracted: {len(result['key_specific_packing_suggestions_information'])} items")
            logger.info(f"Attractions info extracted: {len(result['key_specific_local_attractions_information'])} items")
            
            return result
                
        except Exception as e:
            logger.error(f"Gemini classification failed: {str(e)}")
            raise Exception(f"LLM classification error: {str(e)}")

    
    def classify_with_patterns(self, query: str) -> Dict[str, Any]:
        """
        Basic pattern matching as a backup when Gemini isn't working.
        
        """
        query_lower = query.lower()
        
        # Score each query type based on keyword matches
        type_scores = {}
        
        for query_type, patterns in self.type_patterns.items():
            score = 0
            matches = []
            
            # Check for individual keywords
            for keyword in patterns["keywords"]:
                if keyword in query_lower:
                    score += 1
                    matches.append(keyword)
            
            # Phrases get double points because they're more specific
            for phrase in patterns["phrases"]:
                if phrase in query_lower:
                    score += 2
                    matches.append(phrase)
            
            # Normalize the score
            total_patterns = len(patterns["keywords"]) + len(patterns["phrases"])
            normalized_score = score / total_patterns if total_patterns > 0 else 0
            
            type_scores[query_type] = {
                "score": normalized_score,
                "matches": matches
            }
        
        # Pick the highest scoring type
        best_type = max(type_scores.keys(), key=lambda k: type_scores[k]["score"])
        best_score = type_scores[best_type]["score"]
        
        # If nothing matched well, default to destinations
        if best_score == 0:
            best_type = "destination_recommendations"
            best_score = 0.1
        
        # Figure out if we need external data
        external_data_needed = False
        external_data_reason = "Pattern matching suggests no external data needed"
        external_data_type = "none"
        
        weather_matches = sum(1 for pattern in self.external_data_patterns["weather_needed"] 
                            if pattern in query_lower)
        
        location_matches = sum(1 for pattern in self.external_data_patterns["location_specific"]
                             if pattern in query_lower)
        
        if weather_matches > 0 :
            external_data_needed = True
            external_data_reason = "Weather query detected with weather-specific terms"
            external_data_type = "weather"
        if location_matches > 0 :
            external_data_needed = True
            external_data_reason = "Location-specific query detected with location terms"
            if external_data_type == "none":
                external_data_type = "attractions"
            if external_data_type == "weather":
                external_data_type = "both"
                external_data_reason = "Weather and location-specific query detected"


        
        result = {
            "type": best_type,
            "external_data_needed": external_data_needed,
            "external_data_reason": external_data_reason,
            "external_data_type": external_data_type,
            "confidence": best_score,
            "all_scores": type_scores,
            "reasoning": f"Pattern matching: {type_scores[best_type]['matches']}",
            # Pattern matching can't extract detailed info like the LLM can
            "key_Global_information": [],
            "key_specific_destination_recommendations_information": [],
            "key_specific_packing_suggestions_information": [],
            "key_specific_local_attractions_information": []
        }
        
        logger.info(f"Pattern classification: {best_type} (confidence: {best_score:.2f})")
        return result
    
    def combine_classifications(self, gemini_result: Dict[str, Any], 
                              pattern_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Take the results from both Gemini and pattern matching and pick the best one.
        
        """
        
        # How much we trust each method
        GEMINI_WEIGHT = 0.8
        PATTERN_WEIGHT = 0.2
        AGREEMENT_BONUS = 0.3  # Extra confidence when they agree
        
        final_result = {
            "type": None,
            "external_data_needed": False,
            "external_data_type": "none",
            "key_Global_information": [],
            "key_specific_destination_recommendations_information": [],
            "key_specific_packing_suggestions_information": [],
            "key_specific_local_attractions_information": [],
            "confidence_score": 0.0,
            "primary_source": None,
            "reasoning": "",
            "fallback_used": False
        }
        
        try:
            # Do both methods agree on the query type?
            types_agree = gemini_result["type"] == pattern_result["type"]
            
            # Calculate confidence scores
            gemini_confidence = GEMINI_WEIGHT
            pattern_confidence = PATTERN_WEIGHT * pattern_result["confidence"]
            
            if types_agree:
                # Both methods agree - we're confident
                final_result["type"] = gemini_result["type"]
                final_result["confidence_score"] = gemini_confidence + pattern_confidence + AGREEMENT_BONUS
                final_result["primary_source"] = "consensus"
                final_result["reasoning"] = f"Both LLM and patterns agree on {gemini_result['type']}"
                
            elif gemini_confidence > pattern_confidence:
                # Trust the LLM
                final_result["type"] = gemini_result["type"]
                final_result["confidence_score"] = gemini_confidence
                final_result["primary_source"] = "llm"
                final_result["reasoning"] = f"LLM classification preferred: {gemini_result['type']}"
                
            else:
                # Pattern matching won out
                final_result["type"] = pattern_result["type"]
                final_result["confidence_score"] = pattern_confidence
                final_result["primary_source"] = "patterns"
                final_result["reasoning"] = f"Pattern matching preferred: {pattern_result['type']}"
            
            # For external data, trust Gemini if we have it
            if "external_data_needed" in gemini_result:
                final_result["external_data_needed"] = gemini_result["external_data_needed"]
                final_result["external_data_reason"] = gemini_result.get("external_data_reason", "LLM recommendation")
                final_result["external_data_type"] = gemini_result.get("external_data_type", "none")
            else:
                final_result["external_data_needed"] = pattern_result["external_data_needed"]
                final_result["external_data_reason"] = pattern_result["external_data_reason"]
                final_result["external_data_type"] = pattern_result["external_data_type"]
            
            # Only Gemini can extract the detailed user preferences
            final_result["key_Global_information"] = gemini_result.get("key_Global_information", [])
            final_result["key_specific_destination_recommendations_information"] = gemini_result.get("key_specific_destination_recommendations_information", [])
            final_result["key_specific_packing_suggestions_information"] = gemini_result.get("key_specific_packing_suggestions_information", [])
            final_result["key_specific_local_attractions_information"] = gemini_result.get("key_specific_local_attractions_information", [])
            
            logger.info(f"Combined classification: {final_result['type']} (confidence: {final_result['confidence_score']:.2f})")
            logger.info(f"Global info: {len(final_result['key_Global_information'])} items")
            logger.info(f"Destination info: {len(final_result['key_specific_destination_recommendations_information'])} items")
            logger.info(f"Packing info: {len(final_result['key_specific_packing_suggestions_information'])} items")
            logger.info(f"Attractions info: {len(final_result['key_specific_local_attractions_information'])} items")
            
        except Exception as e:
            logger.error(f"Error combining classifications: {str(e)}")
            # Emergency fallback
            final_result = {
                "type": "destination_recommendations",
                "external_data_needed": False,
                "key_Global_information": [],
                "key_specific_destination_recommendations_information": [],
                "key_specific_packing_suggestions_information": [],
                "key_specific_local_attractions_information": [],
                "confidence_score": 0.1,
                "primary_source": "fallback",
                "reasoning": "Error in classification - using safe default",
                "fallback_used": True,
                "error": str(e)
            }
        
        return final_result
    
    def classify_query(self, query: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classify a user's travel query.
        
        This orchestrates the whole process:
        1. Try to use Gemini for smart classification and info extraction
        2. Use pattern matching as backup and validation
        3. Combine the results intelligently
        4. Return everything the conversation manager needs
        
        """
        logger.info(f"Classifying query: {query[:50]}...")
        
        # Try the smart approach first
        gemini_result = None
        try:
            gemini_result = self.classify_with_gemini(query, conversation_history)
        except Exception as e:
            logger.error(f"Gemini classification failed: {str(e)}")
        
        # Always do pattern matching for backup/validation
        pattern_result = self.classify_with_patterns(query)
        
        # Combine the results or fall back
        if gemini_result:
            final_result = self.combine_classifications(gemini_result, pattern_result)
        else:
            # Gemini failed - use pattern matching only
            logger.warning("Using pattern matching fallback due to LLM failure")
            final_result = {
                "type": pattern_result["type"],
                "external_data_needed": pattern_result["external_data_needed"],
                "external_data_type": pattern_result["external_data_type"],
                "key_Global_information": [],
                "key_specific_destination_recommendations_information": [],
                "key_specific_packing_suggestions_information": [],
                "key_specific_local_attractions_information": [],
                "confidence_score": pattern_result["confidence"],
                "primary_source": "patterns_fallback",
                "reasoning": "LLM failed - using pattern matching only",
                "fallback_used": True
            }
        
        # Add some metadata
        final_result["timestamp"] = datetime.utcnow().isoformat()
        final_result["query"] = query
        
        logger.info(f"Final classification: {final_result}")
        return final_result