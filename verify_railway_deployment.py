#!/usr/bin/env python3
"""
Railway Deployment Verification Script
Complete Autonomous Trading System

This script verifies that all components are properly configured
for Railway deployment and the system is production-ready.
"""

import os
import sys
import json
import subprocess
import requests
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RailwayDeploymentVerifier:
    """Comprehensive Railway deployment verification"""
    
    def __init__(self):
        self.root_dir = Path.cwd()
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_checks = 0
        
    def log_result(self, check_name: str, success: bool, message: str = "", warning: bool = False):
        """Log verification result"""
        self.total_checks += 1
        
        if success:
            self.success_count += 1
            logger.info(f"✅ {check_name}: PASSED")
            if message:
                logger.info(f"   {message}")
        elif warning:
            self.warnings.append(f"{check_name}: {message}")
            logger.warning(f"⚠️  {check_name}: WARNING - {message}")
        else:
            self.errors.append(f"{check_name}: {message}")
            logger.error(f"❌ {check_name}: FAILED - {message}")
    
    def verify_file_exists(self, file_path: str, required: bool = True) -> bool:
        """Verify file exists"""
        path = self.root_dir / file_path
        exists = path.exists()
        
        if not exists and required:
            self.log_result(
                f"File Check: {file_path}",
                False,
                f"Required file {file_path} not found"
            )
        elif not exists:
            self.log_result(
                f"File Check: {file_path}",
                True,
                f"Optional file {file_path} not found",
                warning=True
            )
        else:
            self.log_result(
                f"File Check: {file_path}",
                True,
                f"File exists and readable"
            )
        
        return exists
    
    def verify_railway_config(self) -> bool:
        """Verify Railway configuration files"""
        logger.info("\n🔍 Verifying Railway Configuration Files...")
        
        # Check Procfile
        procfile_exists = self.verify_file_exists("Procfile")
        if procfile_exists:
            try:
                with open(self.root_dir / "Procfile", 'r') as f:
                    content = f.read()
                    if "python main_consolidated.py" in content or "gunicorn" in content:
                        self.log_result("Procfile Content", True, "Valid startup command found")
                    else:
                        self.log_result("Procfile Content", False, "No valid startup command found")
            except Exception as e:
                self.log_result("Procfile Content", False, f"Error reading Procfile: {e}")
        
        # Check railway.json
        railway_config_exists = self.verify_file_exists("railway.json")
        if railway_config_exists:
            try:
                with open(self.root_dir / "railway.json", 'r') as f:
                    config = json.load(f)
                    
                # Verify essential config sections
                required_sections = ["build", "deploy", "environments"]
                for section in required_sections:
                    if section in config:
                        self.log_result(f"Railway Config: {section}", True)
                    else:
                        self.log_result(f"Railway Config: {section}", False, f"Missing {section} section")
                        
                # Check production environment
                if "environments" in config and "production" in config["environments"]:
                    self.log_result("Railway Production Environment", True)
                else:
                    self.log_result("Railway Production Environment", False, "Missing production environment config")
                    
            except json.JSONDecodeError as e:
                self.log_result("Railway Config JSON", False, f"Invalid JSON: {e}")
            except Exception as e:
                self.log_result("Railway Config", False, f"Error reading railway.json: {e}")
        
        # Check nixpacks.toml
        nixpacks_exists = self.verify_file_exists("nixpacks.toml", required=False)
        if nixpacks_exists:
            self.log_result("Nixpacks Config", True, "Custom nixpacks configuration found")
        
        # Check environment file
        env_exists = self.verify_file_exists(".env.railway")
        
        return procfile_exists and railway_config_exists
    
    def verify_python_requirements(self) -> bool:
        """Verify Python requirements and dependencies"""
        logger.info("\n🐍 Verifying Python Requirements...")
        
        requirements_exists = self.verify_file_exists("requirements.txt")
        if not requirements_exists:
            return False
        
        try:
            with open(self.root_dir / "requirements.txt", 'r') as f:
                requirements = f.read()
            
            # Check essential dependencies
            essential_deps = [
                "fastapi",
                "uvicorn",
                "sqlalchemy",
                "psycopg2-binary",
                "redis",
                "openai",
                "requests",
                "websockets",
                "pydantic"
            ]
            
            missing_deps = []
            for dep in essential_deps:
                if dep not in requirements.lower():
                    missing_deps.append(dep)
            
            if missing_deps:
                self.log_result(
                    "Essential Dependencies",
                    False,
                    f"Missing dependencies: {', '.join(missing_deps)}"
                )
            else:
                self.log_result("Essential Dependencies", True, "All essential dependencies found")
            
            return len(missing_deps) == 0
            
        except Exception as e:
            self.log_result("Requirements File", False, f"Error reading requirements.txt: {e}")
            return False
    
    def verify_main_application(self) -> bool:
        """Verify main application file"""
        logger.info("\n🚀 Verifying Main Application...")
        
        main_exists = self.verify_file_exists("main_consolidated.py")
        if not main_exists:
            return False
        
        try:
            with open(self.root_dir / "main_consolidated.py", 'r') as f:
                content = f.read()
            
            # Check for essential components
            essential_components = [
                "FastAPI",
                "uvicorn.run",
                "service_registry",
                "__name__ == \"__main__\""
            ]
            
            missing_components = []
            for component in essential_components:
                if component not in content:
                    missing_components.append(component)
            
            if missing_components:
                self.log_result(
                    "Main Application Components",
                    False,
                    f"Missing components: {', '.join(missing_components)}"
                )
            else:
                self.log_result("Main Application Components", True, "All essential components found")
            
            return len(missing_components) == 0
            
        except Exception as e:
            self.log_result("Main Application", False, f"Error reading main_consolidated.py: {e}")
            return False
    
    def verify_directory_structure(self) -> bool:
        """Verify expected directory structure"""
        logger.info("\n📁 Verifying Directory Structure...")
        
        required_dirs = [
            "core",
            "services",
            "models",
            "api"
        ]
        
        optional_dirs = [
            "agents",
            "farms", 
            "goals",
            "frontend",
            "dashboard",
            "scripts",
            "static",
            "templates"
        ]
        
        all_good = True
        
        for dir_name in required_dirs:
            if (self.root_dir / dir_name).exists():
                self.log_result(f"Directory: {dir_name}", True)
            else:
                self.log_result(f"Directory: {dir_name}", False, f"Required directory {dir_name} not found")
                all_good = False
        
        for dir_name in optional_dirs:
            if (self.root_dir / dir_name).exists():
                self.log_result(f"Directory: {dir_name}", True, "Optional directory found")
            else:
                self.log_result(f"Directory: {dir_name}", True, "Optional directory not found", warning=True)
        
        return all_good
    
    def verify_environment_variables(self) -> bool:
        """Verify environment variable configuration"""
        logger.info("\n🔐 Verifying Environment Variables...")
        
        env_file = self.root_dir / ".env.railway"
        if not env_file.exists():
            self.log_result("Environment File", False, ".env.railway file not found")
            return False
        
        try:
            with open(env_file, 'r') as f:
                env_content = f.read()
            
            # Check for essential environment variables
            essential_vars = [
                "DATABASE_URL",
                "REDIS_URL",
                "OPENROUTER_API_KEY",
                "JWT_SECRET_KEY",
                "APP_PORT",
                "ENVIRONMENT"
            ]
            
            missing_vars = []
            for var in essential_vars:
                if f"{var}=" not in env_content:
                    missing_vars.append(var)
            
            if missing_vars:
                self.log_result(
                    "Essential Environment Variables",
                    False,
                    f"Missing variables: {', '.join(missing_vars)}"
                )
            else:
                self.log_result("Essential Environment Variables", True, "All essential variables defined")
            
            # Check for placeholder values
            placeholders = [
                "[your-",
                "[project-ref]",
                "[password]",
                "[generate-"
            ]
            
            placeholder_count = sum(env_content.count(placeholder) for placeholder in placeholders)
            if placeholder_count > 0:
                self.log_result(
                    "Environment Variable Values",
                    True,
                    f"Found {placeholder_count} placeholder values - remember to replace before deployment",
                    warning=True
                )
            else:
                self.log_result("Environment Variable Values", True, "No placeholder values found")
            
            return len(missing_vars) == 0
            
        except Exception as e:
            self.log_result("Environment Variables", False, f"Error reading .env.railway: {e}")
            return False
    
    def verify_frontend_build(self) -> bool:
        """Verify frontend configuration if present"""
        logger.info("\n🎨 Verifying Frontend Configuration...")
        
        frontend_dir = self.root_dir / "frontend"
        if not frontend_dir.exists():
            self.log_result("Frontend Directory", True, "No frontend directory found - backend only deployment", warning=True)
            return True
        
        # Check package.json
        package_json = frontend_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    package_data = json.load(f)
                
                # Check for build script
                scripts = package_data.get("scripts", {})
                if "build" in scripts:
                    self.log_result("Frontend Build Script", True)
                else:
                    self.log_result("Frontend Build Script", False, "No build script found in package.json")
                
                # Check for essential dependencies
                deps = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                if "react" in deps or "next" in deps or "vue" in deps:
                    self.log_result("Frontend Framework", True, f"Framework detected: {list(deps.keys())}")
                else:
                    self.log_result("Frontend Framework", True, "No major framework detected", warning=True)
                
                return "build" in scripts
                
            except Exception as e:
                self.log_result("Frontend Package.json", False, f"Error reading package.json: {e}")
                return False
        else:
            self.log_result("Frontend Package.json", False, "package.json not found in frontend directory")
            return False
    
    def verify_database_connection(self) -> bool:
        """Verify database configuration (without actual connection)"""
        logger.info("\n🗄️ Verifying Database Configuration...")
        
        # Check if database models exist
        models_dir = self.root_dir / "models"
        if models_dir.exists():
            model_files = list(models_dir.glob("*.py"))
            if model_files:
                self.log_result("Database Models", True, f"Found {len(model_files)} model files")
            else:
                self.log_result("Database Models", False, "No Python model files found")
        else:
            self.log_result("Database Models", False, "Models directory not found")
        
        # Check for database configuration in main file
        main_file = self.root_dir / "main_consolidated.py"
        if main_file.exists():
            try:
                with open(main_file, 'r') as f:
                    content = f.read()
                
                db_indicators = ["sqlalchemy", "database", "create_engine", "sessionmaker"]
                found_indicators = [indicator for indicator in db_indicators if indicator in content.lower()]
                
                if found_indicators:
                    self.log_result("Database Integration", True, f"Found database indicators: {', '.join(found_indicators)}")
                else:
                    self.log_result("Database Integration", True, "No database indicators found", warning=True)
                    
            except Exception as e:
                self.log_result("Database Configuration", False, f"Error checking database config: {e}")
        
        return True
    
    def verify_security_configuration(self) -> bool:
        """Verify security configuration"""
        logger.info("\n🔒 Verifying Security Configuration...")
        
        env_file = self.root_dir / ".env.railway"
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    env_content = f.read()
                
                # Check security-related configurations
                security_vars = [
                    "JWT_SECRET_KEY",
                    "API_KEY", 
                    "CORS_ORIGINS",
                    "SECURE_COOKIES",
                    "CSRF_PROTECTION"
                ]
                
                security_score = 0
                for var in security_vars:
                    if f"{var}=" in env_content:
                        security_score += 1
                
                if security_score >= 3:
                    self.log_result("Security Configuration", True, f"Found {security_score}/5 security configurations")
                else:
                    self.log_result("Security Configuration", False, f"Only found {security_score}/5 security configurations")
                
                # Check for SSL/HTTPS configuration
                if "SSL_REDIRECT=true" in env_content or "HTTPS" in env_content:
                    self.log_result("SSL Configuration", True)
                else:
                    self.log_result("SSL Configuration", True, "No explicit SSL configuration found", warning=True)
                
                return security_score >= 3
                
            except Exception as e:
                self.log_result("Security Configuration", False, f"Error checking security config: {e}")
                return False
        
        return False
    
    def verify_performance_optimization(self) -> bool:
        """Verify performance optimization settings"""
        logger.info("\n⚡ Verifying Performance Optimization...")
        
        # Check nixpacks configuration
        nixpacks_file = self.root_dir / "nixpacks.toml"
        if nixpacks_file.exists():
            try:
                with open(nixpacks_file, 'r') as f:
                    nixpacks_content = f.read()
                
                optimization_features = [
                    "cache",
                    "compression",
                    "optimization",
                    "incremental_builds",
                    "parallel_builds"
                ]
                
                found_features = [feature for feature in optimization_features if feature in nixpacks_content.lower()]
                
                if found_features:
                    self.log_result("Build Optimization", True, f"Found optimizations: {', '.join(found_features)}")
                else:
                    self.log_result("Build Optimization", True, "No specific optimizations found", warning=True)
                    
            except Exception as e:
                self.log_result("Build Optimization", False, f"Error checking nixpacks config: {e}")
        
        # Check railway.json for resource limits
        railway_file = self.root_dir / "railway.json"
        if railway_file.exists():
            try:
                with open(railway_file, 'r') as f:
                    railway_config = json.load(f)
                
                if "services" in railway_config and railway_config["services"]:
                    service = railway_config["services"][0]
                    if "resources" in service:
                        self.log_result("Resource Limits", True, "Resource limits configured")
                    else:
                        self.log_result("Resource Limits", True, "No resource limits set", warning=True)
                        
            except Exception as e:
                self.log_result("Resource Configuration", False, f"Error checking resource config: {e}")
        
        return True
    
    def run_syntax_check(self) -> bool:
        """Run Python syntax check on main files"""
        logger.info("\n🔍 Running Syntax Checks...")
        
        python_files = [
            "main_consolidated.py",
            "core/service_registry.py",
            "verify_railway_deployment.py"
        ]
        
        syntax_errors = 0
        
        for file_path in python_files:
            full_path = self.root_dir / file_path
            if full_path.exists():
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "py_compile", str(full_path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        self.log_result(f"Syntax Check: {file_path}", True)
                    else:
                        self.log_result(f"Syntax Check: {file_path}", False, f"Syntax error: {result.stderr}")
                        syntax_errors += 1
                        
                except subprocess.TimeoutExpired:
                    self.log_result(f"Syntax Check: {file_path}", False, "Syntax check timed out")
                    syntax_errors += 1
                except Exception as e:
                    self.log_result(f"Syntax Check: {file_path}", False, f"Error running syntax check: {e}")
                    syntax_errors += 1
            else:
                self.log_result(f"Syntax Check: {file_path}", True, "File not found - skipping", warning=True)
        
        return syntax_errors == 0
    
    def generate_deployment_checklist(self) -> str:
        """Generate deployment checklist"""
        checklist = """
🚀 RAILWAY DEPLOYMENT CHECKLIST

Before deploying to Railway, ensure you have:

✅ Database Setup:
   - Created Supabase project
   - Noted DATABASE_URL, SUPABASE_URL, and API keys
   - Created all required tables using the provided schema

✅ External API Keys:
   - OpenRouter API key for LLM services
   - Exchange API keys (Hyperliquid, etc.)
   - News/Market data API keys
   - Notification service keys (optional)

✅ Security Configuration:
   - Generated strong JWT_SECRET_KEY
   - Generated API_KEY for internal services
   - Set CORS_ORIGINS to your domain
   - Enabled SSL_REDIRECT and SECURE_COOKIES

✅ Railway Project Setup:
   - Create new Railway project
   - Connect GitHub repository
   - Add PostgreSQL plugin (if not using Supabase)
   - Add Redis plugin
   - Configure custom domain (optional)

✅ Environment Variables:
   - Copy variables from .env.railway to Railway dashboard
   - Replace all placeholder values with actual credentials
   - Set ENVIRONMENT=production
   - Configure RAILWAY_DOMAIN

✅ Deployment Process:
   1. Push code to GitHub main branch
   2. Railway will auto-deploy from nixpacks.toml/Procfile
   3. Monitor deployment logs in Railway dashboard
   4. Test health endpoint: https://[your-domain]/health
   5. Verify WebSocket connections work
   6. Test API endpoints

✅ Post-Deployment:
   - Set up monitoring and alerts
   - Configure backup schedules
   - Test trading functionality in paper mode
   - Monitor performance and resource usage
   - Set up log aggregation

🔧 Useful Railway CLI Commands:
   railway login
   railway link [project-id]
   railway up
   railway logs
   railway status
   railway variables

🆘 Troubleshooting:
   - Check Railway deployment logs
   - Verify environment variables are set
   - Test database connectivity
   - Check external API rate limits
   - Monitor resource usage

For support: Railway Discord or GitHub Issues
"""
        return checklist
    
    def run_verification(self) -> bool:
        """Run complete verification suite"""
        logger.info("🔍 Starting Railway Deployment Verification...")
        logger.info("=" * 60)
        
        # Run all verification steps
        verification_steps = [
            ("Railway Configuration", self.verify_railway_config),
            ("Python Requirements", self.verify_python_requirements),
            ("Main Application", self.verify_main_application),
            ("Directory Structure", self.verify_directory_structure),
            ("Environment Variables", self.verify_environment_variables),
            ("Frontend Configuration", self.verify_frontend_build),
            ("Database Configuration", self.verify_database_connection),
            ("Security Configuration", self.verify_security_configuration),
            ("Performance Optimization", self.verify_performance_optimization),
            ("Syntax Checks", self.run_syntax_check)
        ]
        
        all_passed = True
        for step_name, step_func in verification_steps:
            try:
                step_result = step_func()
                if not step_result:
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ {step_name}: EXCEPTION - {e}")
                self.errors.append(f"{step_name}: Exception - {e}")
                all_passed = False
        
        # Print summary
        self.print_summary()
        
        return all_passed
    
    def print_summary(self):
        """Print verification summary"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 VERIFICATION SUMMARY")
        logger.info("=" * 60)
        
        success_rate = (self.success_count / self.total_checks * 100) if self.total_checks > 0 else 0
        
        logger.info(f"✅ Passed: {self.success_count}/{self.total_checks} ({success_rate:.1f}%)")
        logger.info(f"⚠️  Warnings: {len(self.warnings)}")
        logger.info(f"❌ Errors: {len(self.errors)}")
        
        if self.warnings:
            logger.info("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                logger.warning(f"   • {warning}")
        
        if self.errors:
            logger.info("\n❌ ERRORS:")
            for error in self.errors:
                logger.error(f"   • {error}")
        
        # Deployment readiness
        if not self.errors:
            if not self.warnings:
                logger.info("\n🎉 DEPLOYMENT READY!")
                logger.info("Your application is ready for Railway deployment.")
            else:
                logger.info("\n✅ MOSTLY READY!")
                logger.info("Your application can be deployed, but please review warnings.")
        else:
            logger.info("\n🚫 NOT READY FOR DEPLOYMENT")
            logger.info("Please fix all errors before deploying to Railway.")
        
        # Print checklist
        logger.info(self.generate_deployment_checklist())

def main():
    """Main verification function"""
    verifier = RailwayDeploymentVerifier()
    
    try:
        success = verifier.run_verification()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"🚨 Verification failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()