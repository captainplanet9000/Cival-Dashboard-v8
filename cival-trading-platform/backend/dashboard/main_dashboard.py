"""
Phase 9: Main Dashboard Application
Streamlit-based dashboard with complete Master Wallet integration
"""

import streamlit as st
import asyncio
from datetime import datetime, timezone
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, List, Optional, Any

# Import dashboard tabs
from .master_wallet_tab import render_master_wallet_tab
from .goal_management_tab import render_goal_management_tab

# Page configuration
st.set_page_config(
    page_title="🏦 Autonomous Trading Platform",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f2937;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-active { background-color: #10b981; }
    .status-warning { background-color: #f59e0b; }
    .status-error { background-color: #ef4444; }
    
    .sidebar-section {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

async def main_dashboard():
    """Main dashboard application"""
    
    # Header
    st.markdown('<h1 class="main-header">🏦 Autonomous Trading Platform</h1>', unsafe_allow_html=True)
    st.markdown("**Real-time Master Wallet Management & Multi-Agent Trading System**")
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Control Center")
        
        # System status
        await render_system_status()
        
        # Quick actions
        st.header("⚡ Quick Actions")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh All", use_container_width=True):
                st.rerun()
        
        with col2:
            if st.button("⚠️ Emergency Stop", use_container_width=True):
                st.error("Emergency stop would halt all trading")
        
        # Wallet selector
        st.header("💰 Active Wallet")
        selected_wallet = st.selectbox(
            "Select Master Wallet:",
            ["Primary Trading ($25,000)", "Conservative Fund ($15,000)", "High Risk ($10,000)"],
            index=0
        )
        
        # System metrics mini-dashboard
        await render_sidebar_metrics()
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏦 Master Wallet",
        "🎯 Goal Management", 
        "🤖 Agents",
        "📊 Analytics",
        "⚖️ Risk Management",
        "🔧 System"
    ])
    
    with tab1:
        await render_master_wallet_tab()
    
    with tab2:
        await render_goal_management_tab()
    
    with tab3:
        await render_agents_tab()
    
    with tab4:
        await render_analytics_tab()
    
    with tab5:
        await render_risk_management_tab()
    
    with tab6:
        await render_system_tab()

async def render_system_status():
    """Render system status in sidebar"""
    
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.subheader("🔍 System Status")
    
    # System health indicators
    services = [
        {"name": "Master Wallet", "status": "active"},
        {"name": "Trading Engine", "status": "active"},
        {"name": "Goal Service", "status": "active"},
        {"name": "Market Data", "status": "warning"},
        {"name": "Risk Monitor", "status": "active"}
    ]
    
    for service in services:
        status_class = f"status-{service['status']}"
        st.markdown(
            f'<div><span class="status-indicator {status_class}"></span>{service["name"]}</div>',
            unsafe_allow_html=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)

async def render_sidebar_metrics():
    """Render key metrics in sidebar"""
    
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.subheader("📈 Key Metrics")
    
    # Mock metrics
    st.metric("Total Portfolio", "$50,000", "+$3,500")
    st.metric("Active Agents", "12", "+2")
    st.metric("Win Rate", "68.4%", "+2.1%")
    st.metric("Daily P&L", "+$425", "+$125")
    
    st.markdown('</div>', unsafe_allow_html=True)

async def render_agents_tab():
    """Render agents management tab"""
    
    st.header("🤖 Agent Management Center")
    
    # Agent overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Agents", "12", "+2")
    
    with col2:
        st.metric("Total Trades", "1,247", "+38")
    
    with col3:
        st.metric("Avg Performance", "74.2", "+3.5")
    
    with col4:
        st.metric("Total Allocated", "$32,500", "+$2,500")
    
    # Agent list
    st.subheader("🎯 Agent Portfolio")
    
    agents_data = [
        {"Name": "TrendFollower_001", "Strategy": "Trend Following", "Allocation": 5000, "Performance": 82.5, "Status": "Active", "Trades": 45},
        {"Name": "ArbitrageBot_003", "Strategy": "Arbitrage", "Allocation": 3500, "Performance": 76.2, "Status": "Active", "Trades": 128},
        {"Name": "MeanReversion_002", "Strategy": "Mean Reversion", "Allocation": 4200, "Performance": 68.9, "Status": "Active", "Trades": 67},
        {"Name": "BreakoutHunter_005", "Strategy": "Breakout", "Allocation": 3800, "Performance": 71.3, "Status": "Paused", "Trades": 34},
        {"Name": "ScalpingBot_007", "Strategy": "Scalping", "Allocation": 2500, "Performance": 79.1, "Status": "Active", "Trades": 312}
    ]
    
    df_agents = pd.DataFrame(agents_data)
    
    # Agent performance chart
    col1, col2 = st.columns(2)
    
    with col1:
        fig_performance = px.bar(
            df_agents, 
            x='Name', 
            y='Performance',
            color='Performance',
            title="Agent Performance Scores",
            color_continuous_scale='RdYlGn'
        )
        fig_performance.update_xaxis(tickangle=45)
        st.plotly_chart(fig_performance, use_container_width=True)
    
    with col2:
        fig_allocation = px.pie(
            df_agents,
            values='Allocation',
            names='Name',
            title="Capital Allocation Distribution"
        )
        st.plotly_chart(fig_allocation, use_container_width=True)
    
    # Agent details table
    st.subheader("📋 Agent Details")
    
    for idx, agent in df_agents.iterrows():
        with st.expander(f"🤖 {agent['Name']} - {agent['Strategy']}"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Allocation", f"${agent['Allocation']:,.0f}")
            
            with col2:
                st.metric("Performance", f"{agent['Performance']:.1f}")
            
            with col3:
                st.metric("Total Trades", agent['Trades'])
            
            with col4:
                status_color = "green" if agent['Status'] == 'Active' else "orange"
                st.markdown(f"Status: :{status_color}[{agent['Status']}]")
            
            # Agent actions
            action_col1, action_col2, action_col3 = st.columns(3)
            
            with action_col1:
                if st.button(f"⚙️ Configure", key=f"config_{idx}"):
                    st.info("Agent configuration panel would open here")
            
            with action_col2:
                if st.button(f"📊 Analytics", key=f"analytics_{idx}"):
                    st.info("Detailed agent analytics would be shown")
            
            with action_col3:
                action_text = "⏸️ Pause" if agent['Status'] == 'Active' else "▶️ Resume"
                if st.button(action_text, key=f"toggle_{idx}"):
                    new_status = "Paused" if agent['Status'] == 'Active' else "Active"
                    st.success(f"Agent {agent['Name']} {new_status.lower()}")

async def render_analytics_tab():
    """Render analytics and performance tab"""
    
    st.header("📊 Performance Analytics")
    
    # Portfolio performance overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Portfolio Value", "$50,000", "+7.5%")
    
    with col2:
        st.metric("Monthly Return", "+$3,500", "+12.8%")
    
    with col3:
        st.metric("Sharpe Ratio", "1.85", "+0.12")
    
    with col4:
        st.metric("Max Drawdown", "-5.2%", "+1.1%")
    
    # Performance charts
    st.subheader("📈 Portfolio Performance Timeline")
    
    # Mock performance data
    dates = pd.date_range(start='2025-01-01', end='2025-06-14', freq='D')
    performance_data = pd.DataFrame({
        'Date': dates,
        'Portfolio Value': [46500 + i*20 + (i%7)*100 for i in range(len(dates))],
        'Daily PnL': [(i%7)*50 - 100 for i in range(len(dates))],
        'Cumulative Return': [i*0.1 + (i%7)*0.5 for i in range(len(dates))]
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_value = px.line(
            performance_data, 
            x='Date', 
            y='Portfolio Value',
            title="Portfolio Value Over Time"
        )
        st.plotly_chart(fig_value, use_container_width=True)
    
    with col2:
        fig_returns = px.line(
            performance_data,
            x='Date', 
            y='Cumulative Return',
            title="Cumulative Returns (%)"
        )
        st.plotly_chart(fig_returns, use_container_width=True)
    
    # Performance attribution
    st.subheader("🎯 Performance Attribution")
    
    attribution_data = {
        'Strategy': ['Trend Following', 'Arbitrage', 'Mean Reversion', 'Breakout', 'Scalping'],
        'Contribution': [1250, 850, 420, 680, 300],
        'Allocation': [35, 25, 20, 15, 5]
    }
    
    df_attribution = pd.DataFrame(attribution_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_contrib = px.bar(
            df_attribution,
            x='Strategy',
            y='Contribution',
            title="P&L Contribution by Strategy",
            color='Contribution',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig_contrib, use_container_width=True)
    
    with col2:
        fig_alloc = px.pie(
            df_attribution,
            values='Allocation',
            names='Strategy',
            title="Allocation by Strategy"
        )
        st.plotly_chart(fig_alloc, use_container_width=True)

async def render_risk_management_tab():
    """Render risk management tab"""
    
    st.header("⚖️ Risk Management Center")
    
    # Risk metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Portfolio VaR", "$1,250", "-$150")
    
    with col2:
        st.metric("Beta", "0.85", "-0.05")
    
    with col3:
        st.metric("Correlation", "0.62", "+0.03")
    
    with col4:
        st.metric("Volatility", "18.5%", "-2.1%")
    
    # Risk charts
    st.subheader("📊 Risk Analysis")
    
    # Risk heatmap
    risk_data = {
        'Agent': ['TrendFollower_001', 'ArbitrageBot_003', 'MeanReversion_002', 'BreakoutHunter_005', 'ScalpingBot_007'],
        'Market Risk': [0.75, 0.45, 0.60, 0.85, 0.55],
        'Liquidity Risk': [0.30, 0.20, 0.40, 0.50, 0.25],
        'Counterparty Risk': [0.15, 0.10, 0.20, 0.25, 0.15]
    }
    
    df_risk = pd.DataFrame(risk_data)
    df_risk_melted = df_risk.melt(id_vars=['Agent'], var_name='Risk Type', value_name='Risk Level')
    
    fig_risk = px.imshow(
        df_risk.set_index('Agent')[['Market Risk', 'Liquidity Risk', 'Counterparty Risk']].T,
        title="Risk Heatmap by Agent",
        color_continuous_scale='Reds',
        aspect='auto'
    )
    st.plotly_chart(fig_risk, use_container_width=True)
    
    # Risk limits and controls
    st.subheader("🛡️ Risk Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Position Limits**")
        st.slider("Max Position Size", 0, 10000, 5000, 500)
        st.slider("Max Portfolio Exposure", 0, 100, 80, 5)
        st.slider("Max Daily Loss", 0, 5000, 1000, 100)
    
    with col2:
        st.write("**Risk Monitoring**")
        st.checkbox("Real-time VaR monitoring", value=True)
        st.checkbox("Correlation alerts", value=True)
        st.checkbox("Drawdown protection", value=True)
        st.checkbox("Emergency stop triggers", value=False)

async def render_system_tab():
    """Render system monitoring tab"""
    
    st.header("🔧 System Monitoring")
    
    # System health
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Uptime", "99.8%", "+0.1%")
    
    with col2:
        st.metric("API Latency", "45ms", "-5ms")
    
    with col3:
        st.metric("Memory Usage", "68%", "+2%")
    
    with col4:
        st.metric("CPU Usage", "42%", "-3%")
    
    # Service status
    st.subheader("🔍 Service Health")
    
    services = [
        {"Service": "Master Wallet Service", "Status": "Healthy", "Response Time": "25ms", "Uptime": "99.9%"},
        {"Service": "Trading Engine", "Status": "Healthy", "Response Time": "35ms", "Uptime": "99.8%"},
        {"Service": "Goal Management", "Status": "Healthy", "Response Time": "20ms", "Uptime": "100%"},
        {"Service": "Market Data Feed", "Status": "Warning", "Response Time": "120ms", "Uptime": "98.5%"},
        {"Service": "Risk Monitor", "Status": "Healthy", "Response Time": "15ms", "Uptime": "99.9%"},
        {"Service": "Fund Distribution", "Status": "Healthy", "Response Time": "30ms", "Uptime": "99.7%"}
    ]
    
    df_services = pd.DataFrame(services)
    
    for idx, service in df_services.iterrows():
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.write(f"**{service['Service']}**")
        
        with col2:
            status_color = "green" if service['Status'] == 'Healthy' else "orange"
            st.markdown(f":{status_color}[{service['Status']}]")
        
        with col3:
            st.write(service['Response Time'])
        
        with col4:
            st.write(service['Uptime'])
    
    # System logs
    st.subheader("📋 Recent System Events")
    
    logs = [
        {"Time": "2025-06-14 14:30:25", "Level": "INFO", "Service": "Master Wallet", "Message": "Fund allocation completed: $2,500 to Agent_001"},
        {"Time": "2025-06-14 14:28:15", "Level": "INFO", "Service": "Goal Management", "Message": "Goal progress updated: Goal_007 now 68% complete"},
        {"Time": "2025-06-14 14:25:10", "Level": "WARN", "Service": "Market Data", "Message": "High latency detected on Binance feed"},
        {"Time": "2025-06-14 14:22:30", "Level": "INFO", "Service": "Trading Engine", "Message": "Position opened: BTC/USD Long $1,000"},
        {"Time": "2025-06-14 14:20:45", "Level": "INFO", "Service": "Risk Monitor", "Message": "Daily VaR recalculated: $1,250"}
    ]
    
    for log in logs:
        level_color = "red" if log['Level'] == 'ERROR' else "orange" if log['Level'] == 'WARN' else "blue"
        st.markdown(f"`{log['Time']}` :{level_color}[{log['Level']}] **{log['Service']}:** {log['Message']}")

# Run the dashboard
if __name__ == "__main__":
    asyncio.run(main_dashboard())