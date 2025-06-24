#!/usr/bin/env python3
"""
Basic HTTP server for AI services using only standard library
No external dependencies required
"""
import os
import json
import http.server
import socketserver
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import threading
import time
import random

# Load environment from .env file manually
def load_env():
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
                    os.environ[key] = value
    except FileNotFoundError:
        print("No .env file found, using environment variables only")
    return env_vars

# Load environment
env_vars = load_env()

# Configuration
API_PORT = int(os.getenv("PORT", 9000))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

class TradingAgentManager:
    """Manages trading agents and their state"""
    
    def __init__(self):
        self.agents = {}
        self.trades = []
        self.market_data = {}
        self.initialize_agents()
    
    def initialize_agents(self):
        """Initialize sample trading agents"""
        self.agents = {
            "trading_agent_001": {
                "id": "trading_agent_001",
                "name": "Darvas Box Strategy Agent",
                "strategy": "darvas_box",
                "status": "active",
                "cash": 100000.0,
                "total_value": 100000.0,
                "positions": {},
                "daily_pnl": 0.0,
                "total_trades": 0,
                "win_rate": 0.0,
                "created_at": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat()
            },
            "trading_agent_002": {
                "id": "trading_agent_002", 
                "name": "Elliott Wave Strategy Agent",
                "strategy": "elliott_wave",
                "status": "active",
                "cash": 100000.0,
                "total_value": 100000.0,
                "positions": {},
                "daily_pnl": 0.0,
                "total_trades": 0,
                "win_rate": 0.0,
                "created_at": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat()
            },
            "trading_agent_003": {
                "id": "trading_agent_003",
                "name": "SMA Crossover Strategy Agent", 
                "strategy": "sma_crossover",
                "status": "active",
                "cash": 100000.0,
                "total_value": 100000.0,
                "positions": {},
                "daily_pnl": 0.0,
                "total_trades": 0,
                "win_rate": 0.0,
                "created_at": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat()
            },
            "trading_agent_004": {
                "id": "trading_agent_004",
                "name": "Williams Alligator Strategy Agent",
                "strategy": "williams_alligator", 
                "status": "active",
                "cash": 100000.0,
                "total_value": 100000.0,
                "positions": {},
                "daily_pnl": 0.0,
                "total_trades": 0,
                "win_rate": 0.0,
                "created_at": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat()
            }
        }
    
    def get_market_data(self, symbol):
        """Simulate market data for testing"""
        base_price = {"AAPL": 150, "GOOGL": 2800, "MSFT": 300, "TSLA": 200}.get(symbol, 100)
        price = base_price + random.uniform(-10, 10)
        
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "volume": random.randint(100000, 5000000),
            "change": round(random.uniform(-5, 5), 2),
            "change_percent": round(random.uniform(-3, 3), 2),
            "timestamp": datetime.now().isoformat(),
            "source": "simulated"
        }
    
    def create_trade(self, agent_id, symbol, side, quantity):
        """Create a simulated paper trade"""
        if agent_id not in self.agents:
            return {"error": "Agent not found"}
        
        market_data = self.get_market_data(symbol)
        trade_id = len(self.trades) + 1
        
        trade = {
            "id": trade_id,
            "agent_id": agent_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": market_data["price"],
            "total_value": quantity * market_data["price"],
            "status": "filled",
            "paper_trade": True,
            "reasoning": f"Automated {side} order for {symbol} based on {self.agents[agent_id]['strategy']} strategy",
            "confidence_score": round(random.uniform(0.6, 0.9), 2),
            "created_at": datetime.now().isoformat(),
            "executed_at": datetime.now().isoformat()
        }
        
        self.trades.append(trade)
        
        # Update agent stats
        agent = self.agents[agent_id]
        agent["total_trades"] += 1
        agent["last_update"] = datetime.now().isoformat()
        
        return trade

class TradingAPIHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for trading API"""
    
    def __init__(self, *args, **kwargs):
        self.agent_manager = TradingAgentManager()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        url = urlparse(self.path)
        path = url.path
        query = parse_qs(url.query)
        
        # Set CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
        
        response = {}
        
        if path == '/':
            response = {
                "message": "Cival Dashboard AI Services",
                "status": "running",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "agents_active": len([a for a in self.agent_manager.agents.values() if a["status"] == "active"])
            }
        
        elif path == '/health':
            response = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "anthropic_api": "configured" if ANTHROPIC_API_KEY else "missing",
                    "openai_api": "configured" if OPENAI_API_KEY else "missing",
                    "alpha_vantage": "configured" if ALPHA_VANTAGE_API_KEY else "missing"
                },
                "agents": len(self.agent_manager.agents),
                "trades": len(self.agent_manager.trades)
            }
        
        elif path == '/agents':
            response = {
                "agents": list(self.agent_manager.agents.values()),
                "count": len(self.agent_manager.agents)
            }
        
        elif path.startswith('/agents/'):
            agent_id = path.split('/')[-1]
            if agent_id in self.agent_manager.agents:
                response = self.agent_manager.agents[agent_id]
            else:
                response = {"error": "Agent not found"}
        
        elif path.startswith('/market-data/'):
            symbol = path.split('/')[-1].upper()
            response = self.agent_manager.get_market_data(symbol)
        
        elif path == '/trades':
            response = {
                "trades": self.agent_manager.trades,
                "count": len(self.agent_manager.trades)
            }
        
        else:
            response = {"error": "Endpoint not found"}
        
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except:
            data = {}
        
        url = urlparse(self.path)
        path = url.path
        
        # Set CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
        
        response = {}
        
        if path == '/trades/simulate':
            agent_id = data.get('agent_id', 'trading_agent_001')
            symbol = data.get('symbol', 'AAPL')
            side = data.get('side', 'buy')
            quantity = data.get('quantity', 10)
            
            trade = self.agent_manager.create_trade(agent_id, symbol, side, quantity)
            response = trade
        
        else:
            response = {"error": "Endpoint not found"}
        
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def do_OPTIONS(self):
        """Handle preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Override to reduce log noise"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {format % args}")

def start_agent_simulation():
    """Start background agent simulation"""
    agent_manager = TradingAgentManager()
    
    def simulate_trading():
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
        
        while True:
            time.sleep(30)  # Trade every 30 seconds
            
            # Randomly select an agent and symbol
            agent_id = random.choice(list(agent_manager.agents.keys()))
            symbol = random.choice(symbols)
            side = random.choice(['buy', 'sell'])
            quantity = random.randint(1, 20)
            
            # Create simulated trade
            trade = agent_manager.create_trade(agent_id, symbol, side, quantity)
            if 'error' not in trade:
                print(f"📈 Simulated trade: {agent_id} {side} {quantity} {symbol} @ ${trade['price']}")
    
    # Start simulation in background thread
    simulation_thread = threading.Thread(target=simulate_trading, daemon=True)
    simulation_thread.start()
    
    return agent_manager

def main():
    """Start the AI services server"""
    print("🚀 Starting Cival Dashboard AI Services")
    print("=" * 50)
    print(f"Port: {API_PORT}")
    print(f"Anthropic API: {'✅ Configured' if ANTHROPIC_API_KEY else '❌ Missing'}")
    print(f"OpenAI API: {'✅ Configured' if OPENAI_API_KEY else '❌ Missing'}")
    print(f"Alpha Vantage API: {'✅ Configured' if ALPHA_VANTAGE_API_KEY else '❌ Missing'}")
    print("=" * 50)
    
    # Start agent simulation
    start_agent_simulation()
    
    # Start HTTP server
    with socketserver.TCPServer(("", API_PORT), TradingAPIHandler) as httpd:
        print(f"✅ AI Services running on http://localhost:{API_PORT}")
        print(f"🔗 Health check: http://localhost:{API_PORT}/health")
        print(f"🤖 Agents: http://localhost:{API_PORT}/agents")
        print(f"📊 Trades: http://localhost:{API_PORT}/trades")
        print("=" * 50)
        print("Press Ctrl+C to stop")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down AI services...")

if __name__ == "__main__":
    main()