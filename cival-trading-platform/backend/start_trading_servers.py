#!/usr/bin/env python3
"""
Startup script for all trading operations MCP servers
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def start_server(script_name, port, server_name):
    """Start a single MCP server"""
    script_path = Path(__file__).parent / "mcp_servers" / script_name
    
    if not script_path.exists():
        print(f"❌ Server script not found: {script_path}")
        return None
    
    try:
        print(f"🚀 Starting {server_name} on port {port}...")
        
        # Start the server process
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(script_path.parent)
        )
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            print(f"✅ {server_name} started successfully (PID: {process.pid})")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ {server_name} failed to start")
            print(f"   stdout: {stdout.decode()}")
            print(f"   stderr: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting {server_name}: {e}")
        return None

def main():
    """Start all trading operations MCP servers"""
    print("🔄 Starting Trading Operations & Intelligence MCP Servers...")
    print("=" * 60)
    
    # Define all trading operations and intelligence servers
    servers = [
        ("trading_gateway.py", 8010, "Trading Gateway"),
        ("order_management.py", 8013, "Order Management System"),
        ("portfolio_management.py", 8014, "Portfolio Management System"),
        ("risk_management.py", 8015, "Risk Management Engine"),
        ("broker_execution.py", 8016, "Broker Execution Engine"),
        ("octagon_intelligence.py", 8020, "Octagon Intelligence System"),
        ("mongodb_intelligence.py", 8021, "MongoDB Intelligence System"),
        ("neo4j_intelligence.py", 8022, "Neo4j Intelligence System"),
    ]
    
    running_processes = []
    
    for script_name, port, server_name in servers:
        process = start_server(script_name, port, server_name)
        if process:
            running_processes.append((process, server_name))
        time.sleep(1)  # Stagger startups
    
    print("\n" + "=" * 60)
    print(f"📊 Started {len(running_processes)}/{len(servers)} servers successfully")
    
    if running_processes:
        print("\n🎯 Running servers:")
        for process, name in running_processes:
            print(f"   • {name} (PID: {process.pid})")
        
        print("\n💡 Press Ctrl+C to stop all servers")
        
        try:
            # Wait for interrupt
            while True:
                time.sleep(1)
                # Check if any processes have died
                for i, (process, name) in enumerate(running_processes):
                    if process.poll() is not None:
                        print(f"⚠️  {name} has stopped unexpectedly")
                        running_processes.pop(i)
                        break
                        
                if not running_processes:
                    print("❌ All servers have stopped")
                    break
                    
        except KeyboardInterrupt:
            print("\n🛑 Stopping all servers...")
            
            for process, name in running_processes:
                try:
                    process.terminate()
                    print(f"🔴 Stopped {name}")
                except:
                    print(f"⚠️  Error stopping {name}")
            
            # Wait for clean shutdown
            time.sleep(2)
            
            # Force kill if necessary
            for process, name in running_processes:
                if process.poll() is None:
                    try:
                        process.kill()
                        print(f"💀 Force killed {name}")
                    except:
                        pass
                        
            print("✅ All servers stopped")
    
    else:
        print("❌ No servers started successfully")
        sys.exit(1)

if __name__ == "__main__":
    main()