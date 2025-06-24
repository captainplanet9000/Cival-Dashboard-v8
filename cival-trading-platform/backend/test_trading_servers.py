#!/usr/bin/env python3
"""
Test script for trading operations MCP servers
"""

import sys
import ast
import importlib.util
from pathlib import Path

def validate_server_file(script_path, expected_port, server_name):
    """Validate a server Python file for basic structure"""
    print(f"🔍 Validating {server_name}...")
    
    try:
        # Read the file
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        # Check for required components
        has_fastapi = False
        has_uvicorn_run = False
        has_health_endpoint = False
        has_port_config = False
        
        for node in ast.walk(tree):
            # Check for FastAPI import
            if isinstance(node, ast.ImportFrom) and node.module == 'fastapi':
                has_fastapi = True
            
            # Check for uvicorn.run call
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and \
                   isinstance(node.func.value, ast.Name) and \
                   node.func.value.id == 'uvicorn' and \
                   node.func.attr == 'run':
                    has_uvicorn_run = True
                    
                    # Check for port configuration
                    for keyword in node.keywords:
                        if keyword.arg == 'port' and \
                           isinstance(keyword.value, ast.Constant) and \
                           keyword.value.value == expected_port:
                            has_port_config = True
            
            # Check for health endpoint
            if isinstance(node, ast.AsyncFunctionDef) and node.name == 'health_check':
                has_health_endpoint = True
        
        # Check for specific content patterns
        has_app_definition = 'app = FastAPI(' in content
        has_logging = 'logging' in content
        has_async_functions = 'async def' in content
        
        # Validation results
        checks = [
            (has_fastapi, "FastAPI import"),
            (has_app_definition, "FastAPI app definition"),
            (has_health_endpoint, "Health check endpoint"),
            (has_uvicorn_run, "Uvicorn run call"),
            (has_port_config, f"Port {expected_port} configuration"),
            (has_logging, "Logging setup"),
            (has_async_functions, "Async functions")
        ]
        
        passed_checks = sum(1 for passed, _ in checks if passed)
        total_checks = len(checks)
        
        print(f"   📊 {passed_checks}/{total_checks} checks passed")
        
        for passed, check_name in checks:
            status = "✅" if passed else "❌"
            print(f"   {status} {check_name}")
        
        if passed_checks == total_checks:
            print(f"   🎉 {server_name} validation passed!")
            return True
        else:
            print(f"   ⚠️  {server_name} validation incomplete")
            return False
            
    except Exception as e:
        print(f"   ❌ Error validating {server_name}: {e}")
        return False

def main():
    """Test all trading operations MCP servers"""
    print("🧪 Testing Trading Operations & Intelligence MCP Servers")
    print("=" * 60)
    
    # Define servers to test
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
    
    mcp_servers_dir = Path(__file__).parent / "mcp_servers"
    
    if not mcp_servers_dir.exists():
        print(f"❌ MCP servers directory not found: {mcp_servers_dir}")
        sys.exit(1)
    
    passed_servers = 0
    total_servers = len(servers)
    
    for script_name, port, server_name in servers:
        script_path = mcp_servers_dir / script_name
        
        if not script_path.exists():
            print(f"❌ Server file not found: {script_path}")
            continue
        
        if validate_server_file(script_path, port, server_name):
            passed_servers += 1
        
        print()  # Add spacing between servers
    
    print("=" * 60)
    print(f"📈 Test Results: {passed_servers}/{total_servers} servers passed validation")
    
    if passed_servers == total_servers:
        print("🎯 All trading operations & intelligence MCP servers are properly structured!")
        
        # Additional checks
        print("\n🔧 Additional Validation:")
        
        # Check registry registration
        registry_path = Path(__file__).parent.parent / "src" / "lib" / "mcp" / "registry.ts"
        if registry_path.exists():
            print("✅ MCP registry file exists")
            
            with open(registry_path, 'r') as f:
                registry_content = f.read()
            
            server_ids = ['order_management', 'portfolio_management', 'risk_management', 'broker_execution', 'octagon_intelligence', 'mongodb_intelligence', 'neo4j_intelligence']
            registered_servers = sum(1 for server_id in server_ids if server_id in registry_content)
            
            print(f"✅ {registered_servers}/{len(server_ids)} servers registered in MCP registry")
        else:
            print("⚠️  MCP registry file not found")
        
        # Check startup script
        startup_script = Path(__file__).parent / "start_trading_servers.py"
        if startup_script.exists():
            print("✅ Startup script exists")
        else:
            print("⚠️  Startup script not found")
        
        print("\n🚀 Phase 6 - Intelligence MCP Servers: COMPLETE")
        
    else:
        print("❌ Some servers failed validation. Please review and fix issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()