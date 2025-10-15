import google.generativeai as genai
from config.settings import GEMINI_API_KEY, MODEL_NAME

class AgentOrchestrator:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(MODEL_NAME)
    
    def generate_response(self, prompt, context=""):
        full_prompt = f"{context}\n\n{prompt}"
        response = self.model.generate_content(full_prompt)
        return response.text

# Timeline Agent
class TimelineAgent(AgentOrchestrator):
    def analyze_timeline(self, deal_data):
        prompt = f"""
        Analyze this sales deal timeline and identify:
        1. Key positive moments
        2. Warning signals and when they occurred
        3. The exact moment things started going wrong
        4. Response time issues
        
        Deal Timeline: {deal_data['timeline']}
        """
        return self.generate_response(prompt)

# Comparative Agent  
class ComparativeAgent(AgentOrchestrator):
    def compare_with_won_deals(self, lost_deal, won_deals_context):
        prompt = f"""
        Compare this lost deal with similar won deals and identify:
        1. Key differences in response times
        2. Different approaches to objections
        3. Missing actions in the lost deal
        4. Best practices from won deals
        
        Lost Deal: {lost_deal}
        Won Deals Context: {won_deals_context}
        """
        return self.generate_response(prompt)

# Playbook Agent
class PlaybookAgent(AgentOrchestrator):
    def generate_playbook(self, analysis_results):
        prompt = f"""
        Based on the deal analysis, create an actionable playbook with:
        1. Specific triggers to watch for
        2. Recommended immediate actions
        3. Response templates for common objections
        4. Timing guidelines
        
        Analysis: {analysis_results}
        """
        return self.generate_response(prompt)