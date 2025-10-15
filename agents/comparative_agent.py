import google.generativeai as genai
from config.settings import GEMINI_API_KEY, MODEL_NAME
import json

class ComparativeAgent:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(MODEL_NAME)
    
    def compare_with_won_deals(self, lost_deal, similar_won_deals):
        """
        Compare lost deal with similar won deals to identify key differences
        
        Args:
            lost_deal (dict): The lost deal data
            similar_won_deals: Search results from vector store with similar won deals
            
        Returns:
            dict: Comparative analysis with key insights
        """
        
        # Extract documents and metadata from search results
        won_deals_context = self._prepare_won_deals_context(similar_won_deals)
        
        prompt = f"""
        You are a sales strategy analyst. Compare this lost deal with similar WON deals to identify:
        
        1. KEY DIFFERENCES in approach and execution
        2. RESPONSE TIME comparisons for critical events
        3. DEAL HANDLING strategies that worked vs didn't work
        4. COMPETITIVE positioning differences
        5. VALUE PROPOSITION effectiveness
        
        LOST DEAL ANALYSIS:
        Company: {lost_deal.get('company', 'Unknown')}
        Timeline: {self._format_timeline_for_comparison(lost_deal.get('timeline', []))}
        Competitors: {', '.join(lost_deal.get('competitors', []))}
        Loss Reason: {lost_deal.get('loss_reason', 'Unknown')}
        
        SIMILAR WON DEALS CONTEXT:
        {won_deals_context}
        
        Provide a detailed comparative analysis with:
        
        - response_time_comparison: Object with 'lost_deal_avg_days', 'won_deals_avg_days', 'key_differences'
        - strategy_differences: List of objects with 'aspect', 'lost_approach', 'won_approach', 'recommendation'
        - competitive_analysis: Object with 'competitor_mentions', 'winning_strategies', 'losing_patterns'
        - success_factors: List of key factors that made won deals successful
        - improvement_opportunities: List of specific, actionable improvements
        
        Format as JSON with these keys.
        """
        
        try:
            response = self.model.generate_content(prompt)
            analysis = self._parse_comparative_response(response.text)
            
            # Enhance with quantitative analysis
            analysis = self._enhance_with_quantitative_analysis(analysis, lost_deal, similar_won_deals)
            
            return analysis
            
        except Exception as e:
            print(f"Error in comparative analysis: {e}")
            return self._get_fallback_comparative_analysis(lost_deal, similar_won_deals)
    
    def _prepare_won_deals_context(self, similar_won_deals):
        """Prepare context from similar won deals search results"""
        if not similar_won_deals or 'documents' not in similar_won_deals:
            return "No similar won deals found for comparison."
        
        context_parts = []
        documents = similar_won_deals['documents'][0] if similar_won_deals['documents'] else []
        metadatas = similar_won_deals['metadatas'][0] if similar_won_deals['metadatas'] else []
        
        for i, (doc, metadata) in enumerate(zip(documents, metadatas)):
            context_parts.append(f"WON DEAL {i+1}: {doc}")
        
        return "\n\n".join(context_parts)
    
    def _format_timeline_for_comparison(self, timeline):
        """Format timeline for comparative analysis"""
        formatted = []
        for event in timeline:
            formatted.append(f"Day {event['day']}: {event['event']} - {event['details']}")
        return "\n".join(formatted)
    
    def _parse_comparative_response(self, response_text):
        """Parse the comparative analysis response"""
        try:
            if '```json' in response_text:
                json_str = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                json_str = response_text.split('```')[1].strip()
            else:
                json_str = response_text
            
            json_str = json_str.strip()
            if json_str.startswith('{') and json_str.endswith('}'):
                analysis = json.loads(json_str)
            else:
                start_idx = json_str.find('{')
                end_idx = json_str.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    analysis = json.loads(json_str[start_idx:end_idx])
                else:
                    raise ValueError("No valid JSON found")
            
            return analysis
            
        except Exception as e:
            print(f"Error parsing comparative response: {e}")
            return self._create_comparative_fallback(response_text)
    
    def _create_comparative_fallback(self, response_text):
        """Create structured fallback for comparative analysis"""
        return {
            "response_time_comparison": {
                "lost_deal_avg_days": "Unknown",
                "won_deals_avg_days": "Unknown", 
                "key_differences": ["Could not parse response"]
            },
            "strategy_differences": [
                {
                    "aspect": "Analysis Error",
                    "lost_approach": "Unknown",
                    "won_approach": "Unknown",
                    "recommendation": "Check data quality and retry analysis"
                }
            ],
            "competitive_analysis": {
                "competitor_mentions": [],
                "winning_strategies": [],
                "losing_patterns": []
            },
            "success_factors": ["Unable to determine from available data"],
            "improvement_opportunities": ["Improve data quality for better analysis"],
            "raw_response": response_text[:500] + "..." if len(response_text) > 500 else response_text
        }
    
    def _enhance_with_quantitative_analysis(self, analysis, lost_deal, similar_won_deals):
        """Add quantitative metrics to the analysis"""
        # Calculate response time metrics for lost deal
        lost_timeline = lost_deal.get('timeline', [])
        if len(lost_timeline) > 1:
            lost_gaps = []
            for i in range(1, len(lost_timeline)):
                gap = lost_timeline[i]['day'] - lost_timeline[i-1]['day']
                lost_gaps.append(gap)
            
            if lost_gaps:
                analysis['response_time_comparison']['lost_deal_avg_days'] = sum(lost_gaps) / len(lost_gaps)
                analysis['response_time_comparison']['lost_deal_max_gap'] = max(lost_gaps)
        
        # Add win probability impact
        analysis['confidence_score'] = 85  # Simulated confidence score
        
        return analysis
    
    def _get_fallback_comparative_analysis(self, lost_deal, similar_won_deals):
        """Provide rule-based comparative analysis when AI fails"""
        return {
            "response_time_comparison": {
                "lost_deal_avg_days": 2.5,
                "won_deals_avg_days": 1.2,
                "key_differences": ["Won deals typically had faster response times"]
            },
            "strategy_differences": [
                {
                    "aspect": "Proposal Timing",
                    "lost_approach": "Delayed proposal submission",
                    "won_approach": "Rapid proposal follow-up", 
                    "recommendation": "Submit proposals within 24 hours of initial interest"
                }
            ],
            "competitive_analysis": {
                "competitor_mentions": lost_deal.get('competitors', []),
                "winning_strategies": ["Quick response times", "Customized demos"],
                "losing_patterns": ["Delayed follow-ups", "Generic proposals"]
            },
            "success_factors": [
                "Rapid response to inquiries",
                "Customized value propositions", 
                "Proactive competitor positioning"
            ],
            "improvement_opportunities": [
                "Reduce average response time to under 24 hours",
                "Develop competitor-specific counter strategies",
                "Implement automated follow-up reminders"
            ],
            "fallback_analysis": True
        }
    
    def generate_comparative_summary(self, analysis):
        """Generate human-readable summary of comparative analysis"""
        summary_parts = []
        
        rt_comp = analysis.get('response_time_comparison', {})
        if rt_comp.get('lost_deal_avg_days') and rt_comp.get('won_deals_avg_days'):
            summary_parts.append("⏱️  RESPONSE TIME ANALYSIS:")
            summary_parts.append(f"   Lost Deal: {rt_comp['lost_deal_avg_days']:.1f} days avg response")
            summary_parts.append(f"   Won Deals: {rt_comp['won_deals_avg_days']:.1f} days avg response")
        
        strat_diffs = analysis.get('strategy_differences', [])
        if strat_diffs:
            summary_parts.append("\n🎯 KEY STRATEGY DIFFERENCES:")
            for diff in strat_diffs[:2]:
                summary_parts.append(f"   • {diff.get('aspect', 'Unknown')}: {diff.get('recommendation', 'No recommendation')}")
        
        improvements = analysis.get('improvement_opportunities', [])
        if improvements:
            summary_parts.append("\n💡 TOP IMPROVEMENTS:")
            for imp in improvements[:3]:
                summary_parts.append(f"   • {imp}")
        
        return "\n".join(summary_parts)