import os
import json
import time
from datetime import datetime
import re

class Helpers:
    @staticmethod
    def setup_environment():
        """Setup environment variables and check requirements"""
        required_vars = ['GEMINI_API_KEY']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
            print("Please set these variables in your environment or .env file")
            return False
        
        print("✅ Environment setup complete")
        return True
    
    @staticmethod
    def format_timestamp():
        """Get current timestamp in readable format"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def calculate_execution_time(func):
        """Decorator to calculate function execution time"""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            print(f"⏱️  {func.__name__} executed in {execution_time:.2f} seconds")
            return result
        return wrapper
    
    @staticmethod
    def validate_deal_data(deal_data):
        """Validate deal data structure"""
        required_fields = ['deal_id', 'company', 'timeline']
        
        if not isinstance(deal_data, dict):
            return False, "Deal data must be a dictionary"
        
        missing_fields = [field for field in required_fields if field not in deal_data]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Validate timeline structure
        timeline = deal_data.get('timeline', [])
        if not isinstance(timeline, list):
            return False, "Timeline must be a list"
        
        for event in timeline:
            if not all(key in event for key in ['day', 'event', 'details']):
                return False, "Each timeline event must have 'day', 'event', and 'details'"
        
        return True, "Deal data is valid"
    
    @staticmethod
    def extract_competitor_names(text):
        """Extract competitor names from text using pattern matching"""
        if not text:
            return []
        
        # Common competitor patterns
        patterns = [
            r'competitor\s+([A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+(?:Inc|Corp|LLC|Ltd))',
            r'competing with\s+([A-Z][a-z]+)',
            r'vs\.?\s+([A-Z][a-z]+)'
        ]
        
        competitors = set()
        text_lower = text.lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            competitors.update(matches)
        
        return list(competitors)
    
    @staticmethod
    def calculate_confidence_score(analysis_data):
        """Calculate confidence score for analysis results"""
        score = 50  # Base score
        
        # Increase score based on data completeness
        if analysis_data.get('timeline_analysis'):
            score += 10
        
        if analysis_data.get('comparative_analysis'):
            score += 15
        
        if analysis_data.get('playbook'):
            score += 15
        
        # Decrease score for fallback analyses
        if analysis_data.get('timeline_analysis', {}).get('fallback_analysis'):
            score -= 20
        
        if analysis_data.get('comparative_analysis', {}).get('fallback_analysis'):
            score -= 15
        
        if analysis_data.get('playbook', {}).get('fallback_playbook'):
            score -= 15
        
        return max(0, min(100, score))
    
    @staticmethod
    def format_currency(amount):
        """Format amount as currency"""
        try:
            return "${:,.2f}".format(float(amount))
        except (ValueError, TypeError):
            return "$0.00"
    
    @staticmethod
    def generate_deal_summary(deal_data):
        """Generate a quick summary of deal data"""
        timeline = deal_data.get('timeline', [])
        if not timeline:
            return "No timeline data available"
        
        first_event = timeline[0]
        last_event = timeline[-1]
        duration = last_event['day'] - first_event['day']
        
        summary = [
            f"🏢 Company: {deal_data.get('company', 'Unknown')}",
            f"💰 Value: {Helpers.format_currency(deal_data.get('value', 0))}",
            f"📅 Duration: {duration} days",
            f"📊 Events: {len(timeline)} timeline events",
            f"🎯 Last Event: {last_event['event']} (Day {last_event['day']})"
        ]
        
        if deal_data.get('competitors'):
            summary.append(f"⚔️  Competitors: {', '.join(deal_data['competitors'])}")
        
        return "\n".join(summary)
    
    @staticmethod
    def save_analysis_results(deal_id, analysis_results, output_dir="output"):
        """Save analysis results to JSON file"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            filename = f"{output_dir}/analysis_{deal_id}_{int(time.time())}.json"
            
            with open(filename, 'w') as f:
                json.dump(analysis_results, f, indent=2)
            
            print(f"💾 Analysis results saved to: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving analysis results: {e}")
            return False
    
    @staticmethod
    def load_analysis_results(filename):
        """Load analysis results from JSON file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading analysis results: {e}")
            return None
    
    @staticmethod
    def create_demo_highlights(analysis_results):
        """Create demo highlights for presentation"""
        highlights = []
        
        timeline_analysis = analysis_results.get('timeline_analysis', {})
        comparative_analysis = analysis_results.get('comparative_analysis', {})
        playbook = analysis_results.get('playbook', {})
        
        # Timeline highlights
        if timeline_analysis.get('failure_point'):
            fp = timeline_analysis['failure_point']
            highlights.append(f"🔍 Identified critical failure point: Day {fp.get('day')} - {fp.get('event')}")
        
        if timeline_analysis.get('timeline_score'):
            highlights.append(f"📊 Timeline management score: {timeline_analysis['timeline_score']}/10")
        
        # Comparative highlights
        rt_comp = comparative_analysis.get('response_time_comparison', {})
        if rt_comp.get('lost_deal_avg_days') and rt_comp.get('won_deals_avg_days'):
            improvement = ((rt_comp['won_deals_avg_days'] - rt_comp['lost_deal_avg_days']) / rt_comp['lost_deal_avg_days']) * 100
            highlights.append(f"⏱️  Response time improvement opportunity: {improvement:.1f}%")
        
        # Playbook highlights
        immediate_actions = playbook.get('immediate_actions', [])
        if immediate_actions:
            high_priority = [action for action in immediate_actions if action.get('priority') == 'high']
            if high_priority:
                highlights.append(f"🎯 {len(high_priority)} high-priority actions identified")
        
        return highlights
    
    @staticmethod
    def check_api_health():
        """Check if required APIs are accessible"""
        # This would typically check API endpoints
        # For now, just check environment variables
        if os.getenv('GEMINI_API_KEY'):
            return True, "Gemini API: ✅ Configured"
        else:
            return False, "Gemini API: ❌ Missing API Key"