"""
🛠️ TEST UTILITIES & LOGGING INFRASTRUCTURE
==========================================

Utilities for SAQ evaluation testing and comprehensive logging system.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import traceback

class TestLogger:
    """Enhanced logging system for test tracking and debugging"""
    
    def __init__(self, test_suite_name: str):
        self.test_suite_name = test_suite_name
        self.logs_dir = Path("tests/logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_dir / f"{test_suite_name}_{timestamp}.log"
        
        # Initialize log file
        self.log("INIT", f"Starting test suite: {test_suite_name}")
    
    def log(self, level: str, message: str, data: Optional[Dict] = None):
        """Log message with timestamp and optional data"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        log_entry = {
            "timestamp": timestamp,
            "suite": self.test_suite_name,
            "level": level,
            "message": message
        }
        
        if data:
            log_entry["data"] = data
        
        # Write to file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, indent=2, ensure_ascii=False) + "\n")
        
        # Also print to console for immediate feedback
        console_msg = f"[{timestamp}] [{level}] {message}"
        if data:
            console_msg += f" | Data: {json.dumps(data, indent=2)}"
        
        print(console_msg)
    
    def log_test_start(self, test_name: str, description: str):
        """Log test start with detailed info"""
        self.log("TEST_START", f"🧪 {test_name}", {
            "description": description,
            "test_file": str(self.log_file)
        })
    
    def log_test_success(self, test_name: str, result: Any = None):
        """Log successful test completion"""
        data = {"result": str(result)} if result else None
        self.log("TEST_SUCCESS", f"✅ {test_name}", data)
    
    def log_test_failure(self, test_name: str, error: Exception):
        """Log test failure with full error details"""
        self.log("TEST_FAILURE", f"❌ {test_name}", {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc()
        })
    
    def log_checkpoint(self, phase: str, status: str, details: Optional[Dict] = None):
        """Log checkpoint completion"""
        self.log("CHECKPOINT", f"📍 Phase {phase}: {status}", details)
    
    def log_performance(self, operation: str, duration_ms: float, details: Optional[Dict] = None):
        """Log performance metrics"""
        perf_data = {"duration_ms": duration_ms}
        if details:
            perf_data.update(details)
        
        self.log("PERFORMANCE", f"⏱️ {operation}", perf_data)
    
    def log_llm_interaction(self, prompt: str, response: str, model: str = "unknown"):
        """Log LLM interactions for debugging"""
        self.log("LLM_INTERACTION", f"🤖 Model: {model}", {
            "prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt,
            "response": response[:500] + "..." if len(response) > 500 else response,
            "full_prompt_length": len(prompt),
            "full_response_length": len(response)
        })


class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_test_question(question_type: str = "saq", difficulty: str = "medium") -> Dict:
        """Create test question data"""
        base_question = {
            "question_id": f"test_q_{datetime.now().strftime('%H%M%S')}",
            "page_number": 1,
            "question_type": question_type,
        }
        
        if question_type == "saq":
            if difficulty == "easy":
                return {
                    **base_question,
                    "question_text": "What is the capital of France?",
                    "ideal_answer": "Paris"
                }
            elif difficulty == "medium":
                return {
                    **base_question,
                    "question_text": "Explain the process of photosynthesis.",
                    "ideal_answer": "Photosynthesis is the process where plants convert sunlight, water, and carbon dioxide into glucose and oxygen using chlorophyll."
                }
            else:  # hard
                return {
                    **base_question,
                    "question_text": "Analyze the economic implications of renewable energy adoption on traditional energy sectors.",
                    "ideal_answer": "Renewable energy adoption creates economic disruption in traditional sectors through job displacement, stranded assets, and market restructuring, while generating new opportunities in green technology, manufacturing, and services. The transition requires careful policy management to ensure equitable distribution of costs and benefits."
                }
        else:  # mcq
            return {
                **base_question,
                "question_text": "What is the largest planet in our solar system?",
                "mcq_options": [
                    {"option_id": 1, "text": "Earth", "is_correct": False},
                    {"option_id": 2, "text": "Jupiter", "is_correct": True},
                    {"option_id": 3, "text": "Saturn", "is_correct": False},
                    {"option_id": 4, "text": "Mars", "is_correct": False}
                ]
            }
    
    @staticmethod
    def create_student_answers(answer_type: str = "varied") -> List[str]:
        """Create various student answer examples"""
        if answer_type == "correct":
            return [
                "Paris is the capital of France.",
                "The capital city of France is Paris.",
                "Paris"
            ]
        elif answer_type == "partially_correct":
            return [
                "It's in France",
                "A big city in France",
                "The main city of France",
                "French capital"
            ]
        elif answer_type == "incorrect":
            return [
                "London",
                "Rome", 
                "Madrid",
                "Berlin"
            ]
        else:  # varied
            return [
                "Paris",  # Correct
                "It's Paris, the capital city",  # Correct with extra info
                "A big city in France",  # Partial
                "The main French city",  # Partial
                "London",  # Incorrect
                "I don't know"  # Incorrect
            ]
    
    @staticmethod
    def create_test_session(session_id: str = None) -> Dict:
        """Create test session data"""
        if not session_id:
            session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "session_id": session_id,
            "user_id": "test_user_123",
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }


class TestValidators:
    """Validation utilities for test assertions"""
    
    @staticmethod
    def validate_semantic_evaluation_result(result, expected_range: tuple = None) -> bool:
        """Validate SemanticEvaluationResult structure and values"""
        required_fields = ["correctness", "feedback_category", "reasoning"]
        
        for field in required_fields:
            if not hasattr(result, field):
                return False
        
        # Validate correctness range
        if not (0.0 <= result.correctness <= 1.0):
            return False
        
        # Validate feedback category
        valid_categories = ["correct", "partially_correct", "incorrect"]
        if result.feedback_category not in valid_categories:
            return False
        
        # Validate expected range if provided
        if expected_range:
            if not (expected_range[0] <= result.correctness <= expected_range[1]):
                return False
        
        return True
    
    @staticmethod
    def validate_dynamic_feedback(feedback) -> bool:
        """Validate DynamicFeedback structure"""
        required_fields = ["evaluation", "explanation_or_hint", "correct_answer", "requires_retry"]
        
        for field in required_fields:
            if not hasattr(feedback, field):
                return False
        
        # Validate evaluation value
        valid_evaluations = ["correct", "partially_correct", "incorrect"]
        if feedback.evaluation not in valid_evaluations:
            return False
        
        # Validate requires_retry logic
        if feedback.evaluation == "correct" and feedback.requires_retry:
            return False  # Correct answers shouldn't require retry
        
        return True
    
    @staticmethod
    def validate_api_response(response_data: Dict, expected_fields: List[str]) -> bool:
        """Validate API response structure"""
        for field in expected_fields:
            if field not in response_data:
                return False
        
        return True


class PerformanceTracker:
    """Track performance metrics during tests"""
    
    def __init__(self, logger: TestLogger):
        self.logger = logger
        self.start_times = {}
    
    def start_timing(self, operation: str):
        """Start timing an operation"""
        self.start_times[operation] = datetime.now()
    
    def end_timing(self, operation: str, details: Optional[Dict] = None):
        """End timing and log performance"""
        if operation in self.start_times:
            duration = datetime.now() - self.start_times[operation]
            duration_ms = duration.total_seconds() * 1000
            
            self.logger.log_performance(operation, duration_ms, details)
            del self.start_times[operation]
            
            return duration_ms
        
        return None


class MockDataGenerator:
    """Generate mock data for testing LLM responses"""
    
    @staticmethod
    def mock_llm_semantic_evaluation(student_answer: str, ideal_answer: str) -> Dict:
        """Generate realistic mock semantic evaluation responses"""
        # Simple heuristic for testing - in real scenario this would be more sophisticated
        student_lower = student_answer.lower()
        ideal_lower = ideal_answer.lower()
        
        # Calculate simple word overlap
        student_words = set(student_lower.split())
        ideal_words = set(ideal_lower.split())
        
        overlap = len(student_words.intersection(ideal_words))
        total_ideal = len(ideal_words)
        
        if total_ideal == 0:
            correctness = 0.0
        else:
            correctness = min(overlap / total_ideal, 1.0)
        
        # Determine category
        if correctness >= 0.9:
            category = "correct"
        elif correctness >= 0.5:
            category = "partially_correct"
        else:
            category = "incorrect"
        
        return {
            "correctness": correctness,
            "feedback_category": category,
            "reasoning": f"Word overlap analysis: {overlap}/{total_ideal} key terms matched"
        }
    
    @staticmethod
    def mock_llm_hint_generation(correctness: float, student_answer: str) -> str:
        """Generate mock hints based on correctness score"""
        if correctness >= 0.7:
            return "You're very close! Just add a bit more detail to complete your answer."
        elif correctness >= 0.5:
            return "You have the right idea! Can you expand on the key concepts?"
        elif correctness >= 0.3:
            return "You're on the right track. Think about the main components of this topic."
        else:
            return "Let's approach this differently. Consider reviewing the key concepts first."


class TestResultsAnalyzer:
    """Analyze test results and generate reports"""
    
    def __init__(self, logger: TestLogger):
        self.logger = logger
        self.results = []
    
    def add_result(self, test_name: str, status: str, duration: float, details: Optional[Dict] = None):
        """Add a test result"""
        result = {
            "test_name": test_name,
            "status": status,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.results.append(result)
        self.logger.log("RESULT", f"Test {test_name}: {status} ({duration:.2f}s)", details)
    
    def generate_summary(self) -> Dict:
        """Generate test results summary"""
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASSED")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        
        summary = {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / total_tests * 100) if total_tests > 0 else 0,
            "total_duration": sum(r["duration"] for r in self.results),
            "results": self.results
        }
        
        return summary
    
    def save_report(self, filename: str = None):
        """Save test report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.json"
        
        reports_dir = Path("tests/reports")
        reports_dir.mkdir(exist_ok=True)
        
        report_path = reports_dir / filename
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.generate_summary(), f, indent=2, ensure_ascii=False)
        
        self.logger.log("REPORT", f"Test report saved: {report_path}")


def setup_test_environment():
    """Set up test environment and directories"""
    test_dirs = ["tests/logs", "tests/reports", "tests/data"]
    
    for dir_path in test_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✅ Test environment set up successfully")


def create_test_question(question_id: str = "test_q1", question_text: str = "What is AI?", correct_answer: str = "Artificial Intelligence"):
    """Create a test question object"""
    return {
        "id": question_id,
        "question": question_text,
        "correct_answer": correct_answer,
        "type": "text",
        "difficulty": "medium",
        "created_at": datetime.now().isoformat()
    }


def create_test_session(session_id: str = "test_session_001", user_id: str = "test_user"):
    """Create a test session object"""
    return {
        "session_id": session_id,
        "user_id": user_id,
        "started_at": datetime.now().isoformat(),
        "current_question": 0,
        "score": 0,
        "answers": []
    }


# Export main classes for easy import
__all__ = [
    'TestLogger',
    'TestDataFactory', 
    'TestValidators',
    'PerformanceTracker',
    'MockDataGenerator',
    'TestResultsAnalyzer',
    'setup_test_environment',
    'create_test_question',
    'create_test_session'
]
