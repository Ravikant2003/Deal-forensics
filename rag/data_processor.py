import json
import pandas as pd
from datetime import datetime, timedelta
import re

class DataProcessor:
    def __init__(self):
        self.sample_data = self._load_sample_data()
    
    def _load_sample_data(self):
        """Load sample deals data from JSON file"""
        try:
            with open('data/sample_deals.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                "sample_deals.json not found in data folder. "
                "Please ensure the data file exists in the data/ directory."
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in sample_deals.json: {e}")
        except Exception as e:
            raise Exception(f"Error loading sample data: {e}")
    
    def get_lost_deal_by_id(self, deal_id):
        """Get specific lost deal by ID"""
        for deal in self.sample_data.get('lost_deals', []):
            if deal['deal_id'] == deal_id:
                return deal
        return None
    
    def get_all_lost_deals(self):
        """Get all lost deals"""
        return self.sample_data.get('lost_deals', [])
    
    def get_won_deals_for_comparison(self, lost_deal, n=2):
        """Get won deals for comparative analysis"""
        won_deals = self.sample_data.get('won_deals', [])
        
        # Simple similarity matching based on industry and value range
        similar_deals = []
        for deal in won_deals:
            similarity_score = self._calculate_deal_similarity(lost_deal, deal)
            if similarity_score > 0.3:  # Threshold for similarity
                similar_deals.append((deal, similarity_score))
        
        # Sort by similarity and return top N
        similar_deals.sort(key=lambda x: x[1], reverse=True)
        return [deal[0] for deal in similar_deals[:n]]
    
    def _calculate_deal_similarity(self, deal1, deal2):
        """Calculate similarity between two deals"""
        score = 0
        
        # Industry similarity
        if deal1.get('industry') == deal2.get('industry'):
            score += 0.4
        
        # Value range similarity (within 50%)
        val1 = deal1.get('value', 0)
        val2 = deal2.get('value', 0)
        if val1 > 0 and val2 > 0:
            ratio = min(val1, val2) / max(val1, val2)
            if ratio > 0.5:
                score += 0.3
        
        # Competitor overlap
        comp1 = set(deal1.get('competitors', []))
        comp2 = set(deal2.get('competitors', []))
        if comp1 & comp2:  # Intersection
            score += 0.3
        
        return score
    
    def extract_timeline_metrics(self, deal):
        """Extract quantitative metrics from deal timeline"""
        timeline = deal.get('timeline', [])
        if not timeline:
            return {}
        
        days = [event['day'] for event in timeline]
        total_duration = max(days) - min(days) if days else 0
        
        # Calculate response gaps
        gaps = []
        for i in range(1, len(timeline)):
            gap = timeline[i]['day'] - timeline[i-1]['day']
            gaps.append(gap)
        
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        max_gap = max(gaps) if gaps else 0
        
        # Identify critical events
        critical_events = []
        for event in timeline:
            event_lower = event['event'].lower()
            if any(keyword in event_lower for keyword in ['proposal', 'demo', 'pricing', 'competitor', 'budget']):
                critical_events.append(event)
        
        return {
            'total_duration_days': total_duration,
            'number_of_events': len(timeline),
            'avg_response_gap_days': avg_gap,
            'max_response_gap_days': max_gap,
            'timeline_density': len(timeline) / total_duration if total_duration > 0 else 0,
            'critical_events_count': len(critical_events)
        }
    
    def prepare_deal_for_analysis(self, deal_id):
        """Prepare complete deal data for analysis"""
        deal = self.get_lost_deal_by_id(deal_id)
        if not deal:
            return None
        
        # Add calculated metrics
        metrics = self.extract_timeline_metrics(deal)
        deal['metrics'] = metrics
        
        # Get similar won deals for comparison
        similar_won_deals = self.get_won_deals_for_comparison(deal)
        deal['similar_won_deals'] = similar_won_deals
        
        return deal
    
    def get_deal_statistics(self):
        """Get overall statistics for all deals"""
        lost_deals = self.get_all_lost_deals()
        won_deals = self.sample_data.get('won_deals', [])
        
        stats = {
            'total_lost_deals': len(lost_deals),
            'total_won_deals': len(won_deals),
            'total_deal_value_lost': sum(deal.get('value', 0) for deal in lost_deals),
            'total_deal_value_won': sum(deal.get('value', 0) for deal in won_deals),
            'common_loss_reasons': self._get_common_loss_reasons(lost_deals),
            'avg_deal_duration_lost': self._get_avg_deal_duration(lost_deals),
            'avg_deal_duration_won': self._get_avg_deal_duration(won_deals)
        }
        
        return stats
    
    def _get_common_loss_reasons(self, lost_deals):
        """Get most common loss reasons"""
        reasons = {}
        for deal in lost_deals:
            reason = deal.get('loss_reason', 'unknown')
            reasons[reason] = reasons.get(reason, 0) + 1
        return dict(sorted(reasons.items(), key=lambda x: x[1], reverse=True))
    
    def _get_avg_deal_duration(self, deals):
        """Calculate average deal duration"""
        durations = []
        for deal in deals:
            timeline = deal.get('timeline', [])
            if timeline:
                days = [event['day'] for event in timeline]
                duration = max(days) - min(days)
                durations.append(duration)
        
        return sum(durations) / len(durations) if durations else 0