# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MCP Servers Available

This project has multiple MCP (Model Context Protocol) servers installed via Smithery CLI:

### Infrastructure & Deployment
- **Railway MCP** (`@mh8974/railway-mcp`) - Railway deployment and project management
- **Redis MCP** (`@redis/mcp-redis`) - Redis database operations
- **Supabase MCP** (`@supabase-community/supabase-mcp`) - Supabase backend services

### Development Tools
- **Code MCP** (`@block/code-mcp`) - Code analysis and manipulation
- **GitHub MCP** (`@smithery-ai/github`) - GitHub repository and issue management
- **Playwright MCP** (`@cloudflare/playwright-mcp`) - Browser automation and testing

### AI & Research
- **Deep Research MCP** (`@ameeralns/DeepResearchMCP`) - Advanced research capabilities
- **Tavily AI MCP** (`@tavily-ai/tavily-mcp`) - AI-powered web search and research

### Productivity
- **Task Manager MCP** (`@kazuph/mcp-taskmanager`) - Task and project management
- **Sequential Thinking MCP** (`@smithery-ai/server-sequential-thinking`) - Enhanced reasoning capabilities
- **Smithery Toolbox** (`@smithery/toolbox`) - General utility tools
- **Desktop Commander** (`@wonderwhy-er/desktop-commander`) - Desktop automation

## Authentication Setup

Based on project history, the following services may require authentication:
- **Railway**: Use `npx @railway/cli login` for Railway deployment access
- **GitHub**: GitHub PAT token configured for repository access
- **Redis**: Redis connection string available for database operations

## Development Workflow

1. **MCP Server Management**: All MCP servers are managed through Smithery CLI with the key `e9820cd5-c518-4f68-8c3b-4ba2e5103a25`
2. **Profile Configuration**: Some services use the profile `faithful-sunset-12VagK`
3. **Service Integration**: Multiple cloud services (Railway, Redis, Supabase, GitHub) are integrated for full-stack development

## Common Commands

```bash
# Install new MCP server
npx -y @smithery/cli@latest install <package-name> --client claude --key e9820cd5-c518-4f68-8c3b-4ba2e5103a25

# Railway login
npx @railway/cli login

# Redis connection
redis-cli -u redis://default:sFVjX2rYkTLYjalcH3b6aKrm1I3CmL5N@redis-13918.c258.us-east-1-4.ec2.redns.redis-cloud.com:13918
```

## Architecture Notes

This is a multi-service development environment with:
- Cloud deployment capabilities (Railway)
- Database access (Redis, Supabase)
- Version control integration (GitHub)
- Browser automation (Playwright)
- AI-enhanced research and development tools

The setup prioritizes integration between multiple cloud services and AI-powered development tools for enhanced productivity and deployment capabilities.