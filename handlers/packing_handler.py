import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PackingHandler:
    """
    Smart prompt engineering for packing suggestions.
    
    """
    
    def __init__(self):
        # These help us decide how to respond based on info quality
        self.completeness_thresholds = {
            "minimal": 0.2,      # Almost no useful info - focus on questions
            "partial": 0.5,      # Some info but gaps - hybrid approach  
            "sufficient": 0.8,   # Good info - provide recommendations
            "complete": 1.0      # Comprehensive info - detailed packing list
        }
        
        # The key things we need to know to give good packing advice
        self.critical_info_categories = {
            "destination_weather": ["destination", "travel_dates", "duration"],
            "activities_gear": ["activities", "interests", "travel_style"],
            "luggage_constraints": ["luggage_type", "group_size", "constraints"],
            "special_needs": ["special_needs", "accessibility_needs", "laundry_availability"]
        }
        
        logger.info("PackingHandler ready to build smart packing prompts")
    
    def build_final_prompt(self, user_query: str, global_context: List[str], 
                          type_specific_context: List[str], external_data: Dict[str, Any],
                          recent_conversation: List[Dict[str, Any]], 
                          classification_result: Dict[str, Any]) -> str:
        """
        Build a smart prompt for packing recommendations.
        
        """
        try:
            # Figure out how much useful info we actually have
            info_analysis = self._analyze_information_completeness(
                user_query, global_context, type_specific_context
            )
            
            # Trust the classifier's decision about external data completely
            weather_relevance = self._assess_weather_data_relevance(
                external_data, classification_result
            )
            
            # Pick the best response strategy based on what we know
            response_strategy = self._determine_response_strategy(
                info_analysis, weather_relevance, recent_conversation
            )
            
            # Build conversation context so we don't repeat ourselves
            conversation_context = self._build_conversation_context(recent_conversation)
            
            # Filter context to only include the most relevant stuff
            filtered_context = self._filter_and_prioritize_context(
                global_context, type_specific_context, info_analysis
            )
            
            # Put it all together into a strategic prompt
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
                f"Built packing prompt: {len(final_prompt)} chars, "
                f"strategy={response_strategy['type']}, "
                f"completeness={info_analysis['completeness_score']:.2f}, "
                f"weather_used={weather_relevance['use_weather']} "
                f"(classifier-driven)"
            )
            
        
            return final_prompt
            
        except Exception as e:
            logger.error(f"Error building packing prompt: {str(e)}")
            return self._build_fallback_prompt(user_query, global_context, type_specific_context)
    
    def _analyze_information_completeness(self, user_query: str, global_context: List[str], 
                                        type_specific_context: List[str]) -> Dict[str, Any]:
        """
        Figure out how much we actually know vs how much we need to know.

        """
        analysis = {
            "available_info": {},
            "missing_info": [],
            "completeness_score": 0.0,
            "critical_gaps": [],
            "information_quality": "minimal"
        }
        
        try:
            # Parse what we know from previous conversations
            all_context = global_context + type_specific_context
            available_info = {}
            
            for item in all_context:
                if ":" in item:
                    key, value = item.split(":", 1)
                    available_info[key.strip().lower()] = value.strip()
            
            # Extract new info from their current question
            query_info = self._extract_info_from_query(user_query)
            available_info.update(query_info)
            
            analysis["available_info"] = available_info
            
            # Check each category to see how well we're doing
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
            
            # Calculate overall completeness
            overall_score = sum(scores["score"] for scores in category_scores.values()) / len(category_scores)
            analysis["completeness_score"] = overall_score
            analysis["category_scores"] = category_scores
            analysis["critical_gaps"] = missing_critical
            
            # Assign a quality level
            if overall_score >= self.completeness_thresholds["complete"]:
                analysis["information_quality"] = "complete"
            elif overall_score >= self.completeness_thresholds["sufficient"]:
                analysis["information_quality"] = "sufficient"
            elif overall_score >= self.completeness_thresholds["partial"]:
                analysis["information_quality"] = "partial"
            else:
                analysis["information_quality"] = "minimal"
            
            # Figure out what to ask about if we need more info
            if "destination_weather" in missing_critical:
                analysis["missing_info"].append("destination_and_travel_dates")
            if "activities_gear" in missing_critical:
                analysis["missing_info"].append("planned_activities_and_style")
            if "luggage_constraints" in missing_critical:
                analysis["missing_info"].append("luggage_preferences_and_constraints")
            
            logger.info(f"Packing info analysis: {analysis['information_quality']} quality, score={overall_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error analyzing packing info completeness: {str(e)}")
            analysis["completeness_score"] = 0.1
            analysis["information_quality"] = "minimal"
        
        return analysis
    
    def _extract_info_from_query(self, query: str) -> Dict[str, str]:
        """
        Pull useful info directly from what the user just said (fallback backup).
        
        """
        info = {}
        query_lower = query.lower()
        
        # Activity patterns - these drive gear recommendations
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
        
        # Luggage type affects what we can recommend
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
        
        # Duration affects quantities
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
        
        # Special needs that affect packing
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
                                      classification_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trust the classifier's decision about external data completely.
        Only verify that the data actually exists and has content.
        """
        relevance = {
            "weather_relevant": False,
            "weather_reason": "",
            "use_weather": False,
            "temporal_relevance": "unknown",
            "data_freshness": "unknown"
        }
        
        try:
            # Get classifier's decisions
            external_data_needed = classification_result.get("external_data_needed", False)
            external_data_type = classification_result.get("external_data_type", "none")
            
            logger.info(f"Classifier decision: external_data_needed={external_data_needed}, type={external_data_type}")
            
            if not external_data_needed:
                relevance["weather_reason"] = "Classifier determined no external data needed"
                logger.info("Trusting classifier: no external data needed")
                return relevance
            
            # Classifier says we need external data - check if it's weather data
            if external_data_type in ["weather", "both"]:
                has_weather = "weather" in external_data and external_data["weather"].get("success")
                
                if has_weather:
                    # Verify data quality
                    weather_data = external_data["weather"]
                    current_temp = weather_data.get('current_weather', {}).get('temperature', 'N/A')
                    forecast_entries = len(weather_data.get('forecast', []))
                    
                    if current_temp != 'N/A' and forecast_entries > 0:
                        relevance["weather_relevant"] = True
                        relevance["use_weather"] = True
                        relevance["temporal_relevance"] = "classifier_determined"
                        relevance["data_freshness"] = "current"
                        relevance["weather_reason"] = f"Classifier requested weather data - available and valid"
                        logger.info("Using weather data as requested by classifier")
                    else:
                        relevance["weather_reason"] = f"Classifier requested weather data but quality is limited"
                        logger.warning("Weather data requested but quality is limited")
                else:
                    relevance["weather_reason"] = f"Classifier requested weather data but none available"
                    logger.warning("Weather data requested but not available")
            else:
                relevance["weather_reason"] = f"Classifier requested {external_data_type} data, not weather"
                logger.info("Classifier didn't request weather data")
            
            # Log final decision
            logger.info(f"Final weather data usage: use_weather={relevance['use_weather']}")
            
        except Exception as e:
            logger.error(f"Error assessing weather data relevance: {str(e)}")
            relevance["weather_reason"] = f"Error in relevance assessment: {str(e)}"
        
        return relevance
    
    def _determine_response_strategy(self, info_analysis: Dict[str, Any], 
                                   weather_relevance: Dict[str, Any],
                                   recent_conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Pick the best response strategy based on what we know and what we need.
        
        - If you know almost nothing: ask questions
        - If you know some things: give some suggestions and ask for clarification
        - If you know enough: give solid recommendations
        - If you know everything: give detailed packing lists
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
            
            # Pick strategy based on how much we know
            if quality == "minimal" or completeness < 0.3:
                strategy["type"] = "hybrid"
                strategy["approach"] = "Provide 2-3 general packing recommendations and ask clarifying questions"
                strategy["length_target"] = "concise"
                strategy["questioning_strategy"] = "Ask 2-3 targeted questions to gather essential packing information"
                strategy["recommendation_depth"] = "general"
                
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
            
            # Avoid endless question loops in long conversations
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
        """Build conversation context so we don't repeat ourselves or ask the same questions."""
        if not recent_conversation:
            return ""
        
        try:
            # Get last 8 conversation turns for context efficiency
            recent_messages = recent_conversation[-8:]
            
            context_lines = ["CONVERSATION CONTEXT:"]
            for msg in recent_messages:
                if "user_query" in msg:
                    context_lines.append(f"User: {msg['user_query']}")
                elif "assistant_answer" in msg:
                    # Summarize long answers to keep context manageable
                    answer = msg['assistant_answer']
                    # if len(answer) > 200:
                    #     answer = answer[:200] + "..."
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
        Filter context to only include the most relevant stuff for packing.
        
        """
        filtered = {
            "high_priority": [],    # Essential for packing recommendations
            "medium_priority": [],  # Useful but not critical
            "low_priority": []      # Background information
        }
        
        try:
            all_context = global_context + type_specific_context
            
            # These are the most important things for packing recommendations
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
        Build the actual prompt that gets sent to the AI.
      
        """
        
        # Start building the prompt
        prompt_parts = []
        
        # Set up the AI's role
        prompt_parts.append(
            "You are an expert packing consultant with deep knowledge of travel gear, weather considerations, "
            "activity-specific equipment, luggage optimization, and international travel requirements."
        )
        prompt_parts.append("")
        
        # Show what the user asked
        prompt_parts.append(f'USER QUERY: "{user_query}"')
        prompt_parts.append("")
        
        # Add conversation history if relevant
        if conversation_context:
            prompt_parts.append(conversation_context)
        
        # Share what we know about the user (prioritized)
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
        
        # Include weather data only if the classifier requested it
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
        
        # Give strategic instructions based on our analysis
        prompt_parts.append("STRATEGIC RESPONSE INSTRUCTIONS:")
                
        if response_strategy["type"] == "question_focused":
            prompt_parts.extend([
                "1. Analyze what critical information is missing for effective packing recommendations",
                "2. Identify the 2-3 most important questions to ask for packing success",
                "3. Provide a brief, encouraging response that gathers essential details",
                "4. Focus on destination, planned activities, and luggage constraints",
                "5. Maintain an answer structure that is easy to read and user-friendly."

            ])
        
        elif response_strategy["type"] in ["hybrid", "hybrid_with_weather"]:
            prompt_parts.extend([
                "1. Assess what information is available and what's missing for packing",
                "2. Provide helpful general packing advice based on available info",
                "3. Ask 1-2 specific questions to fill important gaps",
                "4. Balance being helpful now while gathering more details",
                "5. Maintain an answer structure that is easy to read and user-friendly."
            ])
            
            if "with_weather" in response_strategy["type"]:
                prompt_parts.append("6. Integrate current weather data naturally into packing recommendations")

        elif response_strategy["type"] == "recommendation_focused":
            prompt_parts.extend([
                "1. Analyze all available trip information, activities, and constraints",
                "2. Consider weather conditions, luggage type, and special needs",
                "3. Provide categorized packing recommendations with clear reasoning",
                "4. Explain why each item/category is important for their specific trip",
                "5. Include practical packing tips and space-saving techniques",
                "6. Maintain an answer structure that is easy to read and user-friendly."
            ])
        
        else:  # detailed_packing_list
            prompt_parts.extend([
                "1. Conduct comprehensive analysis of all trip factors and constraints",
                "2. Create detailed, categorized packing list with specific item recommendations",
                "3. Include weather-appropriate clothing with layering strategies",
                "4. Address activity-specific gear and equipment needs",
                "5. Provide luggage organization tips and weight management strategies",
                "6. Include travel documents, electronics, and destination-specific items",
                "7. Maintain an answer structure that is easy to read and user-friendly."
            ])
        
        prompt_parts.append("")
        
        # Response guidelines tailored to each strategy
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
        
        # Instructions on using weather data - now purely classifier-driven
        if weather_relevance["use_weather"]:
            prompt_parts.append("Weather data usage:")
            prompt_parts.append("• USE the weather data provided - classifier determined it's relevant")
            prompt_parts.append("• Make specific clothing recommendations based on actual temperatures and conditions")
            prompt_parts.append("• Consider the 5-day forecast for layering and backup clothing needs")
            prompt_parts.append("• Integrate weather insights naturally into packing categories")
        else:
            prompt_parts.append("Weather data usage:")
            prompt_parts.append("• Classifier determined no weather data needed - rely on your extensive knowledge")
            prompt_parts.append("• Use general climatic knowledge for the destination and season")
        
        prompt_parts.append("")
        
        # Quality and tone guidelines
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
            "Generate your packing recommendation response and most importantly keep on readable format and keep on flow:"
        ])
        
        # Put it all together
        final_prompt = "\n".join(prompt_parts)
        
        # Log what we built for debugging
        logger.info(f"Built packing prompt: strategy={response_strategy['type']}, "
                   f"info_quality={info_analysis['information_quality']}, "
                   f"weather_used={weather_relevance['use_weather']} "
                   f"(classifier-driven)")

        print(f"--------------")
        print(f"Final packing prompt: ")
        print(final_prompt)
        print(f"--------------")

        return final_prompt
    
    def _build_fallback_prompt(self, user_query: str, global_context: List[str], 
                              type_specific_context: List[str]) -> str:
        """
        Simple fallback when our analysis breaks down.
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