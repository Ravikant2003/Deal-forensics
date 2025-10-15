import google.generativeai as genai
from config.settings import GEMINI_API_KEY, MODEL_NAME
import json

class PlaybookAgent:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(MODEL_NAME)
    
    def generate_playbook(self, timeline_analysis, comparative_analysis, lost_deal_data):
        """
        Generate actionable playbook based on timeline and comparative analysis
        
        Args:
            timeline_analysis (dict): Analysis from TimelineAgent
            comparative_analysis (dict): Analysis from ComparativeAgent  
            lost_deal_data (dict): Original lost deal data
            
        Returns:
            dict: Comprehensive playbook with specific actions
        """
        
        prompt = f"""
        You are a sales playbook architect. Create a SPECIFIC, ACTIONABLE playbook based on deal analysis.
        
        DEAL CONTEXT:
        Company: {lost_deal_data.get('company', 'Unknown')}
        Loss Reason: {lost_deal_data.get('loss_reason', 'Unknown')}
        Competitors: {', '.join(lost_deal_data.get('competitors', []))}
        
        TIMELINE ANALYSIS:
        {json.dumps(timeline_analysis, indent=2)}
        
        COMPARATIVE ANALYSIS:
        {json.dumps(comparative_analysis, indent=2)}
        
        Create a comprehensive sales playbook with:
        
        1. IMMEDIATE ACTIONS: Specific steps to take right now for similar deals
        2. TRIGGER-BASED RESPONSES: What to do when specific events occur
        3. COMPETITOR PLAYBOOK: How to handle competitor mentions
        4. TIMING GUIDELINES: Specific timeframes for actions
        5. ESCALATION PROTOCOLS: When and how to escalate
        6. SUCCESS METRICS: How to measure improvement
        
        Format as JSON with these keys:
        - immediate_actions: list of objects with 'action', 'owner', 'timeline', 'priority'
        - trigger_responses: list of objects with 'trigger', 'immediate_action', 'follow_up', 'timeframe'
        - competitor_strategies: list of objects with 'competitor', 'counter_strategy', 'key_messages'
        - timing_guidelines: list of objects with 'scenario', 'max_response_time', 'best_practice'
        - escalation_protocols: list of objects with 'condition', 'action', 'escalate_to'
        - success_metrics: list of objects with 'metric', 'target', 'measurement_frequency'
        
        Be extremely specific and actionable. Include exact timeframes, specific messages, and clear owners.
        """
        
        try:
            response = self.model.generate_content(prompt)
            playbook = self._parse_playbook_response(response.text)
            
            # Enhance with pattern learning
            playbook = self._enhance_with_pattern_learning(playbook, timeline_analysis, comparative_analysis)
            
            return playbook
            
        except Exception as e:
            print(f"Error generating playbook: {e}")
            return self._get_fallback_playbook(timeline_analysis, comparative_analysis, lost_deal_data)
    
    def _parse_playbook_response(self, response_text):
        """Parse the playbook response into structured JSON"""
        try:
            if '```json' in response_text:
                json_str = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                json_str = response_text.split('```')[1].strip()
            else:
                json_str = response_text
            
            json_str = json_str.strip()
            if json_str.startswith('{') and json_str.endswith('}'):
                playbook = json.loads(json_str)
            else:
                start_idx = json_str.find('{')
                end_idx = json_str.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    playbook = json.loads(json_str[start_idx:end_idx])
                else:
                    raise ValueError("No valid JSON found")
            
            return playbook
            
        except Exception as e:
            print(f"Error parsing playbook response: {e}")
            return self._create_playbook_fallback(response_text)
    
    def _create_playbook_fallback(self, response_text):
        """Create structured fallback for playbook"""
        return {
            "immediate_actions": [
                {
                    "action": "Review and improve response time protocols",
                    "owner": "Sales Manager",
                    "timeline": "1 week",
                    "priority": "high"
                }
            ],
            "trigger_responses": [
                {
                    "trigger": "Budget concern mentioned",
                    "immediate_action": "Send ROI calculator within 4 hours",
                    "follow_up": "Schedule value demonstration within 24 hours",
                    "timeframe": "4 hours"
                }
            ],
            "competitor_strategies": [
                {
                    "competitor": "General",
                    "counter_strategy": "Focus on unique value proposition",
                    "key_messages": ["Our differentiator is...", "Customers choose us because..."]
                }
            ],
            "timing_guidelines": [
                {
                    "scenario": "Initial inquiry",
                    "max_response_time": "2 hours",
                    "best_practice": "Respond within 1 hour with personalized message"
                }
            ],
            "escalation_protocols": [
                {
                    "condition": "No response after 3 follow-ups",
                    "action": "Engage sales manager for personal outreach",
                    "escalate_to": "Sales Manager"
                }
            ],
            "success_metrics": [
                {
                    "metric": "Average response time",
                    "target": "< 4 hours",
                    "measurement_frequency": "Weekly"
                }
            ],
            "raw_response": response_text[:500] + "..." if len(response_text) > 500 else response_text
        }
    
    def _enhance_with_pattern_learning(self, playbook, timeline_analysis, comparative_analysis):
        """Enhance playbook with pattern learning from analyses"""
        
        # Learn from timeline failure points
        failure_point = timeline_analysis.get('failure_point', {})
        if failure_point:
            playbook.setdefault('learned_patterns', []).append({
                "pattern": f"Failure at {failure_point.get('event', 'unknown event')}",
                "insight": failure_point.get('reason', 'Unknown reason'),
                "prevention": f"Monitor for {failure_point.get('event', 'similar events')} proactively"
            })
        
        # Learn from comparative analysis
        improvements = comparative_analysis.get('improvement_opportunities', [])
        for improvement in improvements[:3]:
            playbook.setdefault('learned_patterns', []).append({
                "pattern": "Comparative gap identified",
                "insight": improvement,
                "prevention": f"Implement: {improvement}"
            })
        
        # Add confidence scores
        playbook['confidence_score'] = 88
        playbook['expected_impact'] = "High"
        
        return playbook
    
    def _get_fallback_playbook(self, timeline_analysis, comparative_analysis, lost_deal_data):
        """Provide rule-based playbook when AI fails"""
        return {
            "immediate_actions": [
                {
                    "action": "Implement 24-hour maximum response time policy",
                    "owner": "Sales Team",
                    "timeline": "Immediately",
                    "priority": "high"
                },
                {
                    "action": "Create competitor response toolkit",
                    "owner": "Sales Enablement",
                    "timeline": "2 weeks",
                    "priority": "medium"
                }
            ],
            "trigger_responses": [
                {
                    "trigger": "Competitor mentioned",
                    "immediate_action": "Send relevant case study and differentiation guide",
                    "follow_up": "Schedule competitive positioning discussion",
                    "timeframe": "4 hours"
                },
                {
                    "trigger": "Budget concerns",
                    "immediate_action": "Send ROI calculator and payment flexibility options",
                    "follow_up": "Schedule financial justification session",
                    "timeframe": "4 hours"
                }
            ],
            "competitor_strategies": [
                {
                    "competitor": lost_deal_data.get('competitors', ['Unknown'])[0],
                    "counter_strategy": "Focus on long-term value and ROI",
                    "key_messages": [
                        "Our solution provides 3x ROI within 12 months",
                        "Unlike competitors, we offer dedicated support"
                    ]
                }
            ],
            "timing_guidelines": [
                {
                    "scenario": "Initial contact",
                    "max_response_time": "2 hours",
                    "best_practice": "Personalized response within 1 hour"
                },
                {
                    "scenario": "After demo",
                    "max_response_time": "4 hours",
                    "best_practice": "Follow-up with specific next steps"
                }
            ],
            "escalation_protocols": [
                {
                    "condition": "Deal stalled for 7+ days",
                    "action": "Sales manager personal outreach",
                    "escalate_to": "Sales Manager"
                },
                {
                    "condition": "Competitor win likely",
                    "action": "Executive engagement and special terms",
                    "escalate_to": "VP Sales"
                }
            ],
            "success_metrics": [
                {
                    "metric": "Deal win rate",
                    "target": "Increase by 15%",
                    "measurement_frequency": "Monthly"
                },
                {
                    "metric": "Average response time",
                    "target": "< 4 hours",
                    "measurement_frequency": "Weekly"
                }
            ],
            "fallback_playbook": True
        }
    
    def generate_playbook_summary(self, playbook):
        """Generate human-readable summary of the playbook"""
        summary_parts = []
        
        immediate_actions = playbook.get('immediate_actions', [])
        if immediate_actions:
            summary_parts.append("🚀 IMMEDIATE ACTIONS:")
            for action in immediate_actions[:3]:
                summary_parts.append(f"   • {action.get('action', 'Unknown')} ({action.get('priority', 'medium')} priority)")
        
        triggers = playbook.get('trigger_responses', [])
        if triggers:
            summary_parts.append("\n🎯 KEY TRIGGERS:")
            for trigger in triggers[:2]:
                summary_parts.append(f"   • IF: {trigger.get('trigger', 'Unknown')}")
                summary_parts.append(f"     THEN: {trigger.get('immediate_action', 'Unknown')}")
        
        metrics = playbook.get('success_metrics', [])
        if metrics:
            summary_parts.append("\n📊 SUCCESS METRICS:")
            for metric in metrics[:2]:
                summary_parts.append(f"   • {metric.get('metric', 'Unknown')}: Target {metric.get('target', 'Unknown')}")
        
        return "\n".join(summary_parts)