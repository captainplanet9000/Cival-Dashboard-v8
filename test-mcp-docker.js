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
