import streamlit as st
import json
from agents.timeline_agent import TimelineAgent
from agents.comparative_agent import ComparativeAgent
from agents.playbook_agent import PlaybookAgent
from rag.vector_store import DealVectorStore
from utils.visualizer import DealVisualizer
from rag.data_processor import DataProcessor

def main():
    st.set_page_config(page_title="Deal Forensics AI", layout="wide")
    st.title("🔍 Deal Forensics AI - Post-Mortem Analysis")
    
    # Initialize components
    data_processor = DataProcessor()
    vector_store = DealVectorStore()
    timeline_agent = TimelineAgent()
    comparative_agent = ComparativeAgent()
    playbook_agent = PlaybookAgent()
    visualizer = DealVisualizer()
    
    # Load sample data
    sample_data = data_processor.sample_data
    
    # Store data in vector DB
    vector_store.store_deals(sample_data)
    
    st.sidebar.header("Select Lost Deal for Analysis")
    lost_deals = data_processor.get_all_lost_deals()
    selected_deal_id = st.sidebar.selectbox(
        "Choose a deal:",
        [deal["deal_id"] for deal in lost_deals]
    )
    
    if st.sidebar.button("Run Forensic Analysis"):
        # Get selected deal
        lost_deal = data_processor.get_lost_deal_by_id(selected_deal_id)
        
        if not lost_deal:
            st.error("Selected deal not found!")
            return
        
        # Show deal overview
        st.header(f"📋 Deal Overview: {lost_deal['company']}")
        col_overview = st.columns(3)
        with col_overview[0]:
            st.metric("Deal Value", f"${lost_deal['value']:,}")
        with col_overview[1]:
            st.metric("Timeline Duration", f"{len(lost_deal['timeline'])} days")
        with col_overview[2]:
            st.metric("Competitors", ", ".join(lost_deal.get('competitors', ['None'])))
        
        # Run analyses
        with st.spinner("🔍 Analyzing timeline..."):
            timeline_analysis = timeline_agent.analyze_timeline(lost_deal)
        
        with st.spinner("📊 Comparing with won deals..."):
            # Search for similar won deals
            similar_won = vector_store.search_similar_deals(
                lost_deal["company"], 
                deal_type="won"
            )
            comparative_analysis = comparative_agent.compare_with_won_deals(
                lost_deal, 
                similar_won
            )
        
        with st.spinner("🎯 Generating playbook..."):
            # FIXED: Pass all three required arguments
            playbook = playbook_agent.generate_playbook(
                timeline_analysis, 
                comparative_analysis, 
                lost_deal
            )
        
        # Display results in columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("📊 Timeline Analysis")
            
            # Display timeline analysis summary
            if isinstance(timeline_analysis, dict):
                timeline_summary = timeline_agent.generate_timeline_summary(timeline_analysis)
                st.write(timeline_summary)
                
                # Show critical moments in expander
                with st.expander("View Detailed Timeline Analysis"):
                    st.json(timeline_analysis)
            else:
                st.write(timeline_analysis)
            
            # Visual timeline
            st.subheader("📈 Timeline Visualization")
            fig_timeline = visualizer.create_timeline_visualization(lost_deal, timeline_analysis)
            st.plotly_chart(fig_timeline, use_container_width=True)
        
        with col2:
            st.header("🔍 Comparative Analysis")
            
            # Display comparative analysis summary
            if isinstance(comparative_analysis, dict):
                comparative_summary = comparative_agent.generate_comparative_summary(comparative_analysis)
                st.write(comparative_summary)
                
                # Show comparative chart
                st.subheader("📊 Response Time Comparison")
                fig_comparative = visualizer.create_comparative_analysis_chart(comparative_analysis)
                if fig_comparative:
                    st.plotly_chart(fig_comparative, use_container_width=True)
                
                with st.expander("View Detailed Comparative Analysis"):
                    st.json(comparative_analysis)
            else:
                st.write(comparative_analysis)
        
        # Playbook section (full width)
        st.header("🎯 Generated Playbook")
        
        # Display playbook content
        if isinstance(playbook, dict):
            # Improvement opportunities chart
            st.subheader("🚀 Improvement Opportunities")
            fig_improvements = visualizer.create_improvement_opportunities_chart(playbook)
            if fig_improvements:
                st.plotly_chart(fig_improvements, use_container_width=True)
            
            # Immediate actions
            if playbook.get('immediate_actions'):
                st.subheader("📋 Immediate Actions")
                for i, action in enumerate(playbook['immediate_actions'][:5], 1):
                    with st.container():
                        col_a, col_b, col_c = st.columns([3, 1, 1])
                        with col_a:
                            st.write(f"**{i}. {action.get('action', 'Unknown action')}**")
                        with col_b:
                            st.write(f"👤 {action.get('owner', 'Unknown')}")
                        with col_c:
                            priority = action.get('priority', 'medium')
                            color = "🔴" if priority == 'high' else "🟡" if priority == 'medium' else "🟢"
                            st.write(f"{color} {priority}")
                        st.write(f"⏰ Timeline: {action.get('timeline', 'Not specified')}")
                        st.divider()
            
            # Trigger responses
            if playbook.get('trigger_responses'):
                st.subheader("🎯 Trigger-Based Responses")
                for trigger in playbook['trigger_responses'][:3]:
                    with st.expander(f"Trigger: {trigger.get('trigger', 'Unknown')}"):
                        st.write(f"**Immediate Action:** {trigger.get('immediate_action', 'Not specified')}")
                        st.write(f"**Timeframe:** {trigger.get('timeframe', 'Not specified')}")
                        if trigger.get('follow_up'):
                            st.write(f"**Follow-up:** {trigger['follow_up']}")
            
            # Success metrics
            if playbook.get('success_metrics'):
                st.subheader("📈 Success Metrics")
                col_metrics = st.columns(2)
                for i, metric in enumerate(playbook['success_metrics'][:4]):
                    with col_metrics[i % 2]:
                        st.metric(
                            label=metric.get('metric', 'Metric'),
                            value=metric.get('target', 'N/A')
                        )
            
            # Show raw playbook in expander
            with st.expander("View Complete Playbook JSON"):
                st.json(playbook)
                
        else:
            st.write(playbook)
        
        # Add some analytics
        st.header("📈 Analysis Summary")
        col_summary = st.columns(3)
        
        with col_summary[0]:
            if isinstance(timeline_analysis, dict) and timeline_analysis.get('timeline_score'):
                score = timeline_analysis['timeline_score']
                st.metric("Timeline Score", f"{score}/10")
        
        with col_summary[1]:
            if isinstance(playbook, dict) and playbook.get('confidence_score'):
                confidence = playbook['confidence_score']
                st.metric("Confidence Score", f"{confidence}%")
        
        with col_summary[2]:
            if isinstance(playbook, dict) and playbook.get('expected_impact'):
                impact = playbook['expected_impact']
                st.metric("Expected Impact", impact)

if __name__ == "__main__":
    main()