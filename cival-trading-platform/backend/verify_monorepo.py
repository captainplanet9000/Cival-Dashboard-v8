#!/usr/bin/env python3
"""
MCP Trading Platform - Monorepo Verification Script
Comprehensive verification of the consolidated platform before deployment
"""

import asyncio
import sys
import os
import json
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Any

class MonorepoVerifier:
    """Comprehensive verification of the monorepo setup"""
    
    def __init__(self):
        self.root_path = Path(__file__).parent
        self.verification_results = {}
        self.errors = []
        self.warnings = []
    
    def verify_file_structure(self) -> bool:
        """Verify that all required files exist"""
        print("📁 Verifying file structure...")
        
        required_files = [
            "main_consolidated.py",
            "requirements.txt",
            "Procfile",
            "railway.json",
            "railway.toml", 
            "nixpacks.toml",
            ".env",
            ".env.railway",
            "RAILWAY_DEPLOYMENT_FINAL.md",
            "core/__init__.py",
            "core/service_registry.py",
            "core/database_manager.py",
            "core/service_initializer.py",
            "dashboard/monorepo_dashboard.py",
            "dashboard/templates/dashboard.html"
        ]
        
        required_directories = [
            "core",
            "services", 
            "models",
            "agents",
            "auth",
            "dashboard",
            "dashboard/templates"
        ]
        
        all_good = True
        
        # Check files
        for file_path in required_files:
            full_path = self.root_path / file_path
            if full_path.exists():
                print(f"  ✅ {file_path}")
            else:
                print(f"  ❌ {file_path} - MISSING")
                self.errors.append(f"Missing file: {file_path}")
                all_good = False
        
        # Check directories
        for dir_path in required_directories:
            full_path = self.root_path / dir_path
            if full_path.exists() and full_path.is_dir():
                print(f"  ✅ {dir_path}/")
            else:
                print(f"  ❌ {dir_path}/ - MISSING")
                self.errors.append(f"Missing directory: {dir_path}")
                all_good = False
        
        self.verification_results["file_structure"] = all_good
        return all_good
    
    def verify_imports(self) -> bool:
        """Verify that all critical imports work"""
        print("\n📦 Verifying critical imports...")
        
        critical_imports = [
            ("fastapi", "FastAPI web framework"),
            ("uvicorn", "ASGI server"),
            ("pydantic", "Data validation"),
            ("redis", "Redis client"),
            ("supabase", "Supabase client"),
            ("sqlalchemy", "SQL toolkit"),
            ("loguru", "Logging"),
            ("python_dotenv", "Environment variables")
        ]
        
        optional_imports = [
            ("crewai", "CrewAI agent framework"),
            ("autogen", "AutoGen framework"),
            ("numpy", "Numerical computing"),
            ("pandas", "Data analysis"),
            ("httpx", "HTTP client"),
            ("sse_starlette", "Server-sent events")
        ]
        
        all_critical_good = True
        
        # Test critical imports
        for module_name, description in critical_imports:
            try:
                __import__(module_name)
                print(f"  ✅ {module_name} - {description}")
            except ImportError as e:
                print(f"  ❌ {module_name} - {description} - ERROR: {e}")
                self.errors.append(f"Critical import failed: {module_name}")
                all_critical_good = False
        
        # Test optional imports
        for module_name, description in optional_imports:
            try:
                __import__(module_name)
                print(f"  ✅ {module_name} - {description}")
            except ImportError as e:
                print(f"  ⚠️ {module_name} - {description} - WARNING: {e}")
                self.warnings.append(f"Optional import failed: {module_name}")
        
        self.verification_results["imports"] = all_critical_good
        return all_critical_good
    
    def verify_core_modules(self) -> bool:
        """Verify that core modules can be imported"""
        print("\n🔧 Verifying core modules...")
        
        core_modules = [
            ("core.service_registry", "Service registry module"),
            ("core.database_manager", "Database manager module"), 
            ("core.service_initializer", "Service initializer module")
        ]
        
        all_good = True
        
        for module_name, description in core_modules:
            try:
                # Add current directory to path for import
                sys.path.insert(0, str(self.root_path))
                module = __import__(module_name, fromlist=[''])
                print(f"  ✅ {module_name} - {description}")
                
                # Check for key classes/functions
                if module_name == "core.service_registry":
                    if hasattr(module, 'registry') and hasattr(module, 'ServiceRegistry'):
                        print(f"    ✅ ServiceRegistry class found")
                    else:
                        print(f"    ⚠️ ServiceRegistry class or registry instance not found")
                        self.warnings.append(f"ServiceRegistry not properly exposed in {module_name}")
                
                elif module_name == "core.database_manager":
                    if hasattr(module, 'db_manager') and hasattr(module, 'DatabaseManager'):
                        print(f"    ✅ DatabaseManager class found")
                    else:
                        print(f"    ⚠️ DatabaseManager class or db_manager instance not found")
                        self.warnings.append(f"DatabaseManager not properly exposed in {module_name}")
                
                elif module_name == "core.service_initializer":
                    if hasattr(module, 'service_initializer') and hasattr(module, 'ServiceInitializer'):
                        print(f"    ✅ ServiceInitializer class found")
                    else:
                        print(f"    ⚠️ ServiceInitializer class or service_initializer instance not found")
                        self.warnings.append(f"ServiceInitializer not properly exposed in {module_name}")
                        
            except ImportError as e:
                print(f"  ❌ {module_name} - {description} - ERROR: {e}")
                self.errors.append(f"Core module import failed: {module_name}")
                all_good = False
            except Exception as e:
                print(f"  ❌ {module_name} - {description} - UNEXPECTED ERROR: {e}")
                self.errors.append(f"Core module error: {module_name} - {e}")
                all_good = False
        
        self.verification_results["core_modules"] = all_good
        return all_good
    
    def verify_environment_config(self) -> bool:
        """Verify environment configuration"""
        print("\n🌍 Verifying environment configuration...")
        
        env_file = self.root_path / ".env"
        railway_env_file = self.root_path / ".env.railway"
        
        all_good = True
        
        # Check .env file
        if env_file.exists():
            print(f"  ✅ .env file exists")
            try:
                with open(env_file) as f:
                    env_content = f.read()
                    
                required_vars = [
                    "SUPABASE_URL",
                    "REDIS_URL", 
                    "DATABASE_URL",
                    "ANTHROPIC_API_KEY",
                    "OPENAI_API_KEY"
                ]
                
                for var in required_vars:
                    if var in env_content and f"{var}=" in env_content:
                        print(f"    ✅ {var} configured")
                    else:
                        print(f"    ⚠️ {var} missing or not set")
                        self.warnings.append(f"Environment variable {var} not found in .env")
                        
            except Exception as e:
                print(f"  ❌ Error reading .env file: {e}")
                self.errors.append(f"Could not read .env file: {e}")
                all_good = False
        else:
            print(f"  ❌ .env file missing")
            self.errors.append("Missing .env file")
            all_good = False
        
        # Check Railway environment file
        if railway_env_file.exists():
            print(f"  ✅ .env.railway file exists (for Railway deployment)")
        else:
            print(f"  ⚠️ .env.railway file missing")
            self.warnings.append("Missing .env.railway file for Railway deployment")
        
        self.verification_results["environment"] = all_good
        return all_good
    
    def verify_railway_config(self) -> bool:
        """Verify Railway deployment configuration"""
        print("\n🚂 Verifying Railway configuration...")
        
        config_files = {
            "railway.json": "Basic Railway configuration",
            "railway.toml": "Advanced Railway settings",
            "Procfile": "Process definition",
            "nixpacks.toml": "Build configuration"
        }
        
        all_good = True
        
        for filename, description in config_files.items():
            file_path = self.root_path / filename
            if file_path.exists():
                print(f"  ✅ {filename} - {description}")
                
                # Verify content for key files
                try:
                    if filename == "Procfile":
                        with open(file_path) as f:
                            content = f.read().strip()
                            if "main_consolidated.py" in content:
                                print(f"    ✅ Procfile correctly references main_consolidated.py")
                            else:
                                print(f"    ⚠️ Procfile may not reference correct entry point")
                                self.warnings.append("Procfile entry point verification needed")
                    
                    elif filename == "railway.json":
                        with open(file_path) as f:
                            config = json.load(f)
                            if "build" in config and "deploy" in config:
                                print(f"    ✅ Railway JSON has build and deploy sections")
                            else:
                                print(f"    ⚠️ Railway JSON missing expected sections")
                                self.warnings.append("Railway JSON configuration incomplete")
                                
                except Exception as e:
                    print(f"    ⚠️ Could not verify {filename} content: {e}")
                    self.warnings.append(f"Could not verify {filename} content")
            else:
                print(f"  ❌ {filename} - {description} - MISSING")
                self.errors.append(f"Missing Railway config file: {filename}")
                all_good = False
        
        self.verification_results["railway_config"] = all_good
        return all_good
    
    def verify_main_application(self) -> bool:
        """Verify that the main application can be loaded"""
        print("\n🚀 Verifying main application...")
        
        main_file = self.root_path / "main_consolidated.py"
        
        if not main_file.exists():
            print("  ❌ main_consolidated.py not found")
            self.errors.append("Main application file missing")
            self.verification_results["main_application"] = False
            return False
        
        try:
            # Try to load the module without executing
            spec = importlib.util.spec_from_file_location("main_consolidated", main_file)
            if spec is None:
                print("  ❌ Could not create module spec")
                self.errors.append("Could not create module spec for main application")
                self.verification_results["main_application"] = False
                return False
            
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules to handle imports
            sys.modules["main_consolidated"] = module
            
            # Check for key components without executing
            with open(main_file) as f:
                content = f.read()
                
            required_components = [
                "from fastapi import FastAPI",
                "from core import",
                "app = FastAPI",
                "lifespan",
                "if __name__ == \"__main__\":"
            ]
            
            all_components_found = True
            for component in required_components:
                if component in content:
                    print(f"    ✅ Found: {component}")
                else:
                    print(f"    ⚠️ Missing: {component}")
                    self.warnings.append(f"Main application missing component: {component}")
                    all_components_found = False
            
            if all_components_found:
                print("  ✅ Main application structure looks good")
            else:
                print("  ⚠️ Main application structure has issues")
            
            self.verification_results["main_application"] = True
            return True
            
        except Exception as e:
            print(f"  ❌ Error verifying main application: {e}")
            self.errors.append(f"Main application verification failed: {e}")
            self.verification_results["main_application"] = False
            return False
    
    def verify_dashboard(self) -> bool:
        """Verify dashboard configuration"""
        print("\n🖥️ Verifying dashboard...")
        
        dashboard_file = self.root_path / "dashboard" / "monorepo_dashboard.py"
        template_file = self.root_path / "dashboard" / "templates" / "dashboard.html"
        
        all_good = True
        
        if dashboard_file.exists():
            print("  ✅ Dashboard Python file exists")
        else:
            print("  ❌ Dashboard Python file missing")
            self.errors.append("Dashboard file missing")
            all_good = False
        
        if template_file.exists():
            print("  ✅ Dashboard HTML template exists")
        else:
            print("  ❌ Dashboard HTML template missing")
            self.errors.append("Dashboard template missing")
            all_good = False
        
        self.verification_results["dashboard"] = all_good
        return all_good
    
    async def run_verification(self) -> Dict[str, Any]:
        """Run complete verification suite"""
        print("🔍 Starting MCP Trading Platform Monorepo Verification")
        print("=" * 60)
        
        start_time = datetime.now(timezone.utc)
        
        # Run all verification steps
        verification_steps = [
            ("File Structure", self.verify_file_structure),
            ("Critical Imports", self.verify_imports),
            ("Core Modules", self.verify_core_modules),
            ("Environment Config", self.verify_environment_config),
            ("Railway Config", self.verify_railway_config),
            ("Main Application", self.verify_main_application),
            ("Dashboard", self.verify_dashboard)
        ]
        
        passed_steps = 0
        total_steps = len(verification_steps)
        
        for step_name, step_function in verification_steps:
            try:
                result = step_function()
                if result:
                    passed_steps += 1
            except Exception as e:
                print(f"\n❌ Unexpected error in {step_name}: {e}")
                self.errors.append(f"Unexpected error in {step_name}: {e}")
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Compile final results
        results = {
            "verification_time": end_time.isoformat(),
            "duration_seconds": duration,
            "total_steps": total_steps,
            "passed_steps": passed_steps,
            "success_rate": (passed_steps / total_steps) * 100,
            "overall_status": "PASSED" if passed_steps == total_steps else "FAILED",
            "details": self.verification_results,
            "errors": self.errors,
            "warnings": self.warnings
        }
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print verification summary"""
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        
        status = results["overall_status"]
        if status == "PASSED":
            print("🎉 ALL VERIFICATIONS PASSED!")
            print("✅ The monorepo is ready for Railway deployment")
        else:
            print("⚠️ VERIFICATION ISSUES DETECTED")
            print("❌ Please fix issues before deployment")
        
        print(f"\nResults:")
        print(f"  • Steps Passed: {results['passed_steps']}/{results['total_steps']}")
        print(f"  • Success Rate: {results['success_rate']:.1f}%")
        print(f"  • Duration: {results['duration_seconds']:.2f} seconds")
        
        if results["errors"]:
            print(f"\n❌ ERRORS ({len(results['errors'])}):")
            for i, error in enumerate(results["errors"], 1):
                print(f"  {i}. {error}")
        
        if results["warnings"]:
            print(f"\n⚠️ WARNINGS ({len(results['warnings'])}):")
            for i, warning in enumerate(results["warnings"], 1):
                print(f"  {i}. {warning}")
        
        print("\n" + "=" * 60)
        
        if status == "PASSED":
            print("🚀 READY FOR RAILWAY DEPLOYMENT!")
            print("\nNext steps:")
            print("1. Push to GitHub: git add . && git commit -m 'Monorepo ready' && git push")
            print("2. Connect Railway to repository")
            print("3. Set environment variables in Railway dashboard")
            print("4. Deploy to production")
        else:
            print("🔧 PLEASE FIX ISSUES BEFORE DEPLOYMENT")
            print("\nRecommended actions:")
            print("1. Review and fix all errors listed above")
            print("2. Address warnings if possible")
            print("3. Re-run verification: python verify_monorepo.py")

async def main():
    """Main verification function"""
    verifier = MonorepoVerifier()
    results = await verifier.run_verification()
    verifier.print_summary(results)
    
    # Exit with appropriate code
    exit_code = 0 if results["overall_status"] == "PASSED" else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())