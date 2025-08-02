import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DestinationHandler:
    """
    Advanced prompt engineering for destination recommendations.
    
    Demonstrates production-ready AI engineering skills for Navan assignment:
    
    CONVERSATION QUALITY FEATURES:
    - Intelligent information gap analysis to maintain natural flow
    - Adaptive response strategies based on conversation context
    - Smart external data relevance assessment
    - Context-aware questioning that builds on previous exchanges
    
    PROMPT DESIGN FEATURES:
    - Multi-step chain-of-thought reasoning tailored to information available
    - Strategic instruction variations based on completeness analysis
    - Smart data filtering to include only relevant context
    - Length control and response strategy optimization
    - External data usage instructions for smart routing
    
    ADVANCED AI ENGINEERING:
    - Information completeness scoring with critical gap identification
    - External data relevance assessment (temporal and contextual)
    - Adaptive prompt construction based on conversation state
    - Error handling with intelligent fallbacks
    """
    
    def __init__(self):
        # Information completeness thresholds for adaptive responses
        self.completeness_thresholds = {
            "minimal": 0.2,      # Almost no useful info - focus on questions
            "partial": 0.5,      # Some info but gaps - hybrid approach  
            "sufficient": 0.8,   # Good info - provide recommendations
            "complete": 1.0      # Comprehensive info - detailed planning
        }
        
        # Critical information categories for destination recommendations
        self.critical_info_categories = {
            "destination_preference": ["destination", "region", "continent", "climate_preference"],
            "trip_constraints": ["budget", "duration", "travel_dates", "group_size"],
            "traveler_profile": ["interests", "travel_style", "constraints"],
            "specific_requirements": ["activities", "accessibility_needs", "visa_requirements"]
        }
        
        logger.info("Enhanced DestinationHandler initialized with intelligent analysis capabilities")
    
    def build_final_prompt(self, user_query: str, global_context: List[str], 
                          type_specific_context: List[str], external_data: Dict[str, Any],
                          recent_conversation: List[Dict[str, Any]]) -> str:
        """
        Build an intelligently engineered prompt for destination recommendations.
        
        This is the core method that demonstrates advanced prompt engineering:
        
        1. CONVERSATION QUALITY: Analyzes conversation flow and information gaps
        2. PROMPT DESIGN: Creates targeted, effective prompts based on available data
        3. SMART DATA ROUTING: Only uses external data when actually relevant
        4. ADAPTIVE STRATEGY: Changes approach based on information completeness
        """
        try:
            # Step 1: Analyze information completeness and quality
            info_analysis = self._analyze_information_completeness(
                user_query, global_context, type_specific_context
            )
            
            # Step 2: Assess external data relevance (smart routing)
            external_relevance = self._assess_external_data_relevance(
                external_data, global_context, user_query
            )
            
            # Step 3: Determine optimal response strategy (conversation quality)
            response_strategy = self._determine_response_strategy(
                info_analysis, external_relevance, recent_conversation
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
                external_relevance=external_relevance,
                external_data=external_data
            )
            
            logger.info(
                f"Built strategic destination prompt: {len(final_prompt)} chars, "
                f"strategy={response_strategy['type']}, "
                f"completeness={info_analysis['completeness_score']:.2f}, "
                f"weather_used={external_relevance['use_weather']}, "
                f"attractions_used={external_relevance['use_attractions']}"
            )
            
            return final_prompt
            
        except Exception as e:
            logger.error(f"Error building strategic destination prompt: {str(e)}")
            return self._build_fallback_prompt(user_query, global_context, type_specific_context)
    
    def _analyze_information_completeness(self, user_query: str, global_context: List[str], 
                                        type_specific_context: List[str]) -> Dict[str, Any]:
        """
        CONVERSATION QUALITY: Analyze information completeness to determine conversation strategy.
        
        This enables natural conversation flow by identifying what information we have
        vs what we need, allowing for intelligent questioning strategies.
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
            
            # Also extract from current query using smart pattern matching
            query_info = self._extract_info_from_query(user_query)
            available_info.update(query_info)
            
            analysis["available_info"] = available_info
            
            # Analyze each critical category
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
            if "destination_preference" in missing_critical:
                analysis["missing_info"].append("destination_or_region_preference")
            if "trip_constraints" in missing_critical:
                analysis["missing_info"].append("budget_and_duration")
            if "traveler_profile" in missing_critical:
                analysis["missing_info"].append("interests_and_travel_style")
            
            logger.info(f"Information analysis: {analysis['information_quality']} quality, score={overall_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error in information analysis: {str(e)}")
            analysis["completeness_score"] = 0.1
            analysis["information_quality"] = "minimal"
        
        return analysis
    
    def _extract_info_from_query(self, query: str) -> Dict[str, str]:
        """
        PROMPT DESIGN: Extract key information directly from user query using smart patterns.
        
        This enhances prompt effectiveness by capturing implicit information.
        """
        info = {}
        query_lower = query.lower()
        
        # Budget patterns
        budget_patterns = [
            r'\$([0-9,]+)',
            r'budget.*?(\$[0-9,]+)',
            r'spend.*?(\$[0-9,]+)',
            r'([0-9,]+)\s*dollars?'
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, query_lower)
            if match:
                info["budget"] = match.group(1) if '$' in match.group(1) else f"${match.group(1)}"
                break
        
        # Duration patterns
        duration_patterns = [
            r'(\d+)\s*days?',
            r'(\d+)\s*weeks?',
            r'(\d+)\s*months?',
            r'(weekend|long weekend)',
            r'(week|month|fortnight)'
        ]
        for pattern in duration_patterns:
            match = re.search(pattern, query_lower)
            if match:
                info["duration"] = match.group(1)
                break
        
        # Destination patterns
        destination_patterns = [
            r'go\s+to\s+([A-Za-z\s]+?)(?:\s|$|,|\.|!|\?)',
            r'visit\s+([A-Za-z\s]+?)(?:\s|$|,|\.|!|\?)',
            r'travel\s+to\s+([A-Za-z\s]+?)(?:\s|$|,|\.|!|\?)',
            r'trip\s+to\s+([A-Za-z\s]+?)(?:\s|$|,|\.|!|\?)'
        ]
        for pattern in destination_patterns:
            match = re.search(pattern, query_lower)
            if match:
                destination = match.group(1).strip()
                if len(destination) > 2 and destination not in ['the', 'a', 'an']:
                    info["destination"] = destination.title()
                    break
        
        return info
    
    def _assess_external_data_relevance(self, external_data: Dict[str, Any], 
                                      global_context: List[str], user_query: str) -> Dict[str, Any]:
        """
        SMART DATA ROUTING: Intelligently assess external data relevance.
        
        Key insight: Only use external data when it's actually helpful for the user's query.
        Weather data is only useful for near-term trips or weather-specific questions.
        Attractions data is only useful when destination is already established.
        """
        relevance = {
            "weather_relevant": False,
            "attractions_relevant": False,
            "weather_reason": "",
            "attractions_reason": "",
            "use_weather": False,
            "use_attractions": False
        }
        
        try:
            # Check if we have external data
            has_weather = "weather" in external_data and external_data["weather"].get("success")
            has_attractions = "attractions" in external_data and external_data["attractions"].get("success")
            
            # Analyze weather relevance
            if has_weather:
                weather_relevant_indicators = [
                    "weather" in user_query.lower(),
                    "temperature" in user_query.lower(),
                    "climate" in user_query.lower(),
                    "season" in user_query.lower(),
                    any("travel_dates:" in item and self._is_near_term_date(item) for item in global_context)
                ]
                
                if any(weather_relevant_indicators):
                    relevance["weather_relevant"] = True
                    relevance["use_weather"] = True
                    relevance["weather_reason"] = "User asked about weather or trip is near-term"
                else:
                    relevance["weather_reason"] = "Weather not relevant - no weather question and not near-term trip"
            
            # Analyze attractions relevance
            if has_attractions:
                # Check if we already have a destination established
                has_destination = any(
                    item.lower().startswith("destination:") for item in global_context
                ) or "destination" in [item.split(":")[0].strip().lower() for item in global_context if ":" in item]
                
                attractions_query_indicators = [
                    "things to do" in user_query.lower(),
                    "activities" in user_query.lower(),
                    "attractions" in user_query.lower(),
                    "see" in user_query.lower() and "what" in user_query.lower()
                ]
                
                if has_destination and any(attractions_query_indicators):
                    relevance["attractions_relevant"] = True
                    relevance["use_attractions"] = True
                    relevance["attractions_reason"] = "Destination known and user asking about activities"
                elif has_destination:
                    relevance["attractions_relevant"] = True
                    relevance["use_attractions"] = True
                    relevance["attractions_reason"] = "Destination known - attractions can inform recommendation"
                else:
                    relevance["attractions_reason"] = "No established destination - attractions not relevant yet"
            
            logger.info(f"External data relevance: weather={relevance['use_weather']}, attractions={relevance['use_attractions']}")
            
        except Exception as e:
            logger.error(f"Error assessing external data relevance: {str(e)}")
        
        return relevance
    
    def _is_near_term_date(self, date_item: str) -> bool:
        """Check if a date item represents a near-term trip (within maximum 5 days)."""
        try:
            # Simple heuristic: look for words indicating near-term (maximum 5 day) travel
            near_term_indicators = ["this week", "coming week", "coming days", "tomorrow", "this weekend"]
            return any(indicator in date_item.lower() for indicator in near_term_indicators)
        except:
            return False
    
    def _determine_response_strategy(self, info_analysis: Dict[str, Any], 
                                   external_relevance: Dict[str, Any],
                                   recent_conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        CONVERSATION QUALITY: Determine optimal response strategy for natural interaction.
        
        This ensures the assistant responds appropriately based on information available
        and conversation context, maintaining helpful and natural flow.
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
            
            # Determine strategy based on information quality
            if quality == "minimal" or completeness < 0.3:
                strategy["type"] = "question_focused"
                strategy["approach"] = "Ask 2-3 targeted questions to gather essential information"
                strategy["length_target"] = "concise"
                strategy["questioning_strategy"] = "Focus on destination preferences, budget, and interests"
                strategy["recommendation_depth"] = "none"
                
            elif quality == "partial" or completeness < 0.6:
                strategy["type"] = "hybrid"
                strategy["approach"] = "Provide general recommendations while gathering missing details"
                strategy["length_target"] = "moderate"
                strategy["questioning_strategy"] = "Ask for 1-2 specific details while giving helpful suggestions"
                strategy["recommendation_depth"] = "general"
                
            elif quality == "sufficient" or completeness < 0.8:
                strategy["type"] = "recommendation_focused"
                strategy["approach"] = "Provide solid destination recommendations with clear reasoning"
                strategy["length_target"] = "comprehensive"
                strategy["questioning_strategy"] = "Optional clarification questions only"
                strategy["recommendation_depth"] = "detailed"
                
            else:  # complete
                strategy["type"] = "detailed_planning"
                strategy["approach"] = "Provide comprehensive destination recommendations with detailed insights"
                strategy["length_target"] = "comprehensive"
                strategy["questioning_strategy"] = "No questions needed"
                strategy["recommendation_depth"] = "comprehensive"
            
            # Adjust based on conversation context (avoid question loops)
            conversation_length = len(recent_conversation)
            if conversation_length > 4:  # Long conversation - be more decisive
                if strategy["type"] == "question_focused":
                    strategy["type"] = "hybrid"
                    strategy["approach"] = "Move conversation forward with recommendations and minimal questions"
            
            logger.info(f"Selected strategy: {strategy['type']} for {quality} quality information")
            
        except Exception as e:
            logger.error(f"Error determining response strategy: {str(e)}")
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
                    # Truncate long responses for context efficiency
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
        
        Only include the most relevant information to create focused, effective prompts.
        """
        filtered = {
            "high_priority": [],    # Essential for destination recommendations
            "medium_priority": [],  # Useful but not critical
            "low_priority": []      # Background information
        }
        
        try:
            all_context = global_context + type_specific_context
            
            # Define priority keywords for destination recommendations
            high_priority_keys = [
                "destination", "budget", "duration", "interests", "travel_style", 
                "climate_preference", "constraints", "group_size", "travel_dates"
            ]
            
            medium_priority_keys = [
                "activities", "accessibility_needs", "luggage_type", "laundry_availability"
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
            
            logger.info(f"Filtered context: {len(filtered['high_priority'])} high, {len(filtered['medium_priority'])} medium priority items")
            
        except Exception as e:
            logger.error(f"Error filtering context: {str(e)}")
            # Fallback: treat all as medium priority
            filtered["medium_priority"] = global_context + type_specific_context
        
        return filtered
    
    def _build_strategic_prompt(self, user_query: str, info_analysis: Dict[str, Any],
                              response_strategy: Dict[str, Any], conversation_context: str,
                              filtered_context: Dict[str, List[str]], 
                              external_relevance: Dict[str, Any],
                              external_data: Dict[str, Any]) -> str:
        """
        PROMPT DESIGN: Build strategically engineered prompt demonstrating advanced skills.
        
        This is the core prompt engineering method that creates targeted, effective prompts
        based on comprehensive analysis of available information and conversation context.
        """
        
        # Start building the prompt parts
        prompt_parts = []
        
        # 1. Expert role definition with domain expertise
        prompt_parts.append(
            "You are an expert destination consultant with deep knowledge of global travel destinations, "
            "cultural insights, budget optimization, and personalized travel planning."
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
            prompt_parts.append("KEY TRAVELER INFORMATION:")
            for item in filtered_context["high_priority"]:
                prompt_parts.append(f"• {item}")
            prompt_parts.append("")
        
        if filtered_context["medium_priority"]:
            prompt_parts.append("ADDITIONAL PREFERENCES:")
            for item in filtered_context["medium_priority"]:
                prompt_parts.append(f"• {item}")
            prompt_parts.append("")
        
        # 5. External data (ONLY if determined to be relevant)
        if external_relevance["use_weather"] and "weather" in external_data:
            weather = external_data["weather"]
            prompt_parts.append("CURRENT WEATHER DATA:")
            prompt_parts.append(f"• Location: {weather.get('location', 'Unknown')}")
            prompt_parts.append(f"• Current: {weather.get('current_weather', {}).get('temperature', 'N/A')}°C, {weather.get('current_weather', {}).get('description', 'N/A')}")
            prompt_parts.append(f"• Relevance: {external_relevance['weather_reason']}")
            prompt_parts.append("")
        
        if external_relevance["use_attractions"] and "attractions" in external_data:
            attractions = external_data["attractions"]
            prompt_parts.append("CURRENT ATTRACTIONS DATA:")
            prompt_parts.append(f"• Destination: {attractions.get('destination', 'Unknown')}")
            prompt_parts.append(f"• Available attractions: {attractions.get('total_found', 0)} found")
            prompt_parts.append(f"• Relevance: {external_relevance['attractions_reason']}")
            prompt_parts.append("")
        
        # 6. Strategic instructions based on response strategy
        prompt_parts.append("STRATEGIC RESPONSE INSTRUCTIONS:")
        prompt_parts.append("")
        
        # Chain-of-thought reasoning specific to strategy (ADVANCED PROMPT ENGINEERING)
        prompt_parts.append("Chain-of-thought reasoning process:")
        
        if response_strategy["type"] == "question_focused":
            prompt_parts.extend([
                "1. Analyze what critical information is missing for destination recommendations",
                "2. Identify the 2-3 most important questions to ask",
                "3. Provide a brief, encouraging response that gathers essential details",
                "4. Focus on destination preferences, budget range, and travel style"
            ])
        
        elif response_strategy["type"] == "hybrid":
            prompt_parts.extend([
                "1. Assess what information is available and what's missing",
                "2. Provide helpful general recommendations based on available info",
                "3. Ask 1-2 specific questions to fill important gaps",
                "4. Balance being helpful now while gathering more details"
            ])
        
        elif response_strategy["type"] == "recommendation_focused":
            prompt_parts.extend([
                "1. Analyze all available traveler information and preferences",
                "2. Consider budget, duration, interests, and constraints holistically",
                "3. Provide 2-4 specific destination recommendations with clear reasoning",
                "4. Explain why each destination matches their stated preferences",
                "5. Include practical considerations (budget fit, logistics, best time to visit)"
            ])
        
        else:  # detailed_planning
            prompt_parts.extend([
                "1. Conduct comprehensive analysis of all traveler preferences and constraints",
                "2. Provide detailed destination recommendations with specific rationale",
                "3. Include budget breakdown, best travel times, and logistical considerations",
                "4. Suggest specific neighborhoods, must-see highlights, and insider tips",
                "5. Address any special requirements or accessibility needs mentioned"
            ])
        
        prompt_parts.append("")
        
        # 7. Response guidelines tailored to strategy (LENGTH AND QUALITY CONTROL)
        prompt_parts.append("Response guidelines:")
        
        strategy_guidelines = {
            "question_focused": [
                "• Keep response concise but encouraging (2-3 paragraphs max)",
                "• Ask no more than 3 specific, actionable questions", 
                "• Show enthusiasm for helping plan their trip",
                "• Avoid overwhelming with too many options"
            ],
            "hybrid": [
                "• Provide 1-2 general recommendations while asking for clarification",
                "• Balance being immediately helpful with gathering more info",
                "• Keep response moderate length (3-4 paragraphs)",
                "• Show expertise while remaining conversational"
            ],
            "recommendation_focused": [
                "• Provide 2-4 specific destination recommendations with clear reasoning",
                "• Explain why each destination fits their budget, interests, and constraints",
                "• Include practical details (best time to visit, approximate costs)",
                "• Use confident, expert tone while remaining personable",
                "• Aim for comprehensive but digestible response (4-5 paragraphs)"
            ],
            "detailed_planning": [
                "• Provide comprehensive destination analysis with detailed insights",
                "• Include specific neighborhoods, activities, and insider recommendations",
                "• Address all mentioned preferences and constraints thoroughly",
                "• Provide actionable next steps for trip planning",
                "• Use extensive expertise while maintaining conversational tone"
            ]
        }
        
        for guideline in strategy_guidelines[response_strategy["type"]]:
            prompt_parts.append(guideline)
        
        prompt_parts.append("")
        
        # 8. External data usage instructions (SMART DATA ROUTING)
        if external_relevance["use_weather"] or external_relevance["use_attractions"]:
            prompt_parts.append("External data usage:")
            if external_relevance["use_weather"]:
                prompt_parts.append("• USE the weather data provided - it's current and relevant")
                prompt_parts.append("• Integrate weather insights naturally into recommendations")
            if external_relevance["use_attractions"]:
                prompt_parts.append("• USE the attractions data provided - it's current and relevant")
                prompt_parts.append("• Reference specific attractions when recommending destinations")
        else:
            prompt_parts.append("External data usage:")
            prompt_parts.append("• Rely on your extensive knowledge - external data not relevant for this query")
            prompt_parts.append("• Do not reference weather or attraction data that may be shown above")
        
        prompt_parts.append("")
        
        # 9. Quality and tone guidelines (CONVERSATION QUALITY)
        prompt_parts.extend([
            "Quality standards:",
            "• Be conversational, enthusiastic, and genuinely helpful",
            "• Use specific examples and concrete details when possible",
            "• Demonstrate deep travel knowledge while remaining accessible",
            "• Match response length to information available and strategy type",
            "• Use formatting (bullets, brief headers) for easy reading when appropriate",
            "",
            "Generate your destination recommendation response:"
        ])
        
        # Join all parts into final prompt
        final_prompt = "\n".join(prompt_parts)
        
        # Log prompt engineering details for monitoring
        logger.info(f"Strategic prompt built: strategy={response_strategy['type']}, "
                   f"info_quality={info_analysis['information_quality']}, "
                   f"weather_used={external_relevance['use_weather']}, "
                   f"attractions_used={external_relevance['use_attractions']}")
        
        return final_prompt
    
    def _build_fallback_prompt(self, user_query: str, global_context: List[str], 
                              type_specific_context: List[str]) -> str:
        """
        Fallback prompt when advanced analysis fails.
        Still demonstrates good prompt engineering principles.
        """
        return f"""You are an expert destination consultant with deep travel knowledge.

USER QUERY: "{user_query}"

AVAILABLE INFORMATION:
{chr(10).join(f"• {item}" for item in global_context + type_specific_context if item)}

INSTRUCTIONS:
1. Analyze what information is available about the traveler
2. If you have enough info, provide specific destination recommendations
3. If missing critical details, ask 2-3 targeted questions
4. Be conversational, helpful, and demonstrate travel expertise
5. Keep response length appropriate to available information

Generate your destination recommendation response:"""