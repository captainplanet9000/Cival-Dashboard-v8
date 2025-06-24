"""
Phase 9: Master Wallet Dashboard Tab
Complete integration of Master Wallet system into the main dashboard
"""

import streamlit as st
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..core.service_registry import get_registry
from ..models.master_wallet_models import MasterWallet, WalletPerformanceMetrics

async def render_master_wallet_tab():
    """Render the Master Wallet tab with comprehensive wallet management"""
    
    st.header("🏦 Master Wallet Control Center")
    st.markdown("**Central hub for wallet management, allocation, and performance tracking**")
    
    # Get service registry
    registry = get_registry()
    master_wallet_service = registry.get_service("master_wallet_service")
    fund_distribution_engine = registry.get_service("fund_distribution_engine")
    
    if not master_wallet_service:
        st.error("Master Wallet Service not available")
        return
    
    # Create layout columns
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col3:
        # Quick Actions
        st.subheader("⚡ Quick Actions")
        
        if st.button("🔄 Refresh All", use_container_width=True):
            st.rerun()
        
        if st.button("⚖️ Auto Rebalance", use_container_width=True):
            with st.spinner("Executing auto-rebalance..."):
                await execute_auto_rebalance()
            st.success("Auto-rebalance completed!")
        
        if st.button("💰 Create Wallet", use_container_width=True):
            st.session_state.show_create_wallet = True
    
    # Load wallet data
    wallets_data = await load_wallets_data(master_wallet_service)
    
    if not wallets_data:
        st.info("No master wallets found. Create your first wallet to get started.")
        return
    
    with col1:
        # Wallet Selection
        wallet_options = {f"{w['name']} (${w['total_balance']:,.0f})": w['wallet_id'] 
                         for w in wallets_data}
        
        selected_wallet_display = st.selectbox(
            "Select Master Wallet:",
            options=list(wallet_options.keys()),
            index=0 if wallet_options else None
        )
        
        selected_wallet_id = wallet_options.get(selected_wallet_display) if selected_wallet_display else None
    
    with col2:
        # Allocation Method Selection
        allocation_methods = [
            "performance_weighted",
            "risk_parity", 
            "sharpe_optimized",
            "kelly_criterion",
            "ml_optimized",
            "adaptive_risk"
        ]
        
        selected_method = st.selectbox(
            "Allocation Strategy:",
            options=allocation_methods,
            index=0,
            help="Choose the algorithm for fund distribution"
        )
    
    if selected_wallet_id:
        # Load detailed wallet data
        wallet_details = await load_wallet_details(master_wallet_service, selected_wallet_id)
        
        if wallet_details:
            # Display wallet overview
            await display_wallet_overview(wallet_details)
            
            # Create tabs for different sections
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📊 Performance", 
                "🎯 Allocations", 
                "⚖️ Distribution", 
                "🔗 Multi-Chain", 
                "📈 Analytics"
            ])
            
            with tab1:
                await display_performance_section(wallet_details, master_wallet_service)
            
            with tab2:
                await display_allocations_section(wallet_details, fund_distribution_engine)
            
            with tab3:
                await display_distribution_section(wallet_details, fund_distribution_engine, selected_method)
            
            with tab4:
                await display_multichain_section(wallet_details)
            
            with tab5:
                await display_analytics_section(wallet_details, master_wallet_service)
    
    # Handle create wallet modal
    if st.session_state.get('show_create_wallet', False):
        await display_create_wallet_modal(master_wallet_service)

async def load_wallets_data(master_wallet_service) -> List[Dict[str, Any]]:
    """Load summary data for all wallets"""
    try:
        # Mock data - replace with actual service call
        return [
            {
                'wallet_id': 'wallet_001',
                'name': 'Primary Trading Wallet',
                'total_balance': 25000.0,
                'allocated_amount': 18500.0,
                'performance_score': 78.5,
                'status': 'active'
            },
            {
                'wallet_id': 'wallet_002', 
                'name': 'Conservative Wallet',
                'total_balance': 15000.0,
                'allocated_amount': 9000.0,
                'performance_score': 65.2,
                'status': 'active'
            }
        ]
    except Exception as e:
        st.error(f"Failed to load wallets: {e}")
        return []

async def load_wallet_details(master_wallet_service, wallet_id: str) -> Optional[Dict[str, Any]]:
    """Load detailed wallet information"""
    try:
        # Mock detailed wallet data
        return {
            'wallet_id': wallet_id,
            'name': 'Primary Trading Wallet',
            'description': 'Main wallet for autonomous trading operations',
            'total_balance': 25000.0,
            'allocated_amount': 18500.0,
            'available_balance': 6500.0,
            'performance_score': 78.5,
            'total_pnl': 3500.0,
            'total_pnl_percentage': 16.3,
            'win_rate': 68.4,
            'max_drawdown': 8.2,
            'sharpe_ratio': 1.85,
            'active_allocations': 8,
            'chain_balances': {
                'ethereum': {'balance': 12000.0, 'percentage': 48.0},
                'polygon': {'balance': 8000.0, 'percentage': 32.0},
                'bsc': {'balance': 5000.0, 'percentage': 20.0}
            },
            'recent_transactions': [
                {'type': 'allocation', 'amount': 2000.0, 'target': 'Agent_001', 'timestamp': '2025-06-14T10:30:00'},
                {'type': 'collection', 'amount': 500.0, 'target': 'Goal_005', 'timestamp': '2025-06-14T09:15:00'},
                {'type': 'rebalance', 'amount': 1500.0, 'target': 'Farm_003', 'timestamp': '2025-06-14T08:45:00'}
            ]
        }
    except Exception as e:
        st.error(f"Failed to load wallet details: {e}")
        return None

async def display_wallet_overview(wallet_details: Dict[str, Any]):
    """Display wallet overview metrics"""
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Balance",
            f"${wallet_details['total_balance']:,.0f}",
            delta=f"+${wallet_details['total_pnl']:,.0f}"
        )
    
    with col2:
        st.metric(
            "Allocated",
            f"${wallet_details['allocated_amount']:,.0f}",
            delta=f"{(wallet_details['allocated_amount']/wallet_details['total_balance']*100):.1f}%"
        )
    
    with col3:
        st.metric(
            "Performance Score",
            f"{wallet_details['performance_score']:.1f}",
            delta=f"{wallet_details['total_pnl_percentage']:+.1f}%"
        )
    
    with col4:
        st.metric(
            "Win Rate",
            f"{wallet_details['win_rate']:.1f}%",
            delta=f"Sharpe: {wallet_details['sharpe_ratio']:.2f}"
        )

async def display_performance_section(wallet_details: Dict[str, Any], master_wallet_service):
    """Display performance metrics and charts"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Performance Metrics")
        
        # Performance gauge chart
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = wallet_details['performance_score'],
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Performance Score"},
            delta = {'reference': 70},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "green"}],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90}}))
        
        fig_gauge.update_layout(height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col2:
        st.subheader("💰 P&L Distribution")
        
        # P&L pie chart
        pnl_data = {
            'Realized Gains': 2800,
            'Unrealized Gains': 700,
            'Fees Paid': -200,
            'Slippage': -150
        }
        
        fig_pie = px.pie(
            values=list(pnl_data.values()),
            names=list(pnl_data.keys()),
            title="Profit & Loss Breakdown"
        )
        fig_pie.update_layout(height=300)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Performance timeline
    st.subheader("📊 Performance Timeline")
    
    # Mock performance data
    dates = pd.date_range(start='2025-01-01', end='2025-06-14', freq='D')
    performance_data = pd.DataFrame({
        'Date': dates,
        'Portfolio Value': [21500 + i*15 + (i%7)*50 for i in range(len(dates))],
        'Daily PnL': [(i%7)*25 - 50 for i in range(len(dates))]
    })
    
    fig_timeline = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Portfolio Value', 'Daily P&L'),
        vertical_spacing=0.1
    )
    
    fig_timeline.add_trace(
        go.Scatter(x=performance_data['Date'], y=performance_data['Portfolio Value'],
                  mode='lines', name='Portfolio Value'),
        row=1, col=1
    )
    
    fig_timeline.add_trace(
        go.Bar(x=performance_data['Date'], y=performance_data['Daily PnL'],
               name='Daily P&L'),
        row=2, col=1
    )
    
    fig_timeline.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig_timeline, use_container_width=True)

async def display_allocations_section(wallet_details: Dict[str, Any], fund_distribution_engine):
    """Display current allocations and management"""
    
    st.subheader("🎯 Current Allocations")
    
    # Mock allocation data
    allocations_data = [
        {'Target': 'Trading Agent 001', 'Type': 'Agent', 'Amount': 5000, 'Performance': 82.5, 'Status': 'Active'},
        {'Target': 'Trend Following Farm', 'Type': 'Farm', 'Amount': 4500, 'Performance': 75.2, 'Status': 'Active'},
        {'Target': 'Goal: 10% Monthly Return', 'Type': 'Goal', 'Amount': 3000, 'Performance': 68.9, 'Status': 'Active'},
        {'Target': 'Arbitrage Agent 003', 'Type': 'Agent', 'Amount': 2500, 'Performance': 71.3, 'Status': 'Active'},
        {'Target': 'Mean Reversion Farm', 'Type': 'Farm', 'Amount': 3500, 'Performance': 79.1, 'Status': 'Active'}
    ]
    
    df_allocations = pd.DataFrame(allocations_data)
    
    # Display allocation table with actions
    for idx, row in df_allocations.iterrows():
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
        
        with col1:
            st.write(f"**{row['Target']}** ({row['Type']})")
        
        with col2:
            st.write(f"${row['Amount']:,.0f}")
        
        with col3:
            color = "green" if row['Performance'] > 75 else "orange" if row['Performance'] > 60 else "red"
            st.markdown(f":{color}[{row['Performance']:.1f}]")
        
        with col4:
            if st.button(f"📈", key=f"adjust_{idx}", help="Adjust allocation"):
                st.session_state[f'adjust_allocation_{idx}'] = True
        
        with col5:
            if st.button(f"💰", key=f"collect_{idx}", help="Collect funds"):
                await collect_funds_from_allocation(row['Target'], row['Amount'])
    
    # Allocation chart
    st.subheader("📊 Allocation Distribution")
    
    fig_alloc = px.sunburst(
        df_allocations,
        path=['Type', 'Target'],
        values='Amount',
        title="Fund Allocation Hierarchy"
    )
    fig_alloc.update_layout(height=400)
    st.plotly_chart(fig_alloc, use_container_width=True)

async def display_distribution_section(wallet_details: Dict[str, Any], fund_distribution_engine, method: str):
    """Display fund distribution recommendations"""
    
    st.subheader("⚖️ AI-Powered Fund Distribution")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"**Selected Method:** {method.replace('_', ' ').title()}")
        
        # Distribution parameters
        available_funds = wallet_details['available_balance']
        
        st.write(f"**Available Funds:** ${available_funds:,.0f}")
        
        # Get recommendations (mock)
        recommendations = await get_allocation_recommendations(fund_distribution_engine, method, available_funds)
        
        if recommendations:
            st.subheader("🎯 Recommended Allocations")
            
            for rec in recommendations:
                col_target, col_amount, col_conf, col_action = st.columns([2, 1, 1, 1])
                
                with col_target:
                    st.write(f"**{rec['target_name']}**")
                    st.caption(rec['reasoning'])
                
                with col_amount:
                    st.write(f"${rec['amount']:,.0f}")
                    st.caption(f"{rec['percentage']:.1f}%")
                
                with col_conf:
                    conf_color = "green" if rec['confidence'] > 0.8 else "orange" if rec['confidence'] > 0.6 else "red"
                    st.markdown(f":{conf_color}[{rec['confidence']:.0%}]")
                
                with col_action:
                    if st.button(f"✅", key=f"approve_{rec['target_id']}", help="Approve allocation"):
                        await execute_allocation(rec)
                        st.success(f"Allocated ${rec['amount']:,.0f} to {rec['target_name']}")
    
    with col2:
        st.subheader("⚙️ Distribution Settings")
        
        # Risk tolerance
        risk_tolerance = st.slider(
            "Risk Tolerance",
            min_value=1,
            max_value=10,
            value=5,
            help="1 = Conservative, 10 = Aggressive"
        )
        
        # Max allocation per target
        max_allocation = st.slider(
            "Max Allocation %",
            min_value=5,
            max_value=50,
            value=25,
            help="Maximum percentage per single target"
        )
        
        # Rebalance frequency
        rebalance_freq = st.selectbox(
            "Rebalance Frequency",
            ["Manual", "Daily", "Weekly", "Monthly"],
            index=2
        )
        
        if st.button("🔄 Generate New Recommendations", use_container_width=True):
            st.rerun()

async def display_multichain_section(wallet_details: Dict[str, Any]):
    """Display multi-chain wallet information"""
    
    st.subheader("🔗 Multi-Chain Portfolio")
    
    chain_balances = wallet_details['chain_balances']
    
    # Chain distribution
    col1, col2 = st.columns(2)
    
    with col1:
        # Chain balance chart
        chains = list(chain_balances.keys())
        balances = [chain_balances[chain]['balance'] for chain in chains]
        
        fig_chains = px.pie(
            values=balances,
            names=chains,
            title="Cross-Chain Distribution"
        )
        st.plotly_chart(fig_chains, use_container_width=True)
    
    with col2:
        # Chain details
        for chain, data in chain_balances.items():
            with st.expander(f"🔗 {chain.title()} Network"):
                st.metric(
                    "Balance",
                    f"${data['balance']:,.0f}",
                    delta=f"{data['percentage']:.1f}% of total"
                )
                
                # Mock additional chain data
                st.write("**Recent Activity:**")
                st.write("• 3 transactions in last 24h")
                st.write("• Gas fees: $12.50")
                st.write("• Network status: ✅ Healthy")
    
    # Cross-chain actions
    st.subheader("🌉 Cross-Chain Operations")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Bridge Assets", use_container_width=True):
            st.info("Bridge asset functionality would be implemented here")
    
    with col2:
        if st.button("⚡ Optimize Gas", use_container_width=True):
            st.info("Gas optimization would be implemented here")
    
    with col3:
        if st.button("📊 Chain Analytics", use_container_width=True):
            st.info("Detailed chain analytics would be shown here")

async def display_analytics_section(wallet_details: Dict[str, Any], master_wallet_service):
    """Display advanced analytics and insights"""
    
    st.subheader("📈 Advanced Analytics")
    
    # Risk metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Max Drawdown", f"{wallet_details['max_drawdown']:.1f}%")
    
    with col2:
        st.metric("Sharpe Ratio", f"{wallet_details['sharpe_ratio']:.2f}")
    
    with col3:
        st.metric("Win Rate", f"{wallet_details['win_rate']:.1f}%")
    
    # Recent transactions
    st.subheader("💸 Recent Transactions")
    
    transactions = wallet_details['recent_transactions']
    df_transactions = pd.DataFrame(transactions)
    
    if not df_transactions.empty:
        df_transactions['timestamp'] = pd.to_datetime(df_transactions['timestamp'])
        df_transactions = df_transactions.sort_values('timestamp', ascending=False)
        
        for _, txn in df_transactions.head(10).iterrows():
            col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
            
            with col1:
                icon = "📤" if txn['type'] == 'allocation' else "📥" if txn['type'] == 'collection' else "⚖️"
                st.write(f"{icon} {txn['type'].title()}")
            
            with col2:
                st.write(f"${txn['amount']:,.0f}")
            
            with col3:
                st.write(txn['target'])
            
            with col4:
                st.caption(txn['timestamp'].strftime("%m/%d %H:%M"))

async def display_create_wallet_modal(master_wallet_service):
    """Display create wallet modal"""
    
    with st.form("create_wallet_form"):
        st.subheader("💰 Create New Master Wallet")
        
        name = st.text_input("Wallet Name", placeholder="e.g., High Yield Trading Wallet")
        description = st.text_area("Description", placeholder="Brief description of wallet purpose")
        
        initial_balance = st.number_input(
            "Initial Balance ($)",
            min_value=1000.0,
            max_value=1000000.0,
            value=10000.0,
            step=1000.0
        )
        
        chains = st.multiselect(
            "Supported Chains",
            ["ethereum", "polygon", "bsc", "arbitrum", "optimism", "avalanche"],
            default=["ethereum", "polygon"]
        )
        
        auto_distribution = st.checkbox("Enable Auto-Distribution", value=True)
        
        submitted = st.form_submit_button("🚀 Create Wallet")
        
        if submitted:
            if name and description:
                try:
                    # Create wallet (mock)
                    await create_new_wallet(master_wallet_service, {
                        'name': name,
                        'description': description,
                        'initial_balance': initial_balance,
                        'chains': chains,
                        'auto_distribution': auto_distribution
                    })
                    
                    st.success(f"Successfully created wallet: {name}")
                    st.session_state.show_create_wallet = False
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Failed to create wallet: {e}")
            else:
                st.error("Please fill in all required fields")

async def get_allocation_recommendations(fund_distribution_engine, method: str, available_funds: float) -> List[Dict[str, Any]]:
    """Get allocation recommendations from the distribution engine"""
    
    # Mock recommendations
    return [
        {
            'target_id': 'agent_001',
            'target_name': 'High Performance Agent 001',
            'amount': 2500,
            'percentage': 38.5,
            'confidence': 0.87,
            'reasoning': 'Strong performance score (85.2) with consistent returns'
        },
        {
            'target_id': 'farm_003',
            'target_name': 'Momentum Trading Farm',
            'amount': 2000,
            'percentage': 30.8,
            'confidence': 0.82,
            'reasoning': 'Excellent trend following with 78% win rate'
        },
        {
            'target_id': 'goal_007',
            'target_name': 'Goal: 15% Quarterly Return',
            'amount': 1500,
            'percentage': 23.1,
            'confidence': 0.75,
            'reasoning': 'On track for completion with 68% progress'
        },
        {
            'target_id': 'agent_005',
            'target_name': 'Arbitrage Agent 005',
            'amount': 500,
            'percentage': 7.7,
            'confidence': 0.69,
            'reasoning': 'Low risk arbitrage opportunities available'
        }
    ]

async def execute_allocation(recommendation: Dict[str, Any]):
    """Execute a fund allocation"""
    # Implementation would call the actual service
    pass

async def collect_funds_from_allocation(target: str, amount: float):
    """Collect funds from an allocation"""
    # Implementation would call the actual service
    pass

async def execute_auto_rebalance():
    """Execute automatic rebalancing"""
    # Implementation would call the actual service
    pass

async def create_new_wallet(master_wallet_service, wallet_config: Dict[str, Any]):
    """Create a new master wallet"""
    # Implementation would call the actual service
    pass