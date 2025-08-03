import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AttractionsHandler:
    """
    prompt engineering for local attractions and activities recommendations.
    
    
    """
    
    def __init__(self):
        # These thresholds help us decide how to respond based on info quality
        self.completeness_thresholds = {
            "minimal": 0.2,      # Almost no useful info - focus on questions
            "partial": 0.5,      # Some info but gaps - hybrid approach  
            "sufficient": 0.8,   # Good info - provide recommendations
            "complete": 1.0      # Comprehensive info - detailed planning
        }
        
        # The key things we need to know to give good attraction recommendations
        self.critical_info_categories = {
            "location": ["destination", "region", "continent"],
            "time_constraints": ["time_available", "duration", "travel_dates"],
            "preferences": ["interests", "activities", "budget_per_activity"],
            "accessibility": ["mobility", "accessibility_needs", "group_size"]
        }
        
        logger.info("AttractionsHandler ready to build smart prompts")
    
    def build_final_prompt(self, user_query: str, global_context: List[str], 
                          type_specific_context: List[str], external_data: Dict[str, Any],
                          recent_conversation: List[Dict[str, Any]], 
                          classification_result: Dict[str, Any]) -> str:
        """
        Build a smart prompt based on what we know and what we need.

        The steps mirror how a human travel expert would think:
        1. What do I know vs what do I need to know?
        2. Do I have current data that would be helpful?
        3. What's the best way to respond given the situation?
        4. How do I craft a response that feels natural and helpful?
        """
        try:
            # Figure out how much useful info we actually have
            info_analysis = self._analyze_information_completeness(
                user_query, global_context, type_specific_context
            )
            
            # Trust the classifier's decision about external data completely
            external_relevance = self._assess_external_data_relevance(
                external_data, classification_result
            )
            
            # Pick the best response strategy based on what we know
            response_strategy = self._determine_response_strategy(
                info_analysis, external_relevance, recent_conversation
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
                external_relevance=external_relevance,
                external_data=external_data
            )
            
            logger.info(
                f"Built attractions prompt: {len(final_prompt)} chars, "
                f"strategy={response_strategy['type']}, "
                f"completeness={info_analysis['completeness_score']:.2f}, "
                f"weather_used={external_relevance['use_weather']}, "
                f"attractions_used={external_relevance['use_attractions']} "
                f"(trusted classifier decision)"
            )
            
            return final_prompt
            
        except Exception as e:
            logger.error(f"Error building attractions prompt: {str(e)}")
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
            if "location" in missing_critical:
                analysis["missing_info"].append("destination_or_current_location")
            if "time_constraints" in missing_critical:
                analysis["missing_info"].append("time_available_and_duration")
            if "preferences" in missing_critical:
                analysis["missing_info"].append("interests_and_activity_preferences")
            
            logger.info(f"Info analysis: {analysis['information_quality']} quality, score={overall_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error analyzing info completeness: {str(e)}")
            analysis["completeness_score"] = 0.1
            analysis["information_quality"] = "minimal"
        
        return analysis
    
    def _extract_info_from_query(self, query: str) -> Dict[str, str]:
        """
        Pull useful info directly from what the user just said (fallback backup).
        
        """
        info = {}
        query_lower = query.lower()
        
        # Look for time mentions
        time_patterns = [
            r'(\d+)\s*hours?',
            r'(\d+)\s*days?',
            r'(half\s+day|morning|afternoon|evening)',
            r'(quick\s+visit|short\s+time)',
            r'(full\s+day|entire\s+day)'
        ]
        for pattern in time_patterns:
            match = re.search(pattern, query_lower)
            if match:
                info["time_available"] = match.group(1)
                break
        
        # Look for interest indicators
        interest_patterns = [
            r'(museums?|galleries?|art)',
            r'(food|restaurants?|dining)',
            r'(nightlife|bars?|clubs?)',
            r'(nature|parks?|outdoor)',
            r'(history|historical|culture)',
            r'(shopping|markets?)',
            r'(adventure|sports?|active)',
            r'(family|kids?|children)'
        ]
        interests = []
        for pattern in interest_patterns:
            if re.search(pattern, query_lower):
                interests.append(pattern.strip('()'))
        
        if interests:
            info["interests"] = ", ".join(interests[:3])  # Limit to top 3
        
        # Budget clues
        budget_patterns = [
            r'free\s+activities?',
            r'budget\s+friendly',
            r'expensive\s+is\s+okay',
            r'money\s+no\s+object',
            r'\$(\d+)\s*per\s+person'
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if 'free' in pattern:
                    info["budget_per_activity"] = "free activities preferred"
                elif 'budget' in pattern:
                    info["budget_per_activity"] = "budget-friendly"
                elif 'expensive' in pattern or 'money no object' in pattern:
                    info["budget_per_activity"] = "budget not a concern"
                elif match.group(1):
                    info["budget_per_activity"] = f"${match.group(1)} per person"
                break
        
        # Destination mentions
        destination_patterns = [
            r'things\s+to\s+do\s+in\s+([A-Za-z\s]+?)(?:\s|$|,|\.|!|\?)',
            r'attractions\s+in\s+([A-Za-z\s]+?)(?:\s|$|,|\.|!|\?)',
            r'visit\s+in\s+([A-Za-z\s]+?)(?:\s|$|,|\.|!|\?)',
            r'see\s+in\s+([A-Za-z\s]+?)(?:\s|$|,|\.|!|\?)'
        ]
        for pattern in destination_patterns:
            match = re.search(pattern, query_lower)
            if match:
                destination = match.group(1).strip()
                if len(destination) > 2 and destination not in ['the', 'a', 'an', 'my', 'our']:
                    info["destination"] = destination.title()
                    break
        
        return info
    
    def _assess_external_data_relevance(self, external_data: Dict[str, Any], 
                                      classification_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trust the classifier's decision about external data completely.
        Only verify that the data actually exists and has content.
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
            # Get classifier's decisions
            external_data_needed = classification_result.get("external_data_needed", False)
            external_data_type = classification_result.get("external_data_type", "none")
            
            logger.info(f"Classifier decision: external_data_needed={external_data_needed}, type={external_data_type}")
            
            if not external_data_needed:
                relevance["weather_reason"] = "Classifier determined no external data needed"
                relevance["attractions_reason"] = "Classifier determined no external data needed"
                logger.info("Trusting classifier: no external data needed")
                return relevance
            
            # Classifier says we need external data - check what type and verify availability
            
            # Check weather data
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
                        relevance["weather_reason"] = f"Classifier requested weather data - available and valid"
                        logger.info("Using weather data as requested by classifier")
                    else:
                        relevance["weather_reason"] = f"Classifier requested weather data but quality is limited"
                        logger.warning("Weather data requested but quality is limited")
                else:
                    relevance["weather_reason"] = f"Classifier requested weather data but none available"
                    logger.warning("Weather data requested but not available")
            
            # Check attractions data  
            if external_data_type in ["attractions", "both"]:
                has_attractions = "attractions" in external_data and external_data["attractions"].get("success")
                
                if has_attractions:
                    # Verify data quality
                    attractions_data = external_data["attractions"]
                    total_found = attractions_data.get("total_found", 0)
                    
                    if total_found > 0:
                        relevance["attractions_relevant"] = True
                        relevance["use_attractions"] = True
                        relevance["attractions_reason"] = f"Classifier requested attractions data - {total_found} attractions available"
                        logger.info(f"Using attractions data as requested by classifier ({total_found} found)")
                    else:
                        relevance["attractions_reason"] = f"Classifier requested attractions data but none found"
                        logger.warning("Attractions data requested but none found")
                else:
                    relevance["attractions_reason"] = f"Classifier requested attractions data but none available"
                    logger.warning("Attractions data requested but not available")
            
            # Log final decision
            logger.info(f"Final external data usage: weather={relevance['use_weather']}, attractions={relevance['use_attractions']}")
            
        except Exception as e:
            logger.error(f"Error assessing external data relevance: {str(e)}")
            relevance["weather_reason"] = f"Error in relevance assessment: {str(e)}"
            relevance["attractions_reason"] = f"Error in relevance assessment: {str(e)}"
        
        return relevance
    
    def _determine_response_strategy(self, info_analysis: Dict[str, Any], 
                                   external_relevance: Dict[str, Any],
                                   recent_conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Pick the best response strategy based on what we know and what we need.
        
        - If you know almost nothing: ask questions
        - If you know some things: give some suggestions and ask for clarification
        - If you know enough: give solid recommendations
        - If you know everything: give detailed planning advice
        
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
            has_attractions_data = external_relevance["use_attractions"]
            
            # Pick strategy based on how much we know
            if quality == "minimal" or completeness < 0.3:
                strategy["type"] = "hybrid"
                strategy["approach"] = "Always provide 2-3 general attraction recommendations and ask clarifying questions, even with minimal info."
                strategy["length_target"] = "concise"
                strategy["questioning_strategy"] = "Ask 2-3 targeted questions to gather essential information, but always give recommendations first."
                strategy["recommendation_depth"] = "general"

            elif quality == "partial" or completeness < 0.6:
                if has_attractions_data:
                    strategy["type"] = "hybrid_with_data"
                    strategy["approach"] = "Provide current attractions while gathering missing details"
                    strategy["recommendation_depth"] = "general_with_current_data"
                else:
                    strategy["type"] = "hybrid"
                    strategy["approach"] = "Provide general recommendations while gathering missing details"
                    strategy["recommendation_depth"] = "general"
                
                strategy["length_target"] = "moderate"
                strategy["questioning_strategy"] = "Ask for 1-2 specific details while giving helpful suggestions"
                
            elif quality == "sufficient" or completeness < 0.8:
                strategy["type"] = "recommendation_focused"
                strategy["approach"] = "Provide solid attractions recommendations with clear reasoning"
                strategy["length_target"] = "comprehensive"
                strategy["questioning_strategy"] = "Optional clarification questions only"
                strategy["recommendation_depth"] = "detailed"
                
            else:  # complete
                strategy["type"] = "detailed_planning"
                strategy["approach"] = "Provide comprehensive attractions recommendations with detailed insights"
                strategy["length_target"] = "comprehensive"
                strategy["questioning_strategy"] = "No questions needed"
                strategy["recommendation_depth"] = "comprehensive"
            
            # Avoid endless question loops in long conversations
            conversation_length = len(recent_conversation)
            if conversation_length > 4:  # Long conversation - be more decisive
                if strategy["type"] == "question_focused":
                    strategy["type"] = "hybrid"
                    strategy["approach"] = "Move conversation forward with recommendations and minimal questions"
            
            # Enhance strategy if we have good external data
            if has_attractions_data and strategy["type"] in ["recommendation_focused", "detailed_planning"]:
                strategy["approach"] += " using current attractions data"
                strategy["recommendation_depth"] += "_with_current_data"
            
            logger.info(f"Selected strategy: {strategy['type']} for {quality} quality information")
            
        except Exception as e:
            logger.error(f"Error determining response strategy: {str(e)}")
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
        Filter context to only include the most relevant stuff for attractions
        (not overwhelm the prompt with irrelevant info).
     
        """
        filtered = {
            "high_priority": [],    # Essential for attractions recommendations
            "medium_priority": [],  # Useful but not critical
            "low_priority": []      # Background information
        }
        
        try:
            all_context = global_context + type_specific_context
            
            # These are the most important things for attraction recommendations
            high_priority_keys = [
                "destination", "interests", "time_available", "budget_per_activity", 
                "activities", "accessibility_needs", "mobility"
            ]
            
            medium_priority_keys = [
                "duration", "travel_dates", "group_size", "travel_style"
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
        Build the actual prompt that gets sent to the AI.
        
        """
        
        # Start building the prompt
        prompt_parts = []
        
        # Set up the AI's role
        prompt_parts.append(
            "You are an expert local attractions consultant with deep knowledge of global destinations, "
            "current attractions, visitor preferences, activity planning, and personalized recommendations."
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
            prompt_parts.append("KEY VISITOR INFORMATION:")
            for item in filtered_context["high_priority"]:
                prompt_parts.append(f"• {item}")
            prompt_parts.append("")
        
        if filtered_context["medium_priority"]:
            prompt_parts.append("ADDITIONAL CONTEXT:")
            for item in filtered_context["medium_priority"]:
                prompt_parts.append(f"• {item}")
            prompt_parts.append("")
        
        # Include external data based purely on classifier's decision
        if external_relevance["use_weather"] and "weather" in external_data:
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
                for entry in forecast:
                    dt_str = entry.get('datetime', '')
                    temp = entry.get('temperature', 'N/A')
                    desc = entry.get('description', 'N/A')
                    prompt_parts.append(f"  - {dt_str}: {temp}°C, {desc}")
            
            prompt_parts.append("")
        
        if external_relevance["use_attractions"] and "attractions" in external_data:
            attractions = external_data["attractions"]
            prompt_parts.append("CURRENT ATTRACTIONS DATA: (not seen by user - Don't use reference to here in response)")
            prompt_parts.append(f"• Destination: {attractions.get('destination', 'Unknown')}")
            
            # Include actual attractions data if available
            attractions_list = attractions.get('attractions', [])
            if attractions_list:
                prompt_parts.append("• Current attractions available:")
                for i, attraction in enumerate(attractions_list[:20], 1):  # Limit to 20 for prompt efficiency
                    name = attraction.get('name', 'Unknown')
                    price = attraction.get('price', 'Price not available')
                    description = attraction.get('description', '').strip()
                    
                    # Include brief description after price
                    if description:
                        # Limit description to keep prompt manageable
                        description_snippet = description[:100]
                        if len(description) > 100:
                            description_snippet += "..."
                        prompt_parts.append(f"  {i}. {name} - {price} - {description_snippet}")
                    else:
                        prompt_parts.append(f"  {i}. {name} - {price}")
                
                if len(attractions_list) > 20:
                    prompt_parts.append(f"  ... and {len(attractions_list) - 20} more attractions")

            prompt_parts.append("")
        
        # Give strategic instructions based on our analysis
        prompt_parts.append("STRATEGIC RESPONSE INSTRUCTIONS:")
        
        
        if response_strategy["type"] == "question_focused":
            prompt_parts.extend([
                "1. Analyze what critical information is missing for attractions recommendations",
                "2. Identify the 2-3 most important questions to ask",
                "3. Provide a brief, encouraging response that gathers essential details",
                "4. Focus on destination, available time, and activity interests",
                "5. Maintain an answer structure that is easy to read and user-friendly."
            ])
        
        elif response_strategy["type"] in ["hybrid", "hybrid_with_data"]:
            prompt_parts.extend([
                "1. Assess what information is available and what's missing",
                "2. Provide helpful attraction suggestions based on available info",
                "3. Ask 1-2 specific questions to fill important gaps",
                "4. Balance being helpful now while gathering more details",
                "5. Maintain an answer structure that is easy to read and user-friendly."
            ])
            
            if "with_data" in response_strategy["type"]:
                prompt_parts.append("6. Integrate current attractions data naturally into recommendations")

        elif response_strategy["type"] == "recommendation_focused":
            prompt_parts.extend([
                "1. Analyze all available visitor information and preferences",
                "2. Consider time constraints, interests, and accessibility needs",
                "3. Provide 3-5 specific attraction recommendations with clear reasoning",
                "4. Explain why each attraction matches their stated preferences",
                "5. Include practical considerations (timing, costs, accessibility)",
                "6. Maintain an answer structure that is easy to read and user-friendly."
            ])
        
        else:  # detailed_planning
            prompt_parts.extend([
                "1. Conduct comprehensive analysis of all visitor preferences and constraints",
                "2. Provide detailed attraction recommendations with specific rationale",
                "3. Include timing suggestions, costs, and logistical considerations",
                "4. Suggest optimal routes, must-see highlights, and insider tips",
                "5. Address any special requirements or accessibility needs mentioned",
                "6. Maintain an answer structure that is easy to read and user-friendly."
            ])
        
        prompt_parts.append("")
        
        # Response guidelines tailored to each strategy
        prompt_parts.append("Response guidelines:")
        
        strategy_guidelines = {
            "question_focused": [
                "• Keep response concise but encouraging (2-3 paragraphs max)",
                "• Ask no more than 3 specific, actionable questions", 
                "• Show enthusiasm for helping with their attractions planning",
                "• Avoid overwhelming with too many options"
            ],
            "hybrid": [
                "• Provide 1-2 general attraction suggestions while asking for clarification",
                "• Balance being immediately helpful with gathering more info",
                "• Keep response moderate length (3-4 paragraphs)",
                "• Show expertise while remaining conversational"
            ],
            "hybrid_with_data": [
                "• Provide 2-3 current attraction recommendations while asking for clarification",
                "• Use the current attractions data to make specific suggestions",
                "• Balance being immediately helpful with gathering more info",
                "• Keep response moderate length (3-4 paragraphs)"
            ],
            "recommendation_focused": [
                "• Provide 3-5 specific attraction recommendations with clear reasoning",
                "• Explain why each attraction fits their time, interests, and constraints",
                "• Include practical details (opening hours, costs, how to get there)",
                "• Use confident, expert tone while remaining personable",
                "• Aim for comprehensive but digestible response (4-5 paragraphs)"
            ],
            "detailed_planning": [
                "• Provide comprehensive attraction analysis with detailed insights",
                "• Include specific timing, routes, and insider recommendations",
                "• Address all mentioned preferences and constraints thoroughly",
                "• Provide actionable itinerary suggestions",
                "• Use extensive expertise while maintaining conversational tone"
            ]
        }
        
        for guideline in strategy_guidelines.get(response_strategy["type"], strategy_guidelines["hybrid"]):
            prompt_parts.append(guideline)
        
        prompt_parts.append("")
        
        # Instructions on using external data - now purely classifier-driven
        if external_relevance["use_weather"] or external_relevance["use_attractions"]:
            prompt_parts.append("External data usage:")
            if external_relevance["use_weather"]:
                prompt_parts.append("• USE the weather data provided - classifier determined it's relevant")
                prompt_parts.append("• Integrate weather insights naturally into recommendations")
            if external_relevance["use_attractions"]:
                prompt_parts.append("• USE the attractions data provided - classifier determined it's relevant")
                prompt_parts.append("• Reference specific attractions when making recommendations")
        else:
            prompt_parts.append("External data usage:")
            prompt_parts.append("• Classifier determined no external data needed - rely on your extensive knowledge")
            prompt_parts.append("• Do not reference weather or attraction data that may be shown above")
        
        prompt_parts.append("")
        
        # Quality and tone guidelines
        prompt_parts.extend([
            "Quality standards:",
            "• Be conversational, enthusiastic, and genuinely helpful",
            "• Use specific examples and concrete details when possible",
            "• Demonstrate deep local knowledge while remaining accessible",
            "• Match response length to information available and strategy type",
            "• Use formatting (bullets, emojis) for easy reading when appropriate",
            "• Prioritize attractions based on stated interests and time available",
            "",
            "Generate your attractions recommendation response and keep on readable format:"
        ])
        
        # Put it all together
        final_prompt = "\n".join(prompt_parts)
        
        # Log what we built for debugging
        logger.info(f"Built strategic prompt: strategy={response_strategy['type']}, "
                   f"info_quality={info_analysis['information_quality']}, "
                   f"weather_used={external_relevance['use_weather']}, "
                   f"attractions_used={external_relevance['use_attractions']} "
                   f"(classifier-driven)")

        print(f"--------------")
        print(f"Final attraction prompt: ")
        print(final_prompt)
        print(f"--------------")

        return final_prompt
    
    def _build_fallback_prompt(self, user_query: str, global_context: List[str], 
                              type_specific_context: List[str]) -> str:
        """
        Simple fallback when our analysis breaks down.

        """
        return f"""You are an expert local attractions consultant with deep knowledge of destinations worldwide.

USER QUERY: "{user_query}"

AVAILABLE INFORMATION:
{chr(10).join(f"• {item}" for item in global_context + type_specific_context if item)}

INSTRUCTIONS:
1. Analyze what information is available about the visitor and destination
2. If you have enough info, provide specific attraction recommendations
3. If missing critical details (destination, time available, interests), ask 2-3 targeted questions
4. Be conversational, helpful, and demonstrate local expertise
5. Keep response length appropriate to available information
6. Prioritize attractions based on stated interests and time constraints

Generate your attractions recommendation response:"""