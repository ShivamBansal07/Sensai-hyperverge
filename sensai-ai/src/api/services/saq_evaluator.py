import instructor
from openai import OpenAI
from typing import Optional
from ..models import SemanticEvaluationResult, DynamicFeedback, SAQEvaluationRequest
from ..llm import get_llm_client
from ..utils.logging import logger


class SAQEvaluatorService:
    """
    Service for evaluating Short Answer Questions using multi-step LLM evaluation.
    Implements semantic analysis followed by dynamic feedback generation.
    """
    
    def __init__(self):
        self.client = get_llm_client()
    
    async def semantic_evaluation(self, question: str, ideal_answer: str, student_answer: str) -> SemanticEvaluationResult:
        """
        Step 1: Semantic evaluation with structured output using Instructor.
        
        Args:
            question: The original question text
            ideal_answer: The reference correct answer
            student_answer: The student's submitted answer
            
        Returns:
            SemanticEvaluationResult with correctness score and feedback category
        """
        try:
            # Create Instructor client for structured output
            instructor_client = instructor.from_openai(self.client)
            
            # Semantic evaluation prompt
            prompt = f"""
You are an expert AI grading assistant with deep understanding of semantic similarity.

TASK: Evaluate how semantically close a student's answer is to the ideal answer.

QUESTION: {question}
IDEAL CORRECT ANSWER: {ideal_answer}
STUDENT'S ANSWER: {student_answer}

EVALUATION CRITERIA:
- 1.0: Perfect match or complete semantic equivalence
- 0.9-0.99: Correct with minor wording differences
- 0.7-0.89: Mostly correct, missing minor details
- 0.5-0.69: Partially correct, has key concepts but incomplete
- 0.3-0.49: Has some relevant content but significant gaps
- 0.0-0.29: Incorrect or completely off-topic

Respond with a structured evaluation focusing on semantic meaning, not exact wording.
Provide your reasoning for the score in the reasoning field.
"""

            result = await instructor_client.chat.completions.create(
                model="gpt-4o-mini",
                response_model=SemanticEvaluationResult,
                messages=[
                    {"role": "system", "content": "You are an expert grading assistant that evaluates semantic similarity between student answers and ideal answers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1  # Low temperature for consistent grading
            )
            
            logger.info(f"Semantic evaluation completed: {result.correctness:.2f} ({result.feedback_category})")
            return result
            
        except Exception as e:
            logger.error(f"Error in semantic evaluation: {e}")
            # Fallback to basic evaluation
            return SemanticEvaluationResult(
                correctness=0.5,
                feedback_category="partially_correct",
                reasoning=f"Error in evaluation: {str(e)}"
            )
    
    async def generate_dynamic_feedback(self, 
                                      evaluation_result: SemanticEvaluationResult, 
                                      question: str, 
                                      ideal_answer: str, 
                                      student_answer: str) -> DynamicFeedback:
        """
        Step 2: Generate contextual feedback based on evaluation result.
        
        Args:
            evaluation_result: Result from semantic evaluation
            question: The original question text
            ideal_answer: The reference correct answer
            student_answer: The student's submitted answer
            
        Returns:
            DynamicFeedback with appropriate explanation or hint
        """
        try:
            if evaluation_result.correctness >= 0.9:
                # Student is correct - simple confirmation
                explanation = self._generate_correct_feedback()
                requires_retry = False
                
            elif evaluation_result.correctness >= 0.5:
                # Partially correct - generate encouraging hint
                explanation = await self._generate_hint(question, ideal_answer, student_answer, evaluation_result.correctness)
                requires_retry = True
                
            else:
                # Incorrect - provide correct answer and brief explanation
                explanation = await self._generate_incorrect_feedback(question, ideal_answer, student_answer)
                requires_retry = False
            
            return DynamicFeedback(
                evaluation=evaluation_result.feedback_category,
                explanation_or_hint=explanation,
                correct_answer=ideal_answer,
                requires_retry=requires_retry
            )
            
        except Exception as e:
            logger.error(f"Error generating dynamic feedback: {e}")
            # Fallback feedback
            return DynamicFeedback(
                evaluation=evaluation_result.feedback_category,
                explanation_or_hint="I encountered an error generating feedback. Please try again.",
                correct_answer=ideal_answer,
                requires_retry=False
            )
    
    async def evaluate_saq_complete(self, request: SAQEvaluationRequest) -> DynamicFeedback:
        """
        Complete SAQ evaluation pipeline combining both steps.
        
        Args:
            request: SAQEvaluationRequest with all necessary data
            
        Returns:
            DynamicFeedback with complete evaluation and feedback
        """
        logger.info(f"Starting SAQ evaluation for question {request.question_id}")
        
        # Step 1: Semantic evaluation
        evaluation_result = await self.semantic_evaluation(
            request.question_text,
            request.ideal_answer,
            request.student_answer
        )
        
        # Step 2: Generate dynamic feedback
        feedback = await self.generate_dynamic_feedback(
            evaluation_result,
            request.question_text,
            request.ideal_answer,
            request.student_answer
        )
        
        logger.info(f"SAQ evaluation completed: {feedback.evaluation} (retry: {feedback.requires_retry})")
        return feedback
    
    def _generate_correct_feedback(self) -> str:
        """Generate a simple confirmation message for correct answers."""
        correct_responses = [
            "Excellent! You've got it exactly right.",
            "Perfect answer! You clearly understand the concept.",
            "Spot on! That's exactly what I was looking for.",
            "Outstanding! Your answer demonstrates complete understanding.",
            "Exactly right! Well done."
        ]
        import random
        return random.choice(correct_responses)
    
    async def _generate_hint(self, question: str, ideal_answer: str, student_answer: str, correctness: float) -> str:
        """Generate an encouraging hint for partially correct answers."""
        try:
            hint_prompt = f"""
You are a motivating Socratic tutor. The student is on the right track but needs guidance.

CONTEXT:
Question: {question}
Student's Answer: {student_answer}
Ideal Answer: {ideal_answer}
Correctness Score: {correctness:.2f}

Your student is close but needs a gentle push. Generate a SHORT, encouraging hint (max 2 sentences) that:
1. Acknowledges what they got right
2. Guides them toward the missing piece
3. Uses encouraging language
4. Doesn't give away the full answer

Example: "You're definitely on the right track with X! What about the aspect related to Y that we discussed earlier?"
"""

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a motivating tutor who gives encouraging hints to students who are partially correct."},
                    {"role": "user", "content": hint_prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating hint: {e}")
            return f"You're on the right track! Think about what else might be important to include in your answer."
    
    async def _generate_incorrect_feedback(self, question: str, ideal_answer: str, student_answer: str) -> str:
        """Generate feedback for incorrect answers."""
        try:
            feedback_prompt = f"""
Generate a brief, constructive explanation for why the student's answer is incorrect.

Question: {question}
Student's Answer: {student_answer}
Correct Answer: {ideal_answer}

Provide a short explanation (1-2 sentences) that:
1. Briefly explains why the answer is incorrect
2. Points toward the correct answer
3. Is encouraging and educational

Keep it concise and helpful.
"""

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful tutor providing constructive feedback on incorrect answers."},
                    {"role": "user", "content": feedback_prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            explanation = response.choices[0].message.content.strip()
            return f"{explanation}\n\nThe correct answer is: {ideal_answer}"
            
        except Exception as e:
            logger.error(f"Error generating incorrect feedback: {e}")
            return f"Not quite right. The correct answer is: {ideal_answer}. Please review the material and try again."
