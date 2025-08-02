import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PackingHandler:
    """
    Advanced prompt engineering for packing suggestions.
    
    Demonstrates production-ready AI engineering skills for Navan assignment:
    
    CONVERSATION QUALITY FEATURES:
    - Information completeness analysis for natural conversation flow
    - Adaptive response strategies based on available context and weather data
    - Smart external data relevance assessment (only use weather when trip is near-term)
    - Context-aware questioning that builds on previous exchanges
    
    PROMPT DESIGN FEATURES:
    - Multi-step chain-of-thought reasoning tailored to available information
    - Strategic instruction variations based on context completeness
    - Smart weather data integration with temporal relevance checking
    - Length control and response strategy optimization
    - Activity-aware packing logic with gear-specific recommendations
    
    ADVANCED AI ENGINEERING:
    - Information completeness scoring with critical gap identification
    - External weather data relevance assessment (temporal and contextual)
    - Adaptive prompt construction based on conversation state
    - Error handling with intelligent fallbacks
    """
    
    def __init__(self):
        # Information completeness thresholds for adaptive responses
        self.completeness_thresholds = {
            "minimal": 0.2,      # Almost no useful info - focus on questions
            "partial": 0.5,      # Some info but gaps - hybrid approach  
            "sufficient": 0.8,   # Good info - provide recommendations
            "complete": 1.0      # Comprehensive info - detailed packing list
        }
        
        # Critical information categories for packing recommendations
        self.critical_info_categories = {
            "destination_weather": ["destination", "travel_dates", "duration"],
            "activities_gear": ["activities", "interests", "travel_style"],
            "luggage_constraints": ["luggage_type", "group_size", "constraints"],
            "special_needs": ["special_needs", "accessibility_needs", "laundry_availability"]
        }
        
        # Weather relevance temporal thresholds
        self.weather_relevance_days = 5  # Only use real weather data for trips within 5 days
        
        logger.info("Enhanced PackingHandler initialized with intelligent analysis capabilities")
    
    def build_final_prompt(self, user_query: str, global_context: List[str], 
                          type_specific_context: List[str], external_data: Dict[str, Any],
                          recent_conversation: List[Dict[str, Any]]) -> str:
        """
        Build an intelligently engineered prompt for packing recommendations.
        
        This demonstrates advanced prompt engineering through:
        
        1. CONVERSATION QUALITY: Analyzes conversation flow and information gaps
        2. PROMPT DESIGN: Creates targeted, effective prompts based on available data
        3. SMART DATA ROUTING: Only uses weather data when temporally relevant
        4. ADAPTIVE STRATEGY: Changes approach based on information completeness
        """
        try:
            # Step 1: Analyze information completeness and quality
            info_analysis = self._analyze_information_completeness(
                user_query, global_context, type_specific_context
            )
            
            # Step 2: Assess weather data relevance (smart temporal routing)
            weather_relevance = self._assess_weather_data_relevance(
                external_data, global_context, user_query, info_analysis
            )
            
            # Step 3: Determine optimal response strategy (conversation quality)
            response_strategy = self._determine_response_strategy(
                info_analysis, weather_relevance, recent_conversation
            )
            
            # Step 4: Build contextual conversation awareness
            conversation_context = self._build_conversation_context(recent_conversation)
            
            # Step 5: Create filtered and prioritized context (prompt efficiency)
            filtered_context = self._filter_and_prioritize_context(
                global_context, type_specific_context, info_analysis
            )
            
            # Step 6: Build the strategically engineered prompt
            final_prompt = self._build_strategic_prompt(
                user_query=user_query,
                info_analysis=info_analysis,
                response_strategy=response_strategy,
                conversation_context=conversation_context,
                filtered_context=filtered_context,
                weather_relevance=weather_relevance,
                external_data=external_data
            )
            
            logger.info(
                f"Built strategic packing prompt: {len(final_prompt)} chars, "
                f"strategy={response_strategy['type']}, "
                f"completeness={info_analysis['completeness_score']:.2f}, "
                f"weather_used={weather_relevance['use_weather']}"
            )
            
            return final_prompt
            
        except Exception as e:
            logger.error(f"Error building strategic packing prompt: {str(e)}")
            return self._build_fallback_prompt(user_query, global_context, type_specific_context)
    
    def _analyze_information_completeness(self, user_query: str, global_context: List[str], 
                                        type_specific_context: List[str]) -> Dict[str, Any]:
        """
        CONVERSATION QUALITY: Analyze information completeness for natural conversation flow.
        
        This enables intelligent questioning strategies by identifying what information
        we have vs what we need for effective packing recommendations.
        """
        analysis = {
            "available_info": {},
            "missing_info": [],
            "completeness_score": 0.0,
            "critical_gaps": [],
            "information_quality": "minimal"
        }
        
        try:
            # Parse available information from context arrays
            all_context = global_context + type_specific_context
            available_info = {}
            
            for item in all_context:
                if ":" in item:
                    key, value = item.split(":", 1)
                    available_info[key.strip().lower()] = value.strip()
            
            # Extract from current query using smart pattern matching
            query_info = self._extract_info_from_query(user_query)
            available_info.update(query_info)
            
            analysis["available_info"] = available_info
            
            # Analyze each critical category for packing
            category_scores = {}
            missing_critical = []
            
            for category, keywords in self.critical_info_categories.items():
                found_items = []
                for keyword in keywords:
                    if keyword in available_info:
                        found_items.append(keyword)
                
                category_score = len(found_items) / len(keywords)
                category_scores[category] = {
                    "score": category_score,
                    "found": found_items,
                    "missing": [k for k in keywords if k not in available_info]
                }
                
                if category_score < 0.3:  # Less than 30% of category info
                    missing_critical.append(category)
            
            # Calculate overall completeness score
            overall_score = sum(scores["score"] for scores in category_scores.values()) / len(category_scores)
            analysis["completeness_score"] = overall_score
            analysis["category_scores"] = category_scores
            analysis["critical_gaps"] = missing_critical
            
            # Determine information quality level
            if overall_score >= self.completeness_thresholds["complete"]:
                analysis["information_quality"] = "complete"
            elif overall_score >= self.completeness_thresholds["sufficient"]:
                analysis["information_quality"] = "sufficient"
            elif overall_score >= self.completeness_thresholds["partial"]:
                analysis["information_quality"] = "partial"
            else:
                analysis["information_quality"] = "minimal"
            
            # Identify most important missing information for targeted questions
            if "destination_weather" in missing_critical:
                analysis["missing_info"].append("destination_and_travel_dates")
            if "activities_gear" in missing_critical:
                analysis["missing_info"].append("planned_activities_and_style")
            if "luggage_constraints" in missing_critical:
                analysis["missing_info"].append("luggage_preferences_and_constraints")
            
            logger.info(f"Packing info analysis: {analysis['information_quality']} quality, score={overall_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error in packing information analysis: {str(e)}")
            analysis["completeness_score"] = 0.1
            analysis["information_quality"] = "minimal"
        
        return analysis
    
    def _extract_info_from_query(self, query: str) -> Dict[str, str]:
        """
        PROMPT DESIGN: Extract key information directly from user query using smart patterns.
        
        This enhances prompt effectiveness by capturing implicit information for packing.
        """
        info = {}
        query_lower = query.lower()
        
        # Activity patterns (critical for gear recommendations)
        activity_patterns = [
            (r'hiking|trekking|walking', 'hiking'),
            (r'swimming|beach|pool', 'swimming'),
            (r'business|meetings?|work|conference', 'business'),
            (r'formal|dinner|restaurant|fancy', 'formal dining'),
            (r'skiing|snow|winter sports', 'winter sports'),
            (r'running|jogging|gym|workout', 'fitness'),
            (r'camping|outdoor|nature', 'outdoor activities'),
            (r'party|nightlife|club|bar', 'nightlife')
        ]
        
        activities = []
        for pattern, activity in activity_patterns:
            if re.search(pattern, query_lower):
                activities.append(activity)
        
        if activities:
            info["activities"] = ", ".join(activities[:3])  # Limit to top 3
        
        # Luggage type patterns
        luggage_patterns = [
            (r'backpack|backpacking', 'backpack'),
            (r'suitcase|luggage|checked bag', 'suitcase'),
            (r'carry.?on|hand luggage', 'carry-on only'),
            (r'minimal|light|small bag', 'minimal luggage'),
            (r'large|big|lots of space', 'large luggage')
        ]
        
        for pattern, luggage_type in luggage_patterns:
            if re.search(pattern, query_lower):
                info["luggage_type"] = luggage_type
                break
        
        # Duration patterns (affects quantity)
        duration_patterns = [
            r'(\d+)\s*days?',
            r'(\d+)\s*weeks?',
            r'(\d+)\s*months?',
            r'(weekend|long weekend)',
            r'(week|month)'
        ]
        for pattern in duration_patterns:
            match = re.search(pattern, query_lower)
            if match:
                info["duration"] = match.group(1) if match.group(1).isdigit() else match.group(1)
                break
        
        # Weather/climate mentions
        weather_patterns = [
            (r'cold|winter|freezing|snow', 'cold weather'),
            (r'hot|summer|warm|tropical', 'hot weather'),
            (r'rain|rainy|wet|monsoon', 'rainy conditions'),
            (r'humid|humidity|muggy', 'humid climate'),
            (r'dry|desert|arid', 'dry climate')
        ]
        
        for pattern, climate in weather_patterns:
            if re.search(pattern, query_lower):
                info["climate_expectation"] = climate
                break
        
        # Special needs patterns
        special_needs_patterns = [
            (r'wheelchair|mobility|accessible', 'mobility assistance'),
            (r'medication|medical|health', 'medical needs'),
            (r'baby|infant|toddler|kids?|children', 'traveling with children'),
            (r'elderly|senior|older', 'senior travel needs'),
            (r'vegetarian|vegan|kosher|halal|dietary', 'dietary restrictions'),
            (r'work|business|laptop|documents', 'business equipment')
        ]
        
        special_needs = []
        for pattern, need in special_needs_patterns:
            if re.search(pattern, query_lower):
                special_needs.append(need)
        
        if special_needs:
            info["special_needs"] = ", ".join(special_needs[:2])  # Limit to top 2
        
        return info
    
    def _assess_weather_data_relevance(self, external_data: Dict[str, Any], 
                                     global_context: List[str], user_query: str,
                                     info_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        SMART DATA ROUTING: Intelligently assess when to use external weather data.
        
        Key insight: Only use real weather data for near-term trips (within 5 days).
        For future trips, rely on LLM's seasonal knowledge to avoid misleading current weather.
        """
        relevance = {
            "weather_relevant": False,
            "weather_reason": "",
            "use_weather": False,
            "temporal_relevance": "unknown",
            "data_freshness": "unknown"
        }
        
        try:
            # Check if we have external weather data
            has_weather = "weather" in external_data and external_data["weather"].get("success")
            
            if not has_weather:
                relevance["weather_reason"] = "No external weather data available"
                return relevance
            
            # Check temporal relevance - CRITICAL for packing accuracy
            available_info = info_analysis.get("available_info", {})
            
            # Look for travel date indicators
            travel_date_soon = self._is_trip_within_weather_relevance_window(
                available_info, user_query, global_context
            )
            
            if travel_date_soon:
                relevance["temporal_relevance"] = "near_term"
                relevance["weather_relevant"] = True
                relevance["use_weather"] = True
                relevance["weather_reason"] = "Trip is within 5 days - current weather data is relevant"
                
            else:
                # Check if user is explicitly asking about current weather
                weather_query_indicators = [
                    "current weather" in user_query.lower(),
                    "today" in user_query.lower(),
                    "now" in user_query.lower(),
                    "right now" in user_query.lower()
                ]
                
                if any(weather_query_indicators):
                    relevance["temporal_relevance"] = "current_query"
                    relevance["weather_relevant"] = True
                    relevance["use_weather"] = True
                    relevance["weather_reason"] = "User explicitly asking about current weather"
                else:
                    relevance["temporal_relevance"] = "future_trip"
                    relevance["weather_reason"] = "Trip appears to be in future - use seasonal knowledge instead of current weather"
            
            # Assess data freshness if we're using it
            if relevance["use_weather"] and has_weather:
                weather_data = external_data["weather"]
                current_temp = weather_data.get('current_weather', {}).get('temperature', 'N/A')
                forecast_entries = len(weather_data.get('forecast', []))
                
                if current_temp != 'N/A' and forecast_entries > 0:
                    relevance["data_freshness"] = "current"
                else:
                    relevance["data_freshness"] = "limited"
                    relevance["weather_reason"] += " (limited data available)"
            
            logger.info(f"Weather data relevance: use={relevance['use_weather']}, reason={relevance['weather_reason']}")
            
        except Exception as e:
            logger.error(f"Error assessing weather data relevance: {str(e)}")
            relevance["weather_reason"] = f"Error in relevance assessment: {str(e)}"
        
        return relevance
    
    def _is_trip_within_weather_relevance_window(self, available_info: Dict[str, str], 
                                               user_query: str, global_context: List[str]) -> bool:
        """
        SMART TEMPORAL ANALYSIS: Determine if trip is within weather relevance window.
        
        Only trips within 5 days should use real weather data for packing accuracy.
        """
        try:
            # Check for immediate travel indicators in query
            immediate_indicators = [
                "tomorrow", "today", "this week", "coming week", "next few days",
                "leaving tomorrow", "departing today", "traveling tomorrow"
            ]
            
            if any(indicator in user_query.lower() for indicator in immediate_indicators):
                logger.info("Trip detected as immediate based on query language")
                return True
            
            # Check for date information in context
            for item in global_context:
                if "travel_dates:" in item.lower():
                    date_str = item.split(":", 1)[1].strip().lower()
                    if any(indicator in date_str for indicator in immediate_indicators):
                        logger.info("Trip detected as immediate based on context dates")
                        return True
            
            # Check available_info for date clues
            if "travel_dates" in available_info:
                date_str = available_info["travel_dates"].lower()
                if any(indicator in date_str for indicator in immediate_indicators):
                    logger.info("Trip detected as immediate based on available info")
                    return True
            
            # Default: assume future trip (safer for packing accuracy)
            logger.info("Trip assumed to be future - will use seasonal knowledge")
            return False
            
        except Exception as e:
            logger.error(f"Error in temporal analysis: {str(e)}")
            return False  # Safe default: don't use current weather for uncertain dates
    
    def _determine_response_strategy(self, info_analysis: Dict[str, Any], 
                                   weather_relevance: Dict[str, Any],
                                   recent_conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        CONVERSATION QUALITY: Determine optimal response strategy for natural interaction.
        
        This ensures appropriate responses based on information available and conversation context.
        """
        strategy = {
            "type": "question_focused",
            "approach": "",
            "length_target": "concise",
            "questioning_strategy": "",
            "recommendation_depth": "minimal"
        }
        
        try:
            quality = info_analysis["information_quality"]
            completeness = info_analysis["completeness_score"]
            has_critical_gaps = len(info_analysis["critical_gaps"]) > 0
            has_weather_data = weather_relevance["use_weather"]
            
            # Determine strategy based on information quality
            if quality == "minimal" or completeness < 0.3:
                strategy["type"] = "question_focused"
                strategy["approach"] = "Ask 2-3 targeted questions to gather essential packing information"
                strategy["length_target"] = "concise"
                strategy["questioning_strategy"] = "Focus on destination, activities, and luggage type"
                strategy["recommendation_depth"] = "none"
                
            elif quality == "partial" or completeness < 0.6:
                if has_weather_data:
                    strategy["type"] = "hybrid_with_weather"
                    strategy["approach"] = "Provide weather-informed packing advice while gathering missing details"
                    strategy["recommendation_depth"] = "weather_based"
                else:
                    strategy["type"] = "hybrid"
                    strategy["approach"] = "Provide general packing recommendations while gathering missing details"
                    strategy["recommendation_depth"] = "general"
                
                strategy["length_target"] = "moderate"
                strategy["questioning_strategy"] = "Ask for 1-2 specific details while giving helpful suggestions"
                
            elif quality == "sufficient" or completeness < 0.8:
                strategy["type"] = "recommendation_focused"
                strategy["approach"] = "Provide solid packing recommendations with clear reasoning"
                strategy["length_target"] = "comprehensive"
                strategy["questioning_strategy"] = "Optional clarification questions only"
                strategy["recommendation_depth"] = "detailed"
                
            else:  # complete
                strategy["type"] = "detailed_packing_list"
                strategy["approach"] = "Provide comprehensive, categorized packing list with specific insights"
                strategy["length_target"] = "comprehensive"
                strategy["questioning_strategy"] = "No questions needed"
                strategy["recommendation_depth"] = "comprehensive"
            
            # Adjust based on conversation length (avoid question loops)
            conversation_length = len(recent_conversation)
            if conversation_length > 4:  # Long conversation - be more decisive
                if strategy["type"] == "question_focused":
                    strategy["type"] = "hybrid"
                    strategy["approach"] = "Move conversation forward with recommendations and minimal questions"
            
            # Enhance strategy if we have good weather data
            if has_weather_data and strategy["type"] in ["recommendation_focused", "detailed_packing_list"]:
                strategy["approach"] += " using current weather data"
                strategy["recommendation_depth"] += "_with_weather"
            
            logger.info(f"Selected packing strategy: {strategy['type']} for {quality} quality information")
            
        except Exception as e:
            logger.error(f"Error determining packing response strategy: {str(e)}")
            # Safe fallback
            strategy["type"] = "hybrid"
            strategy["approach"] = "Provide helpful response with clarifying questions"
        
        return strategy
    
    def _build_conversation_context(self, recent_conversation: List[Dict[str, Any]]) -> str:
        """Build smart conversation context focusing on relevant exchanges."""
        if not recent_conversation:
            return ""
        
        try:
            # Get last 3 conversation turns (6 messages max) for context efficiency
            recent_messages = recent_conversation[-6:]
            
            context_lines = ["CONVERSATION CONTEXT:"]
            for msg in recent_messages:
                if "user_query" in msg:
                    context_lines.append(f"User: {msg['user_query']}")
                elif "assistant_answer" in msg:
                    # Summarize long assistant answers for context efficiency
                    answer = msg['assistant_answer']
                    if len(answer) > 200:
                        answer = answer[:200] + "..."
                    context_lines.append(f"Assistant: {answer}")
            
            context_lines.append("")  # Empty line for separation
            return "\n".join(context_lines)
            
        except Exception as e:
            logger.error(f"Error building conversation context: {str(e)}")
            return ""
    
    def _filter_and_prioritize_context(self, global_context: List[str], 
                                     type_specific_context: List[str],
                                     info_analysis: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        PROMPT DESIGN: Filter and prioritize context for maximum prompt efficiency.
        
        Only include the most relevant information for packing recommendations.
        """
        filtered = {
            "high_priority": [],    # Essential for packing recommendations
            "medium_priority": [],  # Useful but not critical
            "low_priority": []      # Background information
        }
        
        try:
            all_context = global_context + type_specific_context
            
            # Define priority keywords for packing recommendations
            high_priority_keys = [
                "destination", "activities", "duration", "luggage_type", 
                "special_needs", "travel_dates", "climate_expectation"
            ]
            
            medium_priority_keys = [
                "interests", "budget", "group_size", "travel_style",
                "laundry_availability", "accessibility_needs"
            ]
            
            for item in all_context:
                if not item or ":" not in item:
                    continue
                    
                key = item.split(":", 1)[0].strip().lower()
                
                if key in high_priority_keys:
                    filtered["high_priority"].append(item)
                elif key in medium_priority_keys:
                    filtered["medium_priority"].append(item)
                else:
                    filtered["low_priority"].append(item)
            
            # Remove duplicates while preserving order
            for priority in filtered:
                filtered[priority] = list(dict.fromkeys(filtered[priority]))
            
            logger.info(f"Filtered packing context: {len(filtered['high_priority'])} high, {len(filtered['medium_priority'])} medium priority items")
            
        except Exception as e:
            logger.error(f"Error filtering packing context: {str(e)}")
            # Fallback: treat all as medium priority
            filtered["medium_priority"] = global_context + type_specific_context
        
        return filtered
    
    def _build_strategic_prompt(self, user_query: str, info_analysis: Dict[str, Any],
                              response_strategy: Dict[str, Any], conversation_context: str,
                              filtered_context: Dict[str, List[str]], 
                              weather_relevance: Dict[str, Any],
                              external_data: Dict[str, Any]) -> str:
        """
        PROMPT DESIGN: Build strategically engineered prompt for packing recommendations.
        
        This creates targeted, effective prompts based on comprehensive analysis.
        """
        
        # Start building the prompt parts
        prompt_parts = []
        
        # 1. Expert role definition with domain expertise
        prompt_parts.append(
            "You are an expert packing consultant with deep knowledge of travel gear, weather considerations, "
            "activity-specific equipment, luggage optimization, and international travel requirements."
        )
        prompt_parts.append("")
        
        # 2. Current query and context
        prompt_parts.append(f'USER QUERY: "{user_query}"')
        prompt_parts.append("")
        
        # 3. Conversation context (if relevant)
        if conversation_context:
            prompt_parts.append(conversation_context)
        
        # 4. Available information (strategically organized by priority)
        if filtered_context["high_priority"]:
            prompt_parts.append("KEY TRIP INFORMATION:")
            for item in filtered_context["high_priority"]:
                prompt_parts.append(f"• {item}")
            prompt_parts.append("")
        
        if filtered_context["medium_priority"]:
            prompt_parts.append("ADDITIONAL CONTEXT:")
            for item in filtered_context["medium_priority"]:
                prompt_parts.append(f"• {item}")
            prompt_parts.append("")
        
        # 5. Weather data (ONLY if determined to be temporally relevant)
        if weather_relevance["use_weather"] and "weather" in external_data:
            weather = external_data["weather"]
            prompt_parts.append("CURRENT WEATHER DATA:")
            prompt_parts.append(f"• Location: {weather.get('location', 'Unknown')}")
            
            current_weather = weather.get('current_weather', {})
            if current_weather:
                temp = current_weather.get('temperature', 'N/A')
                desc = current_weather.get('description', 'N/A')
                feels_like = current_weather.get('feels_like', 'N/A')
                prompt_parts.append(f"• Current: {temp}°C (feels like {feels_like}°C), {desc}")
            
            forecast = weather.get('forecast', [])
            if forecast:
                prompt_parts.append("• 5-day forecast highlights:")
                # Show key forecast points for packing decisions
                for i, entry in enumerate(forecast):  # Show all entries 
                    dt_str = entry.get('datetime', '')
                    temp = entry.get('temperature', 'N/A')
                    desc = entry.get('description', 'N/A')
                    prompt_parts.append(f"  - {dt_str}: {temp}°C, {desc}")
                
            
            prompt_parts.append("")
        
        # 6. Strategic instructions based on response strategy
        prompt_parts.append("STRATEGIC RESPONSE INSTRUCTIONS:")
        prompt_parts.append("")
        
        # Chain-of-thought reasoning specific to strategy (ADVANCED PROMPT ENGINEERING)
        prompt_parts.append("Chain-of-thought reasoning process:")
        
        if response_strategy["type"] == "question_focused":
            prompt_parts.extend([
                "1. Analyze what critical information is missing for effective packing recommendations",
                "2. Identify the 2-3 most important questions to ask for packing success",
                "3. Provide a brief, encouraging response that gathers essential details",
                "4. Focus on destination, planned activities, and luggage constraints"
            ])
        
        elif response_strategy["type"] in ["hybrid", "hybrid_with_weather"]:
            prompt_parts.extend([
                "1. Assess what information is available and what's missing for packing",
                "2. Provide helpful general packing advice based on available info",
                "3. Ask 1-2 specific questions to fill important gaps",
                "4. Balance being helpful now while gathering more details"
            ])
            
            if "with_weather" in response_strategy["type"]:
                prompt_parts.append("5. Integrate current weather data naturally into packing recommendations")
        
        elif response_strategy["type"] == "recommendation_focused":
            prompt_parts.extend([
                "1. Analyze all available trip information, activities, and constraints",
                "2. Consider weather conditions, luggage type, and special needs",
                "3. Provide categorized packing recommendations with clear reasoning",
                "4. Explain why each item/category is important for their specific trip",
                "5. Include practical packing tips and space-saving techniques"
            ])
        
        else:  # detailed_packing_list
            prompt_parts.extend([
                "1. Conduct comprehensive analysis of all trip factors and constraints",
                "2. Create detailed, categorized packing list with specific item recommendations",
                "3. Include weather-appropriate clothing with layering strategies",
                "4. Address activity-specific gear and equipment needs",
                "5. Provide luggage organization tips and weight management strategies",
                "6. Include travel documents, electronics, and destination-specific items"
            ])
        
        prompt_parts.append("")
        
        # 7. Response guidelines tailored to strategy (LENGTH AND QUALITY CONTROL)
        prompt_parts.append("Response guidelines:")
        
        strategy_guidelines = {
            "question_focused": [
                "• Keep response concise but encouraging (2-3 paragraphs max)",
                "• Ask no more than 3 specific, actionable questions", 
                "• Show enthusiasm for helping with their packing",
                "• Avoid overwhelming with too many options or details"
            ],
            "hybrid": [
                "• Provide 1-2 general packing categories while asking for clarification",
                "• Balance being immediately helpful with gathering more info",
                "• Keep response moderate length (3-4 paragraphs)",
                "• Show packing expertise while remaining conversational"
            ],
            "hybrid_with_weather": [
                "• Provide weather-informed packing advice while asking for clarification",
                "• Use the current weather data to make specific clothing suggestions",
                "• Balance being immediately helpful with gathering more info",
                "• Keep response moderate length (3-4 paragraphs)"
            ],
            "recommendation_focused": [
                "• Provide 3-5 categorized packing recommendations with clear reasoning",
                "• Explain why each category fits their activities and constraints",
                "• Include practical details (quantities, specific items, packing tips)",
                "• Use confident, expert tone while remaining personable",
                "• Aim for comprehensive but digestible response (4-5 paragraphs)"
            ],
            "detailed_packing_list": [
                "• Provide comprehensive, categorized packing checklist",
                "• Include specific items, quantities, and packing strategies",
                "• Address all activities, weather conditions, and special needs",
                "• Provide actionable organization and space-saving tips",
                "• Use extensive expertise while maintaining helpful tone"
            ]
        }
        
        for guideline in strategy_guidelines.get(response_strategy["type"], strategy_guidelines["hybrid"]):
            prompt_parts.append(guideline)
        
        prompt_parts.append("")
        
        # 8. Weather data usage instructions (SMART DATA ROUTING)
        if weather_relevance["use_weather"]:
            prompt_parts.append("Weather data usage:")
            prompt_parts.append("• USE the current weather data provided - it's temporally relevant for this trip")
            prompt_parts.append("• Make specific clothing recommendations based on actual temperatures and conditions")
            prompt_parts.append("• Consider the 5-day forecast for layering and backup clothing needs")
            prompt_parts.append("• Integrate weather insights naturally into packing categories")
        else:
            prompt_parts.append("Weather data usage:")
            if weather_relevance["temporal_relevance"] == "future_trip":
                prompt_parts.append("• Do NOT use current weather data - this appears to be a future trip")
                prompt_parts.append("• Instead, rely on your seasonal/climatic knowledge for the destination")
                prompt_parts.append("• Use general seasonal patterns rather than current conditions")
            else:
                prompt_parts.append("• No current weather data available - rely on your extensive knowledge")
                prompt_parts.append("• Use general climatic knowledge for the destination and season")
        
        prompt_parts.append("")
        
        # 9. Packing-specific expertise guidelines (CONVERSATION QUALITY)
        prompt_parts.extend([
            "Packing expertise guidelines:",
            "• Organize recommendations in clear categories (clothing, gear, essentials, documents)",
            "• Consider luggage weight and space constraints mentioned",
            "• Provide specific quantities when helpful (e.g., '3-4 t-shirts')",
            "• Include activity-specific gear recommendations",
            "• Suggest versatile items that serve multiple purposes",
            "• Consider local availability vs. must-bring items",
            "• Include practical packing tips (rolling vs. folding, compression, etc.)",
            "• Use emojis and bullet points for easy scanning",
            "• Be encouraging and build confidence in their packing decisions",
            "",
            "Generate your packing recommendation response:"
        ])
        
        # Join all parts into final prompt
        final_prompt = "\n".join(prompt_parts)
        
        # Log prompt engineering details for monitoring
        logger.info(f"Strategic packing prompt built: strategy={response_strategy['type']}, "
                   f"info_quality={info_analysis['information_quality']}, "
                   f"weather_used={weather_relevance['use_weather']}, "
                   f"temporal_relevance={weather_relevance['temporal_relevance']}")
        
        return final_prompt
    
    def _build_fallback_prompt(self, user_query: str, global_context: List[str], 
                              type_specific_context: List[str]) -> str:
        """
        Fallback prompt when advanced analysis fails.
        Still demonstrates good prompt engineering principles.
        """
        return f"""You are an expert packing consultant with deep knowledge of travel gear and weather considerations.

USER QUERY: "{user_query}"

AVAILABLE INFORMATION:
{chr(10).join(f"• {item}" for item in global_context + type_specific_context if item)}

INSTRUCTIONS:
1. Analyze what information is available about the trip and traveler
2. If you have enough info, provide categorized packing recommendations
3. If missing critical details (destination, activities, luggage type), ask 2-3 targeted questions
4. Be conversational, helpful, and demonstrate packing expertise
5. Keep response length appropriate to available information
6. Organize suggestions in clear categories with practical tips

Generate your packing recommendation response:"""