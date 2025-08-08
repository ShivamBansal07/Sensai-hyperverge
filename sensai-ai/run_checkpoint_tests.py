#!/usr/bin/env python3
"""
🧪 SAQ EVALUATION TEST RUNNER
============================

Automated test runner for SAQ evaluation system that:
1. Sets up the virtual environment
2. Starts the backend server
3. Runs comprehensive tests at each checkpoint
4. Generates detailed reports

Usage:
    python run_checkpoint_tests.py [checkpoint_name]
    
Examples:
    python run_checkpoint_tests.py phase_1_models
    python run_checkpoint_tests.py phase_3_api
    python run_checkpoint_tests.py full_integration
"""

import os
import sys
import time
import subprocess
import requests
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import threading
import signal
import psutil

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.utils.test_utils import TestLogger, TestResultsAnalyzer, setup_test_environment


class BackendManager:
    """Manages backend server startup and shutdown for testing"""
    
    def __init__(self, logger: TestLogger):
        self.logger = logger
        self.backend_process = None
        self.base_url = "http://localhost:8001"
        self.health_endpoint = f"{self.base_url}/health"
        
    def start_backend(self) -> bool:
        """Start the backend server in the virtual environment"""
        try:
            self.logger.log("BACKEND", "Starting backend server...")
            
            # Change to sensai-ai directory
            os.chdir(".")
            
            # Activate virtual environment and start server
            if os.name == 'nt':  # Windows
                venv_activate = "venv\\Scripts\\activate"
                python_cmd = "venv\\Scripts\\python"
            else:  # Linux/Mac
                venv_activate = "venv/bin/activate"
                python_cmd = "venv/bin/python"
            
            # Start the backend server
            cmd = [
                python_cmd,
                "-m", "uvicorn",
                "src.api.main:app",
                "--host", "0.0.0.0",
                "--port", "8001",
                "--reload"
            ]
            
            self.logger.log("BACKEND", f"Executing command: {' '.join(cmd)}")
            
            self.backend_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Wait for server to start
            max_retries = 30
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    response = requests.get(f"{self.base_url}/docs", timeout=2)
                    if response.status_code == 200:
                        self.logger.log("BACKEND", "✅ Backend server started successfully")
                        return True
                except requests.exceptions.RequestException:
                    pass
                
                time.sleep(2)
                retry_count += 1
                self.logger.log("BACKEND", f"Waiting for backend... ({retry_count}/{max_retries})")
            
            self.logger.log("BACKEND", "❌ Failed to start backend server")
            return False
            
        except Exception as e:
            self.logger.log("BACKEND", f"Error starting backend: {str(e)}")
            return False
    
    def stop_backend(self):
        """Stop the backend server"""
        if self.backend_process:
            try:
                self.logger.log("BACKEND", "Stopping backend server...")
                
                # Try graceful shutdown first
                self.backend_process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.backend_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown failed
                    self.backend_process.kill()
                    self.backend_process.wait()
                
                self.logger.log("BACKEND", "✅ Backend server stopped")
            except Exception as e:
                self.logger.log("BACKEND", f"Error stopping backend: {str(e)}")
        
        # Kill any remaining uvicorn processes
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'uvicorn' in proc.info['name'] or any('uvicorn' in cmd for cmd in (proc.info['cmdline'] or [])):
                    proc.terminate()
        except:
            pass
    
    def health_check(self) -> bool:
        """Check if backend is healthy"""
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            return response.status_code == 200
        except:
            return False


class CheckpointTestRunner:
    """Runs tests for specific checkpoints"""
    
    def __init__(self):
        self.logger = TestLogger("checkpoint_runner")
        self.analyzer = TestResultsAnalyzer(self.logger)
        self.backend_manager = BackendManager(self.logger)
        
        # Define test phases
        self.test_phases = {
            "phase_1_models": {
                "name": "Phase 1: Pydantic Models",
                "tests": ["test_semantic_evaluation_result_valid",
                         "test_dynamic_feedback_model",
                         "test_saq_evaluation_request_model"],
                "requires_backend": False
            },
            "phase_1_service": {
                "name": "Phase 1: SAQ Evaluator Service",
                "tests": ["test_semantic_evaluation_correct_answer",
                         "test_semantic_evaluation_partial_answer",
                         "test_complete_evaluation_pipeline"],
                "requires_backend": True
            },
            "phase_3_api": {
                "name": "Phase 3: API Enhancement",
                "tests": ["test_enhanced_quiz_answer_endpoint_saq_correct",
                         "test_enhanced_quiz_answer_endpoint_saq_partial",
                         "test_enhanced_quiz_answer_endpoint_error_handling"],
                "requires_backend": True
            },
            "full_integration": {
                "name": "Full Integration Test",
                "tests": ["test_full_saq_evaluation_flow"],
                "requires_backend": True
            }
        }
    
    def run_checkpoint(self, checkpoint_name: str) -> Dict:
        """Run tests for a specific checkpoint"""
        self.logger.log("CHECKPOINT", f"🎯 Running checkpoint: {checkpoint_name}")
        
        if checkpoint_name not in self.test_phases:
            available = ", ".join(self.test_phases.keys())
            self.logger.log("ERROR", f"Unknown checkpoint: {checkpoint_name}. Available: {available}")
            return {"success": False, "error": "Unknown checkpoint"}
        
        phase = self.test_phases[checkpoint_name]
        
        # Start backend if required
        backend_started = False
        if phase["requires_backend"]:
            self.logger.log("SETUP", "Backend required for this phase")
            backend_started = self.backend_manager.start_backend()
            if not backend_started:
                return {"success": False, "error": "Failed to start backend"}
        
        try:
            # Run the tests
            results = self._run_pytest_tests(phase["tests"], checkpoint_name)
            
            # Generate report
            report = {
                "checkpoint": checkpoint_name,
                "phase_name": phase["name"],
                "timestamp": datetime.now().isoformat(),
                "backend_required": phase["requires_backend"],
                "backend_started": backend_started,
                "test_results": results,
                "success": results.get("passed", 0) > 0 and results.get("failed", 1) == 0
            }
            
            self.logger.log("CHECKPOINT", f"✅ Checkpoint {checkpoint_name} completed")
            return report
            
        finally:
            if backend_started:
                self.backend_manager.stop_backend()
    
    def _run_pytest_tests(self, test_list: List[str], checkpoint_name: str) -> Dict:
        """Run specific pytest tests"""
        try:
            # Create pytest command
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/integration/test_saq_evaluation_integration.py",
                "-v",
                "--tb=short",
                "--json-report",
                f"--json-report-file=tests/reports/{checkpoint_name}_pytest_report.json"
            ]
            
            # Add specific test filters if provided
            if test_list:
                # Join test patterns with 'or' for proper pytest syntax
                test_pattern = " or ".join(test_list)
                cmd.extend(["-k", test_pattern])
            
            self.logger.log("TEST", f"Running pytest: {' '.join(cmd)}")
            
            # Run pytest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Parse results
            results = {
                "return_code": result.returncode,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            # Try to parse pytest output for summary
            if result.returncode == 0:  # pytest returns 0 for success
                results["passed"] = 1  # At least one test passed since returncode is 0
                results["failed"] = 0
            else:
                results["failed"] = 1
                results["passed"] = 0
            
            # Try to extract exact numbers from stdout
            stdout_lines = result.stdout.split('\n')
            for line in stdout_lines:
                if 'passed' in line and ('failed' in line or 'error' in line or 'skipped' in line or line.strip().endswith('passed')):
                    # Parse lines like "3 passed in 1.23s" or "2 passed, 1 failed in 1.23s"
                    import re
                    passed_match = re.search(r'(\d+)\s+passed', line)
                    failed_match = re.search(r'(\d+)\s+failed', line)
                    skipped_match = re.search(r'(\d+)\s+skipped', line)
                    
                    if passed_match:
                        results["passed"] = int(passed_match.group(1))
                    if failed_match:
                        results["failed"] = int(failed_match.group(1))
                    if skipped_match:
                        results["skipped"] = int(skipped_match.group(1))
                    break
            
            self.logger.log("TEST", f"Test results: {results['passed']} passed, {results['failed']} failed, {results['skipped']} skipped")
            
            return results
            
        except subprocess.TimeoutExpired:
            self.logger.log("ERROR", "Tests timed out after 5 minutes")
            return {"error": "timeout", "passed": 0, "failed": 1}
        except Exception as e:
            self.logger.log("ERROR", f"Error running tests: {str(e)}")
            return {"error": str(e), "passed": 0, "failed": 1}
    
    def run_all_checkpoints(self) -> Dict:
        """Run all checkpoints in sequence"""
        self.logger.log("RUNNER", "🚀 Starting full checkpoint test run")
        
        all_results = {}
        overall_success = True
        
        for checkpoint_name in self.test_phases.keys():
            result = self.run_checkpoint(checkpoint_name)
            all_results[checkpoint_name] = result
            
            if not result.get("success", False):
                overall_success = False
                self.logger.log("RUNNER", f"❌ Checkpoint {checkpoint_name} failed")
            else:
                self.logger.log("RUNNER", f"✅ Checkpoint {checkpoint_name} passed")
        
        # Generate summary report
        summary = {
            "run_timestamp": datetime.now().isoformat(),
            "overall_success": overall_success,
            "checkpoint_results": all_results,
            "summary": {
                "total_checkpoints": len(self.test_phases),
                "passed_checkpoints": sum(1 for r in all_results.values() if r.get("success", False)),
                "failed_checkpoints": sum(1 for r in all_results.values() if not r.get("success", False))
            }
        }
        
        # Save comprehensive report
        self._save_report(summary, "full_checkpoint_run")
        
        self.logger.log("RUNNER", f"🏁 All checkpoints completed. Success: {overall_success}")
        return summary
    
    def _save_report(self, report: Dict, filename_prefix: str):
        """Save test report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.json"
        
        reports_dir = Path("tests/reports")
        reports_dir.mkdir(exist_ok=True)
        
        filepath = reports_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.log("REPORT", f"Report saved: {filepath}")


def main():
    """Main test runner entry point"""
    # Setup test environment
    setup_test_environment()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        checkpoint_name = sys.argv[1]
        runner = CheckpointTestRunner()
        result = runner.run_checkpoint(checkpoint_name)
        
        if result["success"]:
            print(f"✅ Checkpoint {checkpoint_name} passed!")
            sys.exit(0)
        else:
            print(f"❌ Checkpoint {checkpoint_name} failed!")
            sys.exit(1)
    else:
        # Run all checkpoints
        runner = CheckpointTestRunner()
        result = runner.run_all_checkpoints()
        
        if result["overall_success"]:
            print("✅ All checkpoints passed!")
            sys.exit(0)
        else:
            print("❌ Some checkpoints failed!")
            sys.exit(1)


if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\\n🛑 Test run interrupted by user")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    main()
