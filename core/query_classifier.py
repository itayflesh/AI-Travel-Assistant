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
    """Pydantic model for extracted key information"""
    destination: Optional[str] = None
    dates: Optional[str] = None
    budget: Optional[str] = None
    interests: List[str] = []
    constraints: List[str] = []
    other: Optional[str] = None


class GeminiClassificationResult(BaseModel):
    """Pydantic model for Gemini classification response"""
    reasoning: str
    type: str
    external_data_needed: bool
    external_data_reason: str
    key_information: KeyInformation

class QueryClassifier:
    """
    Advanced query classifier that uses both LLM and pattern matching
    to determine query type, external data needs, and extract key information.
    
    Demonstrates AI engineering skills for Navan assignment.
    """
    
    def __init__(self, gemini_client):
        """
        Initialize the query classifier
        
        Args:
            gemini_client: Initialized GeminiClient instance
        """
        self.gemini_client = gemini_client
        
        # Pattern matching rules for each query type
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
        
        # External data indicators
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
    
    def classify_with_gemini(self, query: str) -> Dict[str, Any]:
        """
        Use Gemini LLM to classify query with advanced prompt engineering.
        Forces classification into one of the 3 types and extracts key information.
        
        Args:
            query: User's travel query
            
        Returns:
            Dict with type, external_data_needed, and key_information
        """
        
        prompt = f"""You are an expert travel query classifier. Analyze this travel query and provide a structured response.

QUERY: "{query}"

MANDATORY CLASSIFICATION TYPES (you MUST choose exactly one):
1. "destination_recommendations" - asking where to go, travel suggestions, destination advice
2. "packing_suggestions" - asking what to pack, bring, or wear for travel
3. "local_attractions" - asking about things to do, see, or experience at a destination

ANALYSIS FRAMEWORK:
Step 1: What is the user's primary intent?
Step 2: Which of the 3 mandatory types best matches this intent?
Step 3: Does answering this query require external data? We ONLY have 2 external data sources: Right now WEATHER data and CURRENT LOCAL ATTRACTIONS data. If the query doesn't need right now weather information OR current attractions information, then external_data_needed should be False and external_data_type should be "none".
Step 4: What key user preferences or information can be extracted for future personalization?

KEY INFORMATION TO EXTRACT (if mentioned):
For destination_recommendations: budget range, travel style, interests, group size, dates, constraints
For packing_suggestions: destination, dates, activities planned, climate preferences, special needs
For local_attractions: interests, activity level, time available, group type, budget, accessibility needs

Respond with JSON:
{{
    "reasoning": "brief explanation",
    "type": "one of the three types",
    "external_data_needed": true/false,
    "external_data_type": "weather/attractions/both/none",
    "external_data_reason": "explanation",
    "key_information": {{
        "destination": null,
        "dates": null,
        "budget": null,
        "interests": [],
        "constraints": [],
        "other": null
    }}
}}"""

        try:
            response = self.gemini_client.generate_response(prompt, max_tokens=500)
            
            # Clean and parse JSON
            response_clean = response.strip()
            
            # Find JSON block if wrapped in markdown
            if "```json" in response_clean:
                json_start = response_clean.find("```json") + 7
                json_end = response_clean.find("```", json_start)
                response_clean = response_clean[json_start:json_end].strip()
            elif "```" in response_clean:
                json_start = response_clean.find("```") + 3
                json_end = response_clean.find("```", json_start)
                response_clean = response_clean[json_start:json_end].strip()
            
            result = json.loads(response_clean)

            # Store raw response for debugging/testing
            self.last_raw_gemini_response = result
            
            # Validate required fields
            if not all(key in result for key in ["type", "external_data_needed", "external_data_type", "key_information"]):
                raise ValueError("Missing required fields in LLM response")
            
            # Ensure type is one of the three allowed
            valid_types = ["destination_recommendations", "packing_suggestions", "local_attractions"]
            if result["type"] not in valid_types:
                logger.warning(f"LLM returned invalid type: {result['type']}, defaulting to destination_recommendations")
                result["type"] = "destination_recommendations"
            
            # Validate external_data_type
            valid_external_types = ["weather", "attractions", "both", "none"]
            if result.get("external_data_type") not in valid_external_types:
                logger.warning(f"LLM returned invalid external_data_type: {result.get('external_data_type')}, defaulting to 'none'")
                result["external_data_type"] = "none"
                result["external_data_needed"] = False
            
            logger.info(f"Gemini classification successful: {result['type']}")
            return result
                
        except Exception as e:
            logger.error(f"Gemini classification failed: {str(e)}")
            raise Exception(f"LLM classification error: {str(e)}")

    
    def classify_with_patterns(self, query: str) -> Dict[str, Any]:
        """
        Use pattern matching as backup classification method.
        
        Args:
            query: User's travel query
            
        Returns:
            Dict with type, external_data_needed, and confidence scores
        """
        query_lower = query.lower()
        
        # Calculate scores for each type
        type_scores = {}
        
        for query_type, patterns in self.type_patterns.items():
            score = 0
            matches = []
            
            # Check keywords
            for keyword in patterns["keywords"]:
                if keyword in query_lower:
                    score += 1
                    matches.append(keyword)
            
            # Check phrases (higher weight)
            for phrase in patterns["phrases"]:
                if phrase in query_lower:
                    score += 2
                    matches.append(phrase)
            
            # Normalize score
            total_patterns = len(patterns["keywords"]) + len(patterns["phrases"])
            normalized_score = score / total_patterns if total_patterns > 0 else 0
            
            type_scores[query_type] = {
                "score": normalized_score,
                "matches": matches
            }
        
        # Determine best match
        best_type = max(type_scores.keys(), key=lambda k: type_scores[k]["score"])
        best_score = type_scores[best_type]["score"]
        
        # If no good matches, default to destination_recommendations
        if best_score == 0:
            best_type = "destination_recommendations"
            best_score = 0.1  # Low confidence default
        
        # Check if external data is needed
        external_data_needed = False
        external_data_reason = "Pattern matching suggests no external data needed"
        
        # Weather API indicators
        weather_matches = sum(1 for pattern in self.external_data_patterns["weather_needed"] 
                            if pattern in query_lower)
        
        # Location-specific data indicators  
        location_matches = sum(1 for pattern in self.external_data_patterns["location_specific"]
                             if pattern in query_lower)
        
        if weather_matches > 0 and best_type == "packing_suggestions":
            external_data_needed = True
            external_data_reason = "Packing query detected with weather-related terms"
        elif location_matches > 0 and best_type == "local_attractions":
            external_data_needed = True
            external_data_reason = "Attractions query detected with location-specific terms"
        
        result = {
            "type": best_type,
            "external_data_needed": external_data_needed,
            "external_data_reason": external_data_reason,
            "confidence": best_score,
            "all_scores": type_scores,
            "reasoning": f"Pattern matching: {type_scores[best_type]['matches']}"
        }
        
        logger.info(f"Pattern classification: {best_type} (confidence: {best_score:.2f})")
        return result
    
    def combine_classifications(self, gemini_result: Dict[str, Any], 
                              pattern_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine Gemini LLM and pattern matching results using confidence scoring.
        Implements intelligent fallback and decision logic.
        
        Args:
            gemini_result: Result from Gemini classification
            pattern_result: Result from pattern matching
            
        Returns:
            Final classification with confidence scoring
        """
        
        # Confidence weights
        GEMINI_WEIGHT = 0.8  # LLM is primary
        PATTERN_WEIGHT = 0.2  # Pattern matching is backup
        
        # Agreement bonus
        AGREEMENT_BONUS = 0.3
        
        final_result = {
            "type": None,
            "external_data_needed": False,
            "external_data_type": "none",
            "key_information": {},
            "confidence_score": 0.0,
            "primary_source": None,
            "reasoning": "",
            "fallback_used": False
        }
        
        try:
            # Check if both methods agree on type
            types_agree = gemini_result["type"] == pattern_result["type"]
            
            # Calculate confidence scores
            gemini_confidence = GEMINI_WEIGHT
            pattern_confidence = PATTERN_WEIGHT * pattern_result["confidence"]
            
            if types_agree:
                # Both methods agree - high confidence
                final_result["type"] = gemini_result["type"]
                final_result["confidence_score"] = gemini_confidence + pattern_confidence + AGREEMENT_BONUS
                final_result["primary_source"] = "consensus"
                final_result["reasoning"] = f"Both LLM and patterns agree on {gemini_result['type']}"
                
            elif gemini_confidence > pattern_confidence:
                # Trust LLM more
                final_result["type"] = gemini_result["type"]
                final_result["confidence_score"] = gemini_confidence
                final_result["primary_source"] = "llm"
                final_result["reasoning"] = f"LLM classification preferred: {gemini_result['type']}"
                
            else:
                # Pattern matching has higher confidence
                final_result["type"] = pattern_result["type"]
                final_result["confidence_score"] = pattern_confidence
                final_result["primary_source"] = "patterns"
                final_result["reasoning"] = f"Pattern matching preferred: {pattern_result['type']}"
            
            # External data decision - use LLM if available, otherwise patterns
            if "external_data_needed" in gemini_result:
                final_result["external_data_needed"] = gemini_result["external_data_needed"]
                final_result["external_data_reason"] = gemini_result.get("external_data_reason", "LLM recommendation")
                final_result["external_data_type"] = gemini_result.get("external_data_type", "none")
            else:
                final_result["external_data_needed"] = pattern_result["external_data_needed"]
                final_result["external_data_reason"] = pattern_result["external_data_reason"]
                final_result["external_data_type"] = "none"
            
            # Key information - only LLM can extract this
            final_result["key_information"] = gemini_result.get("key_information", {})
            
            logger.info(f"Combined classification: {final_result['type']} (confidence: {final_result['confidence_score']:.2f})")
            
        except Exception as e:
            logger.error(f"Error combining classifications: {str(e)}")
            # Emergency fallback
            final_result = {
                "type": "destination_recommendations",  # Safe default
                "external_data_needed": False,
                "key_information": {},
                "confidence_score": 0.1,
                "primary_source": "fallback",
                "reasoning": "Error in classification - using safe default",
                "fallback_used": True,
                "error": str(e)
            }
        
        return final_result
    
    def classify_query(self, query: str) -> Dict[str, Any]:
        """
        Main classification method that orchestrates the entire process.
        
        Args:
            query: User's travel query
            
        Returns:
            Complete classification result with type, external data needs, and key info
        """
        logger.info(f"Classifying query: {query[:50]}...")
        
        # Step 1: Try Gemini classification
        gemini_result = None
        try:
            gemini_result = self.classify_with_gemini(query)
        except Exception as e:
            logger.error(f"Gemini classification failed: {str(e)}")
        
        # Step 2: Always do pattern matching (backup + validation)
        pattern_result = self.classify_with_patterns(query)
        
        # Step 3: Combine results or use fallback
        if gemini_result:
            final_result = self.combine_classifications(gemini_result, pattern_result)
        else:
            # LLM failed - use pattern matching only
            logger.warning("Using pattern matching fallback due to LLM failure")
            final_result = {
                "type": pattern_result["type"],
                "external_data_needed": pattern_result["external_data_needed"],
                "external_data_type": "none",
                "key_information": {},  # No key info without LLM
                "confidence_score": pattern_result["confidence"],
                "primary_source": "patterns_fallback",
                "reasoning": "LLM failed - using pattern matching only",
                "fallback_used": True
            }
        
        # Add metadata
        final_result["timestamp"] = datetime.utcnow().isoformat()
        final_result["query"] = query
        
        logger.info(f"Final classification: {final_result}")
        return final_result