#!/bin/bash

# Fix MCP Servers Script
# This script checks and fixes common MCP server issues

echo "🔧 MCP Server Fix Script"
echo "========================"

# 1. Check if Docker is running
echo "1. Checking Docker status..."
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        echo "✅ Docker is running"
    else
        echo "❌ Docker is installed but not running"
        echo "   Try: sudo systemctl start docker"
    fi
else
    echo "❌ Docker is not installed"
    echo "   For WSL2, ensure Docker Desktop is running on Windows"
fi

# 2. Check Node.js and npm
echo -e "\n2. Checking Node.js and npm..."
if command -v node &> /dev/null; then
    echo "✅ Node.js version: $(node --version)"
else
    echo "❌ Node.js is not installed"
fi

if command -v npm &> /dev/null; then
    echo "✅ npm version: $(npm --version)"
else
    echo "❌ npm is not installed"
fi

# 3. Test MCP server connectivity
echo -e "\n3. Testing MCP server connectivity..."
# Test one of the configured MCP servers
npx -y @smithery/cli@latest --version &> /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Smithery CLI is accessible"
else
    echo "❌ Cannot access Smithery CLI"
    echo "   This might be a network issue"
fi

# 4. Check for any error logs
echo -e "\n4. Checking for Claude logs..."
if [ -d "$HOME/.config/Claude/logs" ]; then
    echo "📋 Recent log entries:"
    tail -n 20 "$HOME/.config/Claude/logs/"*.log 2>/dev/null | grep -i "error\|fail" | tail -5
else
    echo "ℹ️  No Claude log directory found"
fi

# 5. Validate MCP configuration
echo -e "\n5. Validating MCP configuration..."
CONFIG_FILE="$HOME/.config/Claude/claude_desktop_config.json"
if [ -f "$CONFIG_FILE" ]; then
    echo "✅ Configuration file exists"
    # Check if JSON is valid
    if python3 -m json.tool "$CONFIG_FILE" > /dev/null 2>&1; then
        echo "✅ JSON configuration is valid"
    else
        echo "❌ JSON configuration is invalid"
        echo "   Run: python3 -m json.tool $CONFIG_FILE"
    fi
else
    echo "❌ Configuration file not found at $CONFIG_FILE"
fi

# 6. Recommendations
echo -e "\n📌 Recommendations:"
echo "========================"

# Check if we're in WSL
if grep -qi microsoft /proc/version 2>/dev/null; then
    echo "🔹 WSL detected - ensure Docker Desktop is running on Windows"
    echo "🔹 Check Docker Desktop settings > Resources > WSL Integration"
fi

echo "🔹 Try restarting Claude Desktop after fixing any issues"
echo "🔹 If MCP_DOCKER continues to fail, you can:"
echo "   - Remove Docker-based MCP servers from configuration"
echo "   - Use alternative non-Docker MCP servers"
echo "   - Check if specific Docker containers need to be built"

# 7. Quick fix attempt
echo -e "\n🔧 Attempting quick fixes..."
# Clear npm cache
npm cache clean --force 2>/dev/null && echo "✅ Cleared npm cache" || echo "ℹ️  Could not clear npm cache"

# Create a test script for MCP Docker
echo -e "\n📝 Creating MCP Docker test script..."
cat > /home/anthony/test-mcp-docker.js << 'EOF'
// Test MCP Docker connectivity
const { spawn } = require('child_process');

console.log('Testing MCP Docker setup...');

// Check if docker is available
const docker = spawn('docker', ['--version']);

docker.on('error', (err) => {
    console.error('❌ Docker not found:', err.message);
    console.log('   Please ensure Docker is installed and running');
});

docker.stdout.on('data', (data) => {
    console.log('✅ Docker version:', data.toString().trim());
});

docker.on('close', (code) => {
    if (code === 0) {
        console.log('✅ Docker check completed successfully');
    }
});
EOF

echo "✅ Created test-mcp-docker.js"
echo "   Run: node /home/anthony/test-mcp-docker.js"

echo -e "\n✨ Fix script completed!"
echo "========================"