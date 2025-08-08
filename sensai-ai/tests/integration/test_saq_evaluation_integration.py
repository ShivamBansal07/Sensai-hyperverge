"""
🧪 SAQ EVALUATION INTEGimport sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api.models import (
    SemanticEvaluationResult, 
    DynamicFeedback, 
    SAQEvaluationRequest,
    Question,
    QuestionBank
)
from api.routes.assessment import QuizAnswer, QuizFeedback
from api.services.saq_evaluator import SAQEvaluatorService
from api.main import appSTS
==================================

Comprehensive test suite for enhanced SAQ evaluation system.
Tests run after each checkpoint to verify functionality.

Test Categories:
1. Model Validation Tests
2. Service Layer Tests  
3. API Endpoint Tests
4. Integration Flow Tests
5. Error Handling Tests
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Import our application modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api.models import (
    SemanticEvaluationResult, 
    DynamicFeedback, 
    SAQEvaluationRequest,
    Question,
    QuestionType
)
from api.services.saq_evaluator import SAQEvaluatorService
from api.main import app

# Import our test utilities
from ..utils.test_utils import create_test_question, create_test_session, TestLogger

# Initialize test client
client = TestClient(app)

# Initialize test logger
test_logger = TestLogger("saq_evaluation_tests")

class TestSAQModels:
    """🔧 Test Phase 1.1: Pydantic Model Validation"""
    
    def test_semantic_evaluation_result_valid(self):
        """Test SemanticEvaluationResult model with valid data"""
        test_logger.log("TEST", "Testing SemanticEvaluationResult model validation")
        
        valid_data = {
            "correctness": 0.85,
            "feedback_category": "partially_correct",
            "reasoning": "Student has main concept but missing details"
        }
        
        result = SemanticEvaluationResult(**valid_data)
        
        assert result.correctness == 0.85
        assert result.feedback_category == "partially_correct"
        assert result.reasoning == "Student has main concept but missing details"
        
        test_logger.log("SUCCESS", "✅ SemanticEvaluationResult model validation passed")
    
    def test_semantic_evaluation_result_invalid_correctness(self):
        """Test SemanticEvaluationResult with invalid correctness score"""
        test_logger.log("TEST", "Testing SemanticEvaluationResult with invalid correctness score")
        
        with pytest.raises(ValueError):
            SemanticEvaluationResult(
                correctness=1.5,  # Invalid: > 1.0
                feedback_category="correct"
            )
        
        test_logger.log("SUCCESS", "✅ Invalid correctness score properly rejected")
    
    def test_dynamic_feedback_model(self):
        """Test DynamicFeedback model"""
        test_logger.log("TEST", "Testing DynamicFeedback model")
        
        feedback_data = {
            "evaluation": "partially_correct",
            "explanation_or_hint": "You're on the right track! Consider the environmental impact.",
            "correct_answer": "Renewable energy reduces carbon footprint and environmental pollution",
            "requires_retry": True
        }
        
        feedback = DynamicFeedback(**feedback_data)
        
        assert feedback.evaluation == "partially_correct"
        assert feedback.requires_retry == True
        assert "environmental impact" in feedback.explanation_or_hint
        
        test_logger.log("SUCCESS", "✅ DynamicFeedback model validation passed")
    
    def test_saq_evaluation_request_model(self):
        """Test SAQEvaluationRequest model"""
        test_logger.log("TEST", "Testing SAQEvaluationRequest model")
        
        request_data = {
            "question_text": "What are the benefits of renewable energy?",
            "ideal_answer": "Renewable energy reduces carbon footprint and environmental pollution",
            "student_answer": "It's good for environment",
            "question_id": "q_001",
            "session_id": "session_test_123"
        }
        
        request = SAQEvaluationRequest(**request_data)
        
        assert request.question_text == "What are the benefits of renewable energy?"
        assert request.session_id == "session_test_123"
        
        test_logger.log("SUCCESS", "✅ SAQEvaluationRequest model validation passed")


class TestSAQEvaluatorService:
    """🔧 Test Phase 1.2: SAQ Evaluator Service"""
    
    @pytest.fixture
    def evaluator_service(self):
        """Create SAQEvaluatorService instance for testing"""
        return SAQEvaluatorService()
    
    @pytest.mark.asyncio
    async def test_semantic_evaluation_correct_answer(self, evaluator_service):
        """Test semantic evaluation with correct answer"""
        test_logger.log("TEST", "Testing semantic evaluation with correct answer")
        
        question = "What is the capital of France?"
        ideal_answer = "Paris"
        student_answer = "The capital of France is Paris"
        
        # Mock the LLM response
        with patch.object(evaluator_service.client, 'chat') as mock_chat:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test LLM response"
            mock_chat.completions.create.return_value = mock_response
            
            # Mock the instructor client
            with patch('api.services.saq_evaluator.instructor') as mock_instructor:
                mock_instructor_client = Mock()
                mock_instructor_client.chat.completions.create.return_value = SemanticEvaluationResult(
                    correctness=0.95,
                    feedback_category="correct",
                    reasoning="Perfect semantic match"
                )
                mock_instructor.from_openai.return_value = mock_instructor_client
            
            result = await evaluator_service.semantic_evaluation(
                question, ideal_answer, student_answer
            )
            
            assert result.correctness >= 0.9
            assert result.feedback_category == "correct"
            
            test_logger.log("SUCCESS", f"✅ Correct answer evaluation: {result.correctness}")
    
    @pytest.mark.asyncio
    async def test_semantic_evaluation_partial_answer(self, evaluator_service):
        """Test semantic evaluation with partially correct answer"""
        test_logger.log("TEST", "Testing semantic evaluation with partial answer")
        
        question = "Explain the benefits of renewable energy"
        ideal_answer = "Renewable energy reduces carbon emissions, is sustainable, and decreases dependency on fossil fuels"
        student_answer = "It's good for the environment"
        
        with patch.object(evaluator_service, '_call_semantic_evaluation_llm') as mock_llm:
            mock_llm.return_value = SemanticEvaluationResult(
                correctness=0.6,
                feedback_category="partially_correct",
                reasoning="Has environmental concept but lacks detail"
            )
            
            result = await evaluator_service.semantic_evaluation(
                question, ideal_answer, student_answer
            )
            
            assert 0.5 <= result.correctness < 0.9
            assert result.feedback_category == "partially_correct"
            
            test_logger.log("SUCCESS", f"✅ Partial answer evaluation: {result.correctness}")
    
    @pytest.mark.asyncio
    async def test_generate_dynamic_feedback(self, evaluator_service):
        """Test dynamic feedback generation"""
        test_logger.log("TEST", "Testing dynamic feedback generation")
        
        evaluation_result = SemanticEvaluationResult(
            correctness=0.6,
            feedback_category="partially_correct",
            reasoning="Student understands basic concept"
        )
        
        with patch.object(evaluator_service, '_call_hint_generation_llm') as mock_llm:
            mock_llm.return_value = "You're on the right track! What about sustainability aspects?"
            
            feedback = await evaluator_service.generate_dynamic_feedback(
                evaluation_result,
                "Explain renewable energy benefits",
                "Reduces emissions, sustainable, reduces fossil fuel dependency",
                "Good for environment"
            )
            
            assert feedback.evaluation == "partially_correct"
            assert feedback.requires_retry == True
            assert "right track" in feedback.explanation_or_hint
            
            test_logger.log("SUCCESS", "✅ Dynamic feedback generation passed")
    
    @pytest.mark.asyncio
    async def test_complete_evaluation_pipeline(self, evaluator_service):
        """Test complete SAQ evaluation pipeline"""
        test_logger.log("TEST", "Testing complete SAQ evaluation pipeline")
        
        request = SAQEvaluationRequest(
            question_text="What is photosynthesis?",
            ideal_answer="Process where plants convert sunlight, water, and CO2 into glucose and oxygen",
            student_answer="Plants make food from sunlight",
            question_id="q_photo_001",
            session_id="session_pipeline_test"
        )
        
        # Mock both LLM calls
        with patch.object(evaluator_service, 'semantic_evaluation') as mock_semantic:
            with patch.object(evaluator_service, 'generate_dynamic_feedback') as mock_feedback:
                
                mock_semantic.return_value = SemanticEvaluationResult(
                    correctness=0.7,
                    feedback_category="partially_correct"
                )
                
                mock_feedback.return_value = DynamicFeedback(
                    evaluation="partially_correct",
                    explanation_or_hint="Good start! What about the inputs and outputs?",
                    correct_answer="Process where plants convert sunlight, water, and CO2 into glucose and oxygen",
                    requires_retry=True
                )
                
                result = await evaluator_service.evaluate_saq_complete(request)
                
                assert result.evaluation == "partially_correct"
                assert result.requires_retry == True
                assert "Good start" in result.explanation_or_hint
                
                test_logger.log("SUCCESS", "✅ Complete evaluation pipeline passed")


class TestAPIEndpointEnhancement:
    """🔧 Test Phase 3: API Endpoint Enhancement"""
    
    def test_enhanced_quiz_answer_endpoint_saq_correct(self):
        """Test enhanced quiz/answer endpoint with correct SAQ"""
        test_logger.log("TEST", "Testing enhanced quiz/answer endpoint with correct SAQ")
        
        # Create test data
        quiz_data = {
            "question_id": "q_test_001",
            "answer": "Paris is the capital of France",
            "question_bank": {
                "questions": [{
                    "question_id": "q_test_001",
                    "page_number": 1,
                    "question_type": "saq",
                    "question_text": "What is the capital of France?",
                    "ideal_answer": "Paris"
                }]
            },
            "current_score": 0,
            "total_questions_answered": 0,
            "session_id": "test_session_correct"
        }
        
        # Mock the SAQ evaluator service
        with patch('src.api.routes.assessment.SAQEvaluatorService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.evaluate_saq_complete.return_value = DynamicFeedback(
                evaluation="correct",
                explanation_or_hint="Excellent! That's exactly right.",
                correct_answer="Paris",
                requires_retry=False
            )
            
            response = client.post("/assessment/quiz/answer", json=quiz_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["is_correct"] == True
            assert data["feedback_type"] == "correct"
            assert "Excellent" in data["correct_answer"]
            
            test_logger.log("SUCCESS", "✅ Correct SAQ endpoint test passed")
    
    def test_enhanced_quiz_answer_endpoint_saq_partial(self):
        """Test enhanced quiz/answer endpoint with partially correct SAQ"""
        test_logger.log("TEST", "Testing enhanced quiz/answer endpoint with partial SAQ")
        
        quiz_data = {
            "question_id": "q_test_002",
            "answer": "It's the big city in France",
            "question_bank": {
                "questions": [{
                    "question_id": "q_test_002",
                    "page_number": 1,
                    "question_type": "saq", 
                    "question_text": "What is the capital of France?",
                    "ideal_answer": "Paris"
                }]
            },
            "current_score": 0,
            "total_questions_answered": 0,
            "session_id": "test_session_partial"
        }
        
        with patch('src.api.routes.assessment.SAQEvaluatorService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.evaluate_saq_complete.return_value = DynamicFeedback(
                evaluation="partially_correct",
                explanation_or_hint="You're close! Which specific city is the capital?",
                correct_answer="Paris",
                requires_retry=True
            )
            
            response = client.post("/assessment/quiz/answer", json=quiz_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["is_correct"] == False  # Don't advance
            assert data["feedback_type"] == "partially_correct"
            assert data["requires_retry"] == True
            assert "close" in data["hint"]
            
            test_logger.log("SUCCESS", "✅ Partial SAQ endpoint test passed")
    
    def test_enhanced_quiz_answer_endpoint_error_handling(self):
        """Test error handling in enhanced endpoint"""
        test_logger.log("TEST", "Testing error handling in enhanced endpoint")
        
        quiz_data = {
            "question_id": "q_test_003",
            "answer": "Test answer",
            "question_bank": {
                "questions": [{
                    "question_id": "q_test_003",
                    "page_number": 1,
                    "question_type": "saq",
                    "question_text": "Test question?",
                    "ideal_answer": "Test ideal answer"
                }]
            },
            "current_score": 0,
            "total_questions_answered": 0,
            "session_id": "test_session_error"
        }
        
        # Mock service to raise an exception
        with patch('src.api.routes.assessment.SAQEvaluatorService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.evaluate_saq_complete.side_effect = Exception("LLM service error")
            
            response = client.post("/assessment/quiz/answer", json=quiz_data)
            
            assert response.status_code == 200
            data = response.json()
            
            # Should fall back to simple string matching
            assert "feedback_type" in data or "is_correct" in data
            
            test_logger.log("SUCCESS", "✅ Error handling test passed")


class TestIntegrationFlow:
    """🔧 Test Complete Integration Flow"""
    
    @pytest.mark.asyncio
    async def test_full_saq_evaluation_flow(self):
        """Test complete flow from request to response"""
        test_logger.log("TEST", "Testing complete SAQ evaluation flow")
        
        # This would test the full pipeline in a real scenario
        # We'll mock the external dependencies but test the flow
        
        test_data = {
            "question": "Explain the water cycle",
            "ideal_answer": "Water evaporates, forms clouds, precipitates as rain, and returns to bodies of water",
            "student_answers": [
                "Water goes up and comes down",  # Partial
                "Water evaporates, forms clouds, and rains back down",  # Better partial
                "Water evaporates from oceans, forms clouds through condensation, precipitates as rain, and flows back to water bodies"  # Correct
            ]
        }
        
        evaluator = SAQEvaluatorService()
        
        for i, student_answer in enumerate(test_data["student_answers"]):
            test_logger.log("TEST", f"Testing answer {i+1}: {student_answer}")
            
            # Mock the evaluation based on answer quality
            with patch.object(evaluator, 'semantic_evaluation') as mock_eval:
                with patch.object(evaluator, 'generate_dynamic_feedback') as mock_feedback:
                    
                    if i == 0:  # First answer - partial
                        mock_eval.return_value = SemanticEvaluationResult(
                            correctness=0.4, feedback_category="partially_correct"
                        )
                        mock_feedback.return_value = DynamicFeedback(
                            evaluation="partially_correct",
                            explanation_or_hint="You have the basic idea! What happens in the clouds?",
                            correct_answer=test_data["ideal_answer"],
                            requires_retry=True
                        )
                    elif i == 1:  # Second answer - better partial
                        mock_eval.return_value = SemanticEvaluationResult(
                            correctness=0.7, feedback_category="partially_correct"
                        )
                        mock_feedback.return_value = DynamicFeedback(
                            evaluation="partially_correct",
                            explanation_or_hint="Great improvement! Can you add what happens after the rain?",
                            correct_answer=test_data["ideal_answer"],
                            requires_retry=True
                        )
                    else:  # Third answer - correct
                        mock_eval.return_value = SemanticEvaluationResult(
                            correctness=0.95, feedback_category="correct"
                        )
                        mock_feedback.return_value = DynamicFeedback(
                            evaluation="correct",
                            explanation_or_hint="Excellent! You've described the complete water cycle.",
                            correct_answer=test_data["ideal_answer"],
                            requires_retry=False
                        )
                    
                    request = SAQEvaluationRequest(
                        question_text=test_data["question"],
                        ideal_answer=test_data["ideal_answer"],
                        student_answer=student_answer,
                        question_id=f"q_water_cycle_{i}",
                        session_id="integration_test_session"
                    )
                    
                    result = await evaluator.evaluate_saq_complete(request)
                    
                    test_logger.log("RESULT", f"Answer {i+1}: {result.evaluation} (retry: {result.requires_retry})")
                    
                    if i < 2:
                        assert result.requires_retry == True
                        assert result.evaluation == "partially_correct"
                    else:
                        assert result.requires_retry == False
                        assert result.evaluation == "correct"
        
        test_logger.log("SUCCESS", "✅ Full integration flow test passed")


# Test utilities and fixtures
@pytest.fixture
def test_session():
    """Create a test database session"""
    # This would create a test database session
    # Implementation depends on your database setup
    pass

@pytest.fixture  
def sample_quiz_data():
    """Sample quiz data for testing"""
    return {
        "questions": [
            {
                "question_id": "q_001",
                "question_type": "saq",
                "question_text": "What is photosynthesis?",
                "ideal_answer": "Process where plants convert sunlight into energy"
            },
            {
                "question_id": "q_002", 
                "question_type": "mcq",
                "question_text": "What is the capital of Japan?",
                "mcq_options": [
                    {"option_id": 1, "text": "Tokyo", "is_correct": True},
                    {"option_id": 2, "text": "Osaka", "is_correct": False}
                ]
            }
        ]
    }


if __name__ == "__main__":
    # Run tests manually
    test_logger.log("START", "Starting SAQ Evaluation Integration Tests")
    pytest.main([__file__, "-v", "--tb=short"])
    test_logger.log("END", "SAQ Evaluation Integration Tests Complete")
