import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AttractionsHandler:
    """
    Advanced prompt engineering for local attractions and activities recommendations.
    
    Demonstrates production-ready AI engineering skills for Navan assignment:
    
    CONVERSATION QUALITY FEATURES:
    - Information completeness analysis for natural conversation flow
    - Adaptive response strategies based on available context
    - Smart external data relevance assessment
    - Context-aware questioning that builds on previous exchanges
    
    PROMPT DESIGN FEATURES:
    - Multi-step chain-of-thought reasoning tailored to available information
    - Strategic instruction variations based on context completeness
    - Smart data filtering to include only relevant information
    - Length control and response strategy optimization
    - External data usage instructions for intelligent routing
    
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
        
        # Critical information categories for attractions recommendations
        self.critical_info_categories = {
            "location": ["destination", "region", "continent"],
            "time_constraints": ["time_available", "duration", "travel_dates"],
            "preferences": ["interests", "activities", "budget_per_activity"],
            "accessibility": ["mobility", "accessibility_needs", "group_size"]
        }
        
        logger.info("Enhanced AttractionsHandler initialized with intelligent analysis capabilities")
    
    def build_final_prompt(self, user_query: str, global_context: List[str], 
                          type_specific_context: List[str], external_data: Dict[str, Any],
                          recent_conversation: List[Dict[str, Any]]) -> str:
        """
        Build an intelligently engineered prompt for attractions recommendations.
        
        This demonstrates advanced prompt engineering through:
        
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
                external_data, global_context, user_query, info_analysis
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
                f"Built strategic attractions prompt: {len(final_prompt)} chars, "
                f"strategy={response_strategy['type']}, "
                f"completeness={info_analysis['completeness_score']:.2f}, "
                f"attractions_used={external_relevance['use_attractions']}"
            )
            
            return final_prompt
            
        except Exception as e:
            logger.error(f"Error building strategic attractions prompt: {str(e)}")
            return self._build_fallback_prompt(user_query, global_context, type_specific_context)
    
    def _analyze_information_completeness(self, user_query: str, global_context: List[str], 
                                        type_specific_context: List[str]) -> Dict[str, Any]:
        """
        CONVERSATION QUALITY: Analyze information completeness for natural conversation flow.
        
        This enables intelligent questioning strategies by identifying what information
        we have vs what we need for effective attractions recommendations.
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
            
            # Analyze each critical category for attractions
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
            if "location" in missing_critical:
                analysis["missing_info"].append("destination_or_current_location")
            if "time_constraints" in missing_critical:
                analysis["missing_info"].append("time_available_and_duration")
            if "preferences" in missing_critical:
                analysis["missing_info"].append("interests_and_activity_preferences")
            
            logger.info(f"Attractions info analysis: {analysis['information_quality']} quality, score={overall_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error in attractions information analysis: {str(e)}")
            analysis["completeness_score"] = 0.1
            analysis["information_quality"] = "minimal"
        
        return analysis
    
    def _extract_info_from_query(self, query: str) -> Dict[str, str]:
        """
        PROMPT DESIGN: Extract key information directly from user query using smart patterns.
        
        This enhances prompt effectiveness by capturing implicit information for attractions.
        """
        info = {}
        query_lower = query.lower()
        
        # Time available patterns
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
        
        # Interest/activity patterns
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
        
        # Budget patterns
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
        
        # Destination patterns (if asking about specific place)
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
                                      global_context: List[str], user_query: str,
                                      info_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        SMART DATA ROUTING: Intelligently assess when to use external attractions data.
        
        Key insight: Only use external data when it's actually helpful and current.
        Attractions data is only useful when we have a specific destination.
        """
        relevance = {
            "attractions_relevant": False,
            "attractions_reason": "",
            "use_attractions": False,
            "data_freshness": "unknown"
        }
        
        try:
            # Check if we have external attractions data
            has_attractions = "attractions" in external_data and external_data["attractions"].get("success")
            
            if not has_attractions:
                relevance["attractions_reason"] = "No external attractions data available"
                return relevance
            
            # Check if we have a destination established
            available_info = info_analysis.get("available_info", {})
            has_destination = "destination" in available_info
            
            # Check for attractions-specific query indicators
            attractions_query_indicators = [
                "things to do" in user_query.lower(),
                "activities" in user_query.lower(),
                "attractions" in user_query.lower(),
                "see" in user_query.lower() and ("what" in user_query.lower() or "where" in user_query.lower()),
                "visit" in user_query.lower(),
                "recommendations" in user_query.lower() and "attraction" in user_query.lower()
            ]
            
            # Assess relevance based on destination and query type
            if has_destination and any(attractions_query_indicators):
                relevance["attractions_relevant"] = True
                relevance["use_attractions"] = True
                relevance["attractions_reason"] = "Destination known and user explicitly asking about attractions"
                
            elif has_destination and info_analysis["information_quality"] in ["sufficient", "complete"]:
                # Even if not explicitly asking, current attractions can enhance recommendations
                relevance["attractions_relevant"] = True
                relevance["use_attractions"] = True
                relevance["attractions_reason"] = "Destination known - current attractions can inform recommendations"
                
            elif has_destination:
                # Basic case - we have destination but limited other info
                relevance["attractions_relevant"] = True
                relevance["use_attractions"] = True
                relevance["attractions_reason"] = "Destination available - attractions data can be helpful"
                
            else:
                relevance["attractions_reason"] = "No specific destination identified - external attractions not relevant yet"
            
            # Assess data freshness if we're using it
            if relevance["use_attractions"] and has_attractions:
                attractions_data = external_data["attractions"]
                total_found = attractions_data.get("total_found", 0)
                geocoding_method = attractions_data.get("geocoding_method", "unknown")
                
                if total_found > 0:
                    relevance["data_freshness"] = "current"
                    if geocoding_method == "gemini_tourism_center":
                        relevance["attractions_reason"] += " (via tourism center geocoding)"
                else:
                    relevance["data_freshness"] = "limited"
                    relevance["attractions_reason"] += " (limited data available)"
            
            logger.info(f"Attractions data relevance: use={relevance['use_attractions']}, reason={relevance['attractions_reason']}")
            
        except Exception as e:
            logger.error(f"Error assessing attractions data relevance: {str(e)}")
            relevance["attractions_reason"] = f"Error in relevance assessment: {str(e)}"
        
        return relevance
    
    def _determine_response_strategy(self, info_analysis: Dict[str, Any], 
                                   external_relevance: Dict[str, Any],
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
            has_attractions_data = external_relevance["use_attractions"]
            
            # Determine strategy based on information quality
            if quality == "minimal" or completeness < 0.3:
                strategy["type"] = "question_focused"
                strategy["approach"] = "Ask 2-3 targeted questions to gather essential information"
                strategy["length_target"] = "concise"
                strategy["questioning_strategy"] = "Focus on destination, available time, and interests"
                strategy["recommendation_depth"] = "none"
                
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
            
            # Adjust based on conversation length (avoid question loops)
            conversation_length = len(recent_conversation)
            if conversation_length > 4:  # Long conversation - be more decisive
                if strategy["type"] == "question_focused":
                    strategy["type"] = "hybrid"
                    strategy["approach"] = "Move conversation forward with recommendations and minimal questions"
            
            # Enhance strategy if we have good external data
            if has_attractions_data and strategy["type"] in ["recommendation_focused", "detailed_planning"]:
                strategy["approach"] += " using current attractions data"
                strategy["recommendation_depth"] += "_with_current_data"
            
            logger.info(f"Selected attractions strategy: {strategy['type']} for {quality} quality information")
            
        except Exception as e:
            logger.error(f"Error determining attractions response strategy: {str(e)}")
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
        
        Only include the most relevant information for attractions recommendations.
        """
        filtered = {
            "high_priority": [],    # Essential for attractions recommendations
            "medium_priority": [],  # Useful but not critical
            "low_priority": []      # Background information
        }
        
        try:
            all_context = global_context + type_specific_context
            
            # Define priority keywords for attractions recommendations
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
            
            logger.info(f"Filtered attractions context: {len(filtered['high_priority'])} high, {len(filtered['medium_priority'])} medium priority items")
            
        except Exception as e:
            logger.error(f"Error filtering attractions context: {str(e)}")
            # Fallback: treat all as medium priority
            filtered["medium_priority"] = global_context + type_specific_context
        
        return filtered
    
    def _build_strategic_prompt(self, user_query: str, info_analysis: Dict[str, Any],
                              response_strategy: Dict[str, Any], conversation_context: str,
                              filtered_context: Dict[str, List[str]], 
                              external_relevance: Dict[str, Any],
                              external_data: Dict[str, Any]) -> str:
        """
        PROMPT DESIGN: Build strategically engineered prompt for attractions recommendations.
        
        This creates targeted, effective prompts based on comprehensive analysis.
        """
        
        # Start building the prompt parts
        prompt_parts = []
        
        # 1. Expert role definition with domain expertise
        prompt_parts.append(
            "You are an expert local attractions consultant with deep knowledge of global destinations, "
            "current attractions, visitor preferences, activity planning, and personalized recommendations."
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
            prompt_parts.append("KEY VISITOR INFORMATION:")
            for item in filtered_context["high_priority"]:
                prompt_parts.append(f"• {item}")
            prompt_parts.append("")
        
        if filtered_context["medium_priority"]:
            prompt_parts.append("ADDITIONAL CONTEXT:")
            for item in filtered_context["medium_priority"]:
                prompt_parts.append(f"• {item}")
            prompt_parts.append("")
        
        # 5. External data (ONLY if determined to be relevant)
        if external_relevance["use_attractions"] and "attractions" in external_data:
            attractions = external_data["attractions"]
            prompt_parts.append("CURRENT ATTRACTIONS DATA: (the user DOES NOT see this)")
            prompt_parts.append(f"• Destination: {attractions.get('destination', 'Unknown')}")
            # REMOVED: prompt_parts.append(f"• Total attractions found: {attractions.get('total_found', 0)}")
            
            # Include actual attractions data if available
            attractions_list = attractions.get('attractions', [])
            if attractions_list:
                prompt_parts.append("• Current attractions available:")
                for i, attraction in enumerate(attractions_list[:20], 1):  # Limit to 20 for prompt efficiency
                    name = attraction.get('name', 'Unknown')
                    price = attraction.get('price', 'Price not available')
                    description = attraction.get('description', '').strip()
                    
                    # ADDED: Include description snippet after price
                    if description:
                        # Limit description to first 100 characters for prompt efficiency
                        description_snippet = description[:100]
                        if len(description) > 100:
                            description_snippet += "..."
                        prompt_parts.append(f"  {i}. {name} - {price} - {description_snippet}")
                    else:
                        prompt_parts.append(f"  {i}. {name} - {price}")
                
                if len(attractions_list) > 20:
                    prompt_parts.append(f"  ... and {len(attractions_list) - 20} more attractions")

            prompt_parts.append("")
        
        # 6. Strategic instructions based on response strategy
        prompt_parts.append("STRATEGIC RESPONSE INSTRUCTIONS:")
        prompt_parts.append("")
        
        # Chain-of-thought reasoning specific to strategy (ADVANCED PROMPT ENGINEERING)
        prompt_parts.append("Chain-of-thought reasoning process:")
        
        if response_strategy["type"] == "question_focused":
            prompt_parts.extend([
                "1. Analyze what critical information is missing for attractions recommendations",
                "2. Identify the 2-3 most important questions to ask",
                "3. Provide a brief, encouraging response that gathers essential details",
                "4. Focus on destination, available time, and activity interests"
            ])
        
        elif response_strategy["type"] in ["hybrid", "hybrid_with_data"]:
            prompt_parts.extend([
                "1. Assess what information is available and what's missing",
                "2. Provide helpful attraction suggestions based on available info",
                "3. Ask 1-2 specific questions to fill important gaps",
                "4. Balance being helpful now while gathering more details"
            ])
            
            if "with_data" in response_strategy["type"]:
                prompt_parts.append("5. Integrate current attractions data naturally into recommendations")
        
        elif response_strategy["type"] == "recommendation_focused":
            prompt_parts.extend([
                "1. Analyze all available visitor information and preferences",
                "2. Consider time constraints, interests, and accessibility needs",
                "3. Provide 3-5 specific attraction recommendations with clear reasoning",
                "4. Explain why each attraction matches their stated preferences",
                "5. Include practical considerations (timing, costs, accessibility)"
            ])
        
        else:  # detailed_planning
            prompt_parts.extend([
                "1. Conduct comprehensive analysis of all visitor preferences and constraints",
                "2. Provide detailed attraction recommendations with specific rationale",
                "3. Include timing suggestions, costs, and logistical considerations",
                "4. Suggest optimal routes, must-see highlights, and insider tips",
                "5. Address any special requirements or accessibility needs mentioned"
            ])
        
        prompt_parts.append("")
        
        # 7. Response guidelines tailored to strategy (LENGTH AND QUALITY CONTROL)
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
        
        # 8. External data usage instructions (SMART DATA ROUTING)
        if external_relevance["use_attractions"]:
            prompt_parts.append("External data usage:")
            prompt_parts.append("• USE the current attractions data provided - it's up-to-date and relevant")
            prompt_parts.append("• Reference specific attractions from the data when making recommendations")
            prompt_parts.append("• Combine this current data with your knowledge for comprehensive advice")
        else:
            prompt_parts.append("External data usage:")
            prompt_parts.append("• Rely on your extensive knowledge - external data not relevant for this query")
            prompt_parts.append("• Do not reference attractions data that may be shown above")
        
        prompt_parts.append("")
        
        # 9. Quality and tone guidelines (CONVERSATION QUALITY)
        prompt_parts.extend([
            "Quality standards:",
            "• Be conversational, enthusiastic, and genuinely helpful",
            "• Use specific examples and concrete details when possible",
            "• Demonstrate deep local knowledge while remaining accessible",
            "• Match response length to information available and strategy type",
            "• Use formatting (bullets, emojis) for easy reading when appropriate",
            "• Prioritize attractions based on stated interests and time available",
            "",
            "Generate your attractions recommendation response:"
        ])
        
        # Join all parts into final prompt
        final_prompt = "\n".join(prompt_parts)
        
        # Log prompt engineering details for monitoring
        logger.info(f"Strategic attractions prompt built: strategy={response_strategy['type']}, "
                   f"info_quality={info_analysis['information_quality']}, "
                   f"attractions_used={external_relevance['use_attractions']}")
        
        return final_prompt
    
    def _build_fallback_prompt(self, user_query: str, global_context: List[str], 
                              type_specific_context: List[str]) -> str:
        """
        Fallback prompt when advanced analysis fails.
        Still demonstrates good prompt engineering principles.
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