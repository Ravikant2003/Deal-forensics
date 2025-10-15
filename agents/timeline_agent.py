import google.generativeai as genai
from config.settings import GEMINI_API_KEY, MODEL_NAME
import json

class TimelineAgent:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(MODEL_NAME)
        self.analysis_template = {
            "critical_moments": [],
            "warning_signals": [],
            "failure_point": "",
            "response_time_issues": [],
            "timeline_score": 0,
            "recommendations": []
        }
    
    def analyze_timeline(self, deal_data):
        """
        Analyze deal timeline to identify critical moments and failure points
        
        Args:
            deal_data (dict): Deal information including timeline events
            
        Returns:
            dict: Comprehensive timeline analysis
        """
        
        # Prepare context for the AI
        timeline_context = self._prepare_timeline_context(deal_data)
        
        prompt = f"""
        You are a sales forensic analyst. Analyze this sales deal timeline and provide a detailed analysis.
        
        DEAL INFORMATION:
        Company: {deal_data.get('company', 'Unknown')}
        Deal Value: ${deal_data.get('value', 0):,}
        Competitors: {', '.join(deal_data.get('competitors', []))}
        
        TIMELINE EVENTS:
        {timeline_context}
        
        Please analyze this timeline and provide:
        
        1. CRITICAL MOMENTS: Identify 3-5 key moments that significantly impacted the deal outcome
        2. WARNING SIGNALS: List specific warning signs and when they occurred
        3. FAILURE POINT: Identify the exact moment when the deal started going wrong
        4. RESPONSE TIME ANALYSIS: Analyze response times and delays
        5. TIMELINE SCORE: Rate the overall timeline management from 1-10
        6. IMMEDIATE RECOMMENDATIONS: 2-3 specific actions to improve timeline management
        
        Format your response as a JSON object with these keys:
        - critical_moments: list of objects with 'day', 'event', 'impact' (positive/negative), 'description'
        - warning_signals: list of objects with 'day', 'signal', 'severity' (low/medium/high), 'description'
        - failure_point: object with 'day', 'event', 'reason', 'recoverable' (yes/no)
        - response_time_issues: list of objects with 'delay_days', 'event', 'impact'
        - timeline_score: integer from 1-10
        - recommendations: list of strings with specific actions
        
        Be specific and data-driven in your analysis.
        """
        
        try:
            response = self.model.generate_content(prompt)
            analysis = self._parse_analysis_response(response.text)
            
            # Enhance with additional calculations
            analysis = self._enhance_with_calculations(analysis, deal_data)
            
            return analysis
            
        except Exception as e:
            print(f"Error in timeline analysis: {e}")
            return self._get_fallback_analysis(deal_data)
    
    def _prepare_timeline_context(self, deal_data):
        """Prepare formatted timeline context for the AI"""
        timeline_events = deal_data.get('timeline', [])
        
        context_lines = []
        for event in timeline_events:
            day = event.get('day', 0)
            event_type = event.get('event', 'Unknown')
            details = event.get('details', '')
            context_lines.append(f"Day {day}: {event_type} - {details}")
        
        return "\n".join(context_lines)
    
    def _parse_analysis_response(self, response_text):
        """Parse the AI response into structured JSON"""
        try:
            # Extract JSON from response (handling cases where response has extra text)
            if '```json' in response_text:
                json_str = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                json_str = response_text.split('```')[1].strip()
            else:
                json_str = response_text
            
            # Clean the JSON string
            json_str = json_str.strip()
            if json_str.startswith('{') and json_str.endswith('}'):
                analysis = json.loads(json_str)
            else:
                # Fallback: try to find JSON object
                start_idx = json_str.find('{')
                end_idx = json_str.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    analysis = json.loads(json_str[start_idx:end_idx])
                else:
                    raise ValueError("No valid JSON found")
            
            return analysis
            
        except Exception as e:
            print(f"Error parsing AI response: {e}")
            return self._create_structured_fallback(response_text)
    
    def _create_structured_fallback(self, response_text):
        """Create structured analysis from unstructured response"""
        return {
            "critical_moments": [
                {
                    "day": 0,
                    "event": "Analysis Error",
                    "impact": "negative",
                    "description": "Failed to parse AI response"
                }
            ],
            "warning_signals": [
                {
                    "day": 0,
                    "signal": "Parsing Error",
                    "severity": "medium",
                    "description": "Could not parse the analysis response"
                }
            ],
            "failure_point": {
                "day": 0,
                "event": "Analysis Failure",
                "reason": "Technical error in parsing response",
                "recoverable": "yes"
            },
            "response_time_issues": [],
            "timeline_score": 5,
            "recommendations": [
                "Check the AI response format",
                "Verify the input data quality"
            ],
            "raw_response": response_text[:500] + "..." if len(response_text) > 500 else response_text
        }
    
    def _enhance_with_calculations(self, analysis, deal_data):
        """Enhance analysis with calculated metrics"""
        timeline_events = deal_data.get('timeline', [])
        
        # Calculate response time metrics
        if len(timeline_events) > 1:
            total_days = timeline_events[-1]['day'] - timeline_events[0]['day']
            analysis['total_duration_days'] = total_days
            
            # Calculate average time between events
            if len(timeline_events) > 1:
                time_gaps = []
                for i in range(1, len(timeline_events)):
                    gap = timeline_events[i]['day'] - timeline_events[i-1]['day']
                    time_gaps.append(gap)
                
                analysis['avg_response_days'] = sum(time_gaps) / len(time_gaps)
                analysis['max_response_gap'] = max(time_gaps) if time_gaps else 0
        
        # Add timeline density metric
        if 'total_duration_days' in analysis and analysis['total_duration_days'] > 0:
            analysis['timeline_density'] = len(timeline_events) / analysis['total_duration_days']
        
        return analysis
    
    def _get_fallback_analysis(self, deal_data):
        """Provide fallback analysis when AI fails"""
        timeline_events = deal_data.get('timeline', [])
        
        # Simple rule-based analysis as fallback
        critical_moments = []
        warning_signals = []
        response_issues = []
        
        for i, event in enumerate(timeline_events):
            event_lower = event.get('event', '').lower()
            details_lower = event.get('details', '').lower()
            
            # Identify critical moments
            if any(word in event_lower for word in ['proposal', 'demo', 'meeting', 'pricing']):
                critical_moments.append({
                    "day": event['day'],
                    "event": event['event'],
                    "impact": "positive" if 'positive' in details_lower else "negative",
                    "description": event['details']
                })
            
            # Identify warning signals
            if any(word in details_lower for word in ['delay', 'ghost', 'concern', 'competitor', 'budget']):
                warning_signals.append({
                    "day": event['day'],
                    "signal": "Potential Issue",
                    "severity": "medium",
                    "description": event['details']
                })
            
            # Identify response time issues
            if i > 0:
                gap = event['day'] - timeline_events[i-1]['day']
                if gap > 2:  # More than 2 days between events
                    response_issues.append({
                        "delay_days": gap,
                        "event": event['event'],
                        "impact": "Potential loss of momentum"
                    })
        
        # Determine failure point (last negative event)
        failure_event = None
        for event in reversed(timeline_events):
            if any(word in event.get('details', '').lower() for word in ['ghost', 'lost', 'competitor', 'no response']):
                failure_event = event
                break
        
        return {
            "critical_moments": critical_moments[:3],
            "warning_signals": warning_signals[:3],
            "failure_point": {
                "day": failure_event['day'] if failure_event else timeline_events[-1]['day'],
                "event": failure_event['event'] if failure_event else "Unknown",
                "reason": "Identified through pattern matching",
                "recoverable": "yes"
            },
            "response_time_issues": response_issues,
            "timeline_score": 6,
            "recommendations": [
                "Reduce response times between key events",
                "Monitor for warning signals more proactively",
                "Implement automated follow-up system"
            ],
            "fallback_analysis": True
        }
    
    def generate_timeline_summary(self, analysis):
        """Generate a human-readable summary of the timeline analysis"""
        summary_parts = []
        
        if analysis.get('failure_point'):
            fp = analysis['failure_point']
            summary_parts.append(f"🚨 CRITICAL FAILURE: Day {fp.get('day', 'Unknown')} - {fp.get('event', 'Unknown event')}")
            summary_parts.append(f"   Reason: {fp.get('reason', 'Not specified')}")
            summary_parts.append(f"   Recoverable: {fp.get('recoverable', 'Unknown')}")
        
        if analysis.get('warning_signals'):
            summary_parts.append("\n⚠️  WARNING SIGNALS:")
            for signal in analysis['warning_signals'][:3]:
                summary_parts.append(f"   Day {signal.get('day', 'Unknown')}: {signal.get('signal', 'Unknown')} ({signal.get('severity', 'Unknown')})")
        
        if analysis.get('timeline_score'):
            summary_parts.append(f"\n📊 TIMELINE SCORE: {analysis['timeline_score']}/10")
        
        if analysis.get('recommendations'):
            summary_parts.append("\n💡 RECOMMENDATIONS:")
            for rec in analysis['recommendations'][:2]:
                summary_parts.append(f"   • {rec}")
        
        return "\n".join(summary_parts)