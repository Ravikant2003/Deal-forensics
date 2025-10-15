import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from plotly.subplots import make_subplots

class DealVisualizer:
    def __init__(self):
        self.color_scheme = {
            'positive': '#00C851',
            'negative': '#ff4444',
            'warning': '#ffbb33',
            'neutral': '#33b5e5',
            'critical': '#aa66cc'
        }
    
    def create_timeline_visualization(self, deal_data, analysis_results):
        """Create interactive timeline visualization"""
        timeline_events = deal_data.get('timeline', [])
        
        if not timeline_events:
            return self._create_empty_plot("No timeline data available")
        
        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Extract events and days
        events = [event['event'] for event in timeline_events]
        days = [event['day'] for event in timeline_events]
        details = [event['details'] for event in timeline_events]
        
        # Determine event colors based on analysis
        colors = self._get_event_colors(timeline_events, analysis_results)
        
        # Add main timeline trace
        fig.add_trace(
            go.Scatter(
                x=days,
                y=[1] * len(days),  # Constant y for main timeline
                mode='markers+lines+text',
                marker=dict(
                    size=20,
                    color=colors,
                    line=dict(width=2, color='darkgrey')
                ),
                line=dict(color='grey', width=2),
                text=events,
                textposition="middle right",
                textfont=dict(size=10),
                hovertemplate=(
                    "<b>Day %{x}</b><br>" +
                    "<b>%{text}</b><br>" +
                    "Details: %{customdata}<br>" +
                    "<extra></extra>"
                ),
                customdata=details,
                name="Timeline Events"
            ),
            secondary_y=False,
        )
        
        # Add critical moments if available
        critical_moments = analysis_results.get('critical_moments', [])
        if critical_moments:
            crit_days = [moment['day'] for moment in critical_moments]
            crit_events = [moment['event'] for moment in critical_moments]
            
            fig.add_trace(
                go.Scatter(
                    x=crit_days,
                    y=[1.2] * len(crit_days),
                    mode='markers',
                    marker=dict(
                        size=15,
                        color=self.color_scheme['critical'],
                        symbol='star'
                    ),
                    name="Critical Moments",
                    hovertemplate=(
                        "<b>CRITICAL: Day %{x}</b><br>" +
                        "<b>%{text}</b><br>" +
                        "<extra></extra>"
                    ),
                    text=crit_events
                ),
                secondary_y=False,
            )
        
        # Add warning signals if available
        warning_signals = analysis_results.get('warning_signals', [])
        if warning_signals:
            warn_days = [signal['day'] for signal in warning_signals]
            warn_signals = [signal['signal'] for signal in warning_signals]
            
            fig.add_trace(
                go.Scatter(
                    x=warn_days,
                    y=[0.8] * len(warn_days),
                    mode='markers',
                    marker=dict(
                        size=12,
                        color=self.color_scheme['warning'],
                        symbol='triangle-up'
                    ),
                    name="Warning Signals",
                    hovertemplate=(
                        "<b>WARNING: Day %{x}</b><br>" +
                        "<b>%{text}</b><br>" +
                        "<extra></extra>"
                    ),
                    text=warn_signals
                ),
                secondary_y=False,
            )
        
        # Update layout
        fig.update_layout(
            title=f"Deal Timeline Analysis - {deal_data.get('company', 'Unknown Company')}",
            xaxis_title="Days",
            showlegend=True,
            height=400,
            margin=dict(l=20, r=20, t=60, b=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        fig.update_yaxes(
            showticklabels=False,
            secondary_y=False,
            range=[0.5, 1.5]
        )
        
        return fig
    
    def _get_event_colors(self, timeline_events, analysis_results):
        """Determine colors for timeline events based on analysis"""
        colors = []
        failure_point = analysis_results.get('failure_point', {})
        failure_day = failure_point.get('day')
        
        for event in timeline_events:
            day = event['day']
            event_text = event['event'].lower() + " " + event['details'].lower()
            
            if day == failure_day:
                colors.append(self.color_scheme['critical'])
            elif any(word in event_text for word in ['ghost', 'lost', 'no response', 'competitor', 'budget concern']):
                colors.append(self.color_scheme['negative'])
            elif any(word in event_text for word in ['positive', 'won', 'signed', 'approved', 'interested']):
                colors.append(self.color_scheme['positive'])
            elif any(word in event_text for word in ['delay', 'concern', 'issue', 'waiting']):
                colors.append(self.color_scheme['warning'])
            else:
                colors.append(self.color_scheme['neutral'])
        
        return colors
    
    def create_comparative_analysis_chart(self, comparative_analysis):
        """Create comparative analysis visualization"""
        if not comparative_analysis:
            return self._create_empty_plot("No comparative analysis data")
        
        # Extract response time comparison
        rt_comp = comparative_analysis.get('response_time_comparison', {})
        lost_avg = rt_comp.get('lost_deal_avg_days', 0)
        won_avg = rt_comp.get('won_deals_avg_days', 0)
        
        # Create bar chart for response times
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=['Lost Deal Avg', 'Won Deals Avg'],
            y=[lost_avg, won_avg],
            marker_color=[self.color_scheme['negative'], self.color_scheme['positive']],
            text=[f'{lost_avg:.1f} days', f'{won_avg:.1f} days'],
            textposition='auto',
        ))
        
        fig.update_layout(
            title="Response Time Comparison: Lost vs Won Deals",
            yaxis_title="Average Response Time (Days)",
            showlegend=False,
            height=300
        )
        
        return fig
    
    def create_improvement_opportunities_chart(self, playbook):
        """Create visualization of improvement opportunities"""
        if not playbook:
            return self._create_empty_plot("No playbook data available")
        
        immediate_actions = playbook.get('immediate_actions', [])
        
        if not immediate_actions:
            return self._create_empty_plot("No immediate actions defined")
        
        # Extract actions and priorities
        actions = [action['action'][:50] + '...' if len(action['action']) > 50 else action['action'] 
                  for action in immediate_actions]
        priorities = [action['priority'] for action in immediate_actions]
        
        # Convert priorities to numerical values for sorting
        priority_map = {'high': 3, 'medium': 2, 'low': 1}
        priority_values = [priority_map.get(priority, 1) for priority in priorities]
        
        # Create horizontal bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=actions,
            x=priority_values,
            orientation='h',
            marker_color=[self.color_scheme['critical'] if p == 3 else 
                         self.color_scheme['warning'] if p == 2 else 
                         self.color_scheme['neutral'] for p in priority_values],
            text=priorities,
            textposition='auto',
        ))
        
        fig.update_layout(
            title="Immediate Improvement Actions (by Priority)",
            xaxis_title="Priority Level",
            yaxis_title="Actions",
            height=400,
            margin=dict(l=150, r=20, t=60, b=20)
        )
        
        return fig
    
    def create_success_metrics_gauge(self, playbook):
        """Create gauge chart for success metrics"""
        if not playbook:
            return self._create_empty_plot("No playbook data available")
        
        success_metrics = playbook.get('success_metrics', [])
        
        if not success_metrics:
            return self._create_empty_plot("No success metrics defined")
        
        # Take the first metric for the gauge
        metric = success_metrics[0]
        metric_name = metric.get('metric', 'Success Metric')
        target = metric.get('target', '100%')
        
        # Extract numerical value from target if possible
        try:
            target_value = float(''.join(filter(str.isdigit, target)))
            if target_value > 100:
                target_value = 100
        except:
            target_value = 85  # Default value
        
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = target_value,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': f"{metric_name} Target"},
            delta = {'reference': target_value * 0.7, 'increasing': {'color': self.color_scheme['positive']}},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': self.color_scheme['positive']},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 50], 'color': self.color_scheme['negative']},
                    {'range': [50, 80], 'color': self.color_scheme['warning']},
                    {'range': [80, 100], 'color': self.color_scheme['positive']}],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': target_value}}))
        
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=60, b=20)
        )
        
        return fig
    
    def _create_empty_plot(self, message):
        """Create an empty plot with a message"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=300
        )
        return fig