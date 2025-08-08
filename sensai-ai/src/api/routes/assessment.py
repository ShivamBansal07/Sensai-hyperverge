import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models import QuestionBank
from ..models import Question, QuestionBank, SAQEvaluationRequest
from ..services.pdf_processor import process_pdf
from ..services.saq_evaluator import SAQEvaluatorService
from ..utils.logging import logger
from pydantic import BaseModel
from typing import Optional
from ..models import IntegrityLog

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_PAGES = 50

# In-memory storage for integrity logs (session-specific)
integrity_logs = []

# In-memory storage for retry attempts tracking
retry_attempts = {}  # {session_id: {question_id: attempt_count}}

@router.post("/clear-session/{session_id}")
async def clear_session_logs(session_id: str):
    """Clear all integrity logs for a specific session"""
    global integrity_logs
    initial_count = len(integrity_logs)
    integrity_logs = [log for log in integrity_logs if log["session_id"] != session_id]
    cleared_count = initial_count - len(integrity_logs)
    logger.info(f"Cleared {cleared_count} integrity logs for session {session_id}")
    return {"message": f"Cleared {cleared_count} logs for session {session_id}"}

@router.post("/generate-questions", response_model=QuestionBank)
async def generate_questions_from_pdf(
    file: UploadFile = File(...),
):
    """
    Receives a PDF file, processes it, and generates a list of questions.
    """
    logger.info(f"Received file: {file.filename}")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDFs are allowed.")

    # Read the file content asynchronously to avoid blocking
    pdf_content = await file.read()

    if len(pdf_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds the limit of {MAX_FILE_SIZE / 1024 / 1024} MB.")

    # The core logic will be delegated to a service
    question_bank = await process_pdf(pdf_content, MAX_PAGES)
    return question_bank


class QuizAnswer(BaseModel):
    question_id: str
    answer: str
    question_bank: QuestionBank
    current_score: int = 0
    total_questions_answered: int = 0
    session_id: Optional[str] = None  # Added for SAQ evaluation tracking
    retry_attempt: int = 0  # Track which attempt this is

class QuizFeedback(BaseModel):
    is_correct: bool
    correct_answer: Optional[str] = None
    next_question: Optional[Question] = None
    final_score: Optional[str] = None
    new_score: Optional[int] = None
    new_total_questions_answered: Optional[int] = None
    
    # NEW FIELDS for enhanced SAQ evaluation
    feedback_type: Optional[str] = None  # "correct", "partially_correct", "incorrect"
    hint: Optional[str] = None  # For partially correct answers
    explanation: Optional[str] = None  # Detailed feedback text
    requires_retry: bool = False  # Whether user should try again

@router.post("/integrity-log")
async def receive_integrity_log(log: IntegrityLog):
    logger.info(f"Received integrity log: {log.event_type} for session {log.session_id}")
    integrity_logs.append(log.dict())
    return {"message": "Log received"}

@router.get("/integrity-logs/{session_id}")
async def get_integrity_logs(session_id: str):
    session_logs = [log for log in integrity_logs if log["session_id"] == session_id]
    return session_logs

@router.post("/quiz/answer", response_model=QuizFeedback)
async def answer_quiz_question(quiz_answer: QuizAnswer):
    logger.info(f"QUIZ ANSWER RECEIVED: question_id={quiz_answer.question_id}, answer='{quiz_answer.answer}', session_id={quiz_answer.session_id}")
    
    question_bank = quiz_answer.question_bank
    current_question = next((q for q in question_bank.questions if q.question_id == quiz_answer.question_id), None)
    logger.info(f"FOUND QUESTION: {current_question.question_type if current_question else 'None'} - {current_question.question_text[:50] if current_question else 'Question not found'}...")

    if not current_question:
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct = False
    correct_answer = None
    new_score = quiz_answer.current_score
    new_total_questions_answered = quiz_answer.total_questions_answered + 1
    feedback_type = None
    hint = None
    explanation = None
    requires_retry = False

    if current_question.question_type == 'mcq':
        # Enhanced MCQ logic with explanations
        correct_option = next((opt for opt in current_question.mcq_options if opt.is_correct), None)
        if correct_option:
            correct_answer = correct_option.text
            if quiz_answer.answer == correct_option.text:
                is_correct = True
                new_score += 1
                feedback_type = "correct"
                explanation = "Excellent! You selected the correct answer."
            else:
                feedback_type = "incorrect"
                # Generate AI-powered explanation for incorrect MCQ answers
                chosen_option = next((opt for opt in current_question.mcq_options if opt.text == quiz_answer.answer), None)
                if chosen_option:
                    try:
                        # Use LLM client directly for MCQ explanation generation
                        logger.info(f"MCQ EXPLANATION: Generating AI explanation for incorrect MCQ answer...")
                        logger.info(f"MCQ EXPLANATION: Question='{current_question.question_text[:50]}...', Chosen='{chosen_option.text}', Correct='{correct_answer}'")
                        
                        from ..llm import get_llm_client
                        
                        # Create a simple response model for explanations
                        class MCQExplanation(BaseModel):
                            explanation: str
                        
                        client = get_llm_client()  # This is not async
                        
                        # Create a focused prompt for MCQ explanation
                        prompt = f"""You are an educational AI tutor. A student answered a multiple choice question incorrectly.

Question: {current_question.question_text}
Student's answer: {chosen_option.text}
Correct answer: {correct_answer}

Generate a brief, encouraging explanation (2-3 sentences) that:
1. Explains why the correct answer is right
2. Helps the student understand their mistake
3. Is educational and supportive

Be concise, clear, and encouraging."""

                        result = await client.chat.completions.create(
                            model="openai/gpt-4o-mini",
                            response_model=MCQExplanation,
                            messages=[
                                {"role": "system", "content": "You are a helpful educational tutor that explains why answers are correct or incorrect in a supportive way."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.7
                        )
                        
                        ai_explanation = result.explanation.strip()
                        logger.info(f"MCQ EXPLANATION: Generated AI explanation: {ai_explanation[:100]}...")
                        
                        explanation = f"That's not correct. You chose '{chosen_option.text}', but the correct answer is '{correct_answer}'.\n\n{ai_explanation}"
                        
                    except Exception as e:
                        logger.error(f"MCQ EXPLANATION: Error generating AI explanation: {e}")
                        # Fallback to simple explanation
                        explanation = f"That's not correct. You chose '{chosen_option.text}', but the correct answer is '{correct_answer}'.\n\nThe correct answer addresses the key concept in the question more accurately."
                else:
                    explanation = f"Incorrect. The correct answer is: {correct_answer}"
    
    elif current_question.question_type == 'saq':
        logger.info(f"SAQ EVALUATION START: question_id={quiz_answer.question_id}, answer='{quiz_answer.answer}', session_id={quiz_answer.session_id}")
        
        # First try enhanced SAQ evaluation, fall back to improved word matching if it fails
        correct_answer = current_question.ideal_answer or "No ideal answer provided"
        
        try:
            # Initialize SAQ evaluator service
            logger.info(f"SAQ EVALUATOR: Initializing SAQEvaluatorService...")
            evaluator = SAQEvaluatorService()
            
            # Create evaluation request
            evaluation_request = SAQEvaluationRequest(
                question_text=current_question.question_text,
                ideal_answer=current_question.ideal_answer or "No ideal answer provided",
                student_answer=quiz_answer.answer,
                question_id=quiz_answer.question_id,
                session_id=quiz_answer.session_id or f"fallback-{quiz_answer.question_id}"
            )
            
            logger.info(f"SAQ EVALUATOR: About to call evaluate_saq_complete...")
            # Perform enhanced SAQ evaluation
            feedback = await evaluator.evaluate_saq_complete(evaluation_request)
            
            logger.info(f"SAQ EVALUATION COMPLETE: evaluation={feedback.evaluation}, explanation={feedback.explanation_or_hint}")
            
            # Map evaluation results to response
            feedback_type = feedback.evaluation
            explanation = feedback.explanation_or_hint
            correct_answer = feedback.correct_answer
            # Use the retry setting from SAQ evaluator (re-enabled)
            requires_retry = feedback.requires_retry
            hint = None

            # Check retry attempts for this question (add session tracking)
            if not quiz_answer.session_id:
                logger.warning("No session_id provided for SAQ evaluation, using fallback")
                session_id = f"fallback-{quiz_answer.question_id}"
            else:
                session_id = quiz_answer.session_id

            # Initialize retry attempts tracking
            if session_id not in retry_attempts:
                retry_attempts[session_id] = {}
            if quiz_answer.question_id not in retry_attempts[session_id]:
                retry_attempts[session_id][quiz_answer.question_id] = 0

            current_attempts = retry_attempts[session_id][quiz_answer.question_id]
            logger.info(f"SAQ RETRY CHECK: current_attempts={current_attempts} for question {quiz_answer.question_id}")

            # Handle retry logic based on evaluation and attempts
            if feedback.evaluation == "correct":
                is_correct = True
                new_score += 1
                # Reset retry count for this question
                retry_attempts[session_id][quiz_answer.question_id] = 0
                requires_retry = False

            elif feedback.evaluation == "partially_correct" and requires_retry and current_attempts == 0:
                # Only allow retry on FIRST attempt for partially correct answers
                is_correct = False
                requires_retry = True
                hint = explanation  # Use explanation as hint for frontend
                # Increment retry attempt
                retry_attempts[session_id][quiz_answer.question_id] = 1
                logger.info(f"SAQ RETRY ALLOWED: question={quiz_answer.question_id}, answer='{quiz_answer.answer}', attempts=1")

            else:
                # Either incorrect OR this is a second attempt (no more retries)
                is_correct = False
                requires_retry = False
                if current_attempts > 0:
                    # This was a retry attempt
                    logger.info(f"SAQ NO MORE RETRIES: question={quiz_answer.question_id}, answer='{quiz_answer.answer}', attempts={current_attempts}")
                else:
                    # First attempt but incorrect (low score)
                    logger.info(f"SAQ INCORRECT FIRST TRY: question={quiz_answer.question_id}, answer='{quiz_answer.answer}')")
                
        except Exception as e:
            logger.error(f"Error in enhanced SAQ evaluation, using improved fallback: {e}")
            # IMPROVED FALLBACK: Word matching percentage evaluation
            student_words = set(quiz_answer.answer.lower().strip().split())
            ideal_words = set(correct_answer.lower().strip().split())
            
            # Remove common stop words for better matching
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
            student_words_filtered = student_words - stop_words
            ideal_words_filtered = ideal_words - stop_words
            
            if len(ideal_words_filtered) == 0:
                # If no meaningful words in ideal answer, fall back to simple matching
                match_percentage = 1.0 if quiz_answer.answer.lower().strip() in correct_answer.lower() else 0.0
            else:
                # Calculate percentage of ideal words found in student answer
                matching_words = student_words_filtered.intersection(ideal_words_filtered)
                match_percentage = len(matching_words) / len(ideal_words_filtered)
            
            logger.info(f"SAQ FALLBACK WORD MATCHING: {match_percentage:.2f} ({len(matching_words) if 'matching_words' in locals() else 0}/{len(ideal_words_filtered) if 'ideal_words_filtered' in locals() else 0} words)")
            
            if match_percentage >= 0.85:
                # Very high match - consider correct
                is_correct = True
                new_score += 1
                feedback_type = "correct"
                explanation = "Excellent! Your answer contains all the key concepts."
            elif match_percentage >= 0.50:
                # 50-84% match - partially correct (no retry for now, just informational)
                is_correct = False
                feedback_type = "partially_correct" 
                explanation = f"Good start! You have some key concepts right. The complete answer is: {correct_answer}"
            else:
                # Less than 50% match - incorrect
                is_correct = False
                feedback_type = "incorrect"
                explanation = f"Not quite right. The expected answer was: {correct_answer}"
        
        # SAQ retry logic is now controlled by the SAQ evaluator
        # hint = None  # Hints are now handled via explanation field
        
        logger.info(f"SAQ FINAL RESULT: is_correct={is_correct}, feedback_type={feedback_type}, requires_retry={requires_retry}")
        
        # # COMMENTED OUT: Enhanced SAQ evaluation with retry logic
        # if not quiz_answer.session_id:
        #     logger.warning("No session_id provided for SAQ evaluation, using fallback")
        #     session_id = f"fallback-{quiz_answer.question_id}"
        # else:
        #     session_id = quiz_answer.session_id
            
        # # Check retry attempts for this question
        # if session_id not in retry_attempts:
        #     retry_attempts[session_id] = {}
        # if quiz_answer.question_id not in retry_attempts[session_id]:
        #     retry_attempts[session_id][quiz_answer.question_id] = 0
            
        # current_attempts = retry_attempts[session_id][quiz_answer.question_id]
        # logger.info(f"SAQ RETRY CHECK: current_attempts={current_attempts} for question {quiz_answer.question_id}")
        
        # try:
        #     # Initialize SAQ evaluator service
        #     logger.info(f"SAQ EVALUATOR: Initializing SAQEvaluatorService...")
        #     evaluator = SAQEvaluatorService()
            
        #     # Create evaluation request
        #     evaluation_request = SAQEvaluationRequest(
        #         question_text=current_question.question_text,
        #         ideal_answer=current_question.ideal_answer or "No ideal answer provided",
        #         student_answer=quiz_answer.answer,
        #         question_id=quiz_answer.question_id,
        #         session_id=session_id
        #     )
            
        #     logger.info(f"SAQ EVALUATOR: About to call evaluate_saq_complete...")
        #     # Perform enhanced SAQ evaluation
        #     feedback = await evaluator.evaluate_saq_complete(evaluation_request)
            
        #     logger.info(f"SAQ EVALUATION COMPLETE: evaluation={feedback.evaluation}, explanation={feedback.explanation_or_hint}")
            
        #     # Map evaluation results to response
        #     feedback_type = feedback.evaluation
        #     explanation = feedback.explanation_or_hint
        #     correct_answer = feedback.correct_answer
        #     requires_retry = feedback.requires_retry
            
        #     # Determine if answer is "correct enough" to proceed and award points
        #     if feedback.evaluation == "correct":
        #         is_correct = True
        #         new_score += 1
        #         # Reset retry count for this question
        #         retry_attempts[session_id][quiz_answer.question_id] = 0
                
        #     elif feedback.evaluation == "partially_correct" and current_attempts == 0:
        #         # Only allow retry on FIRST attempt and if truly partially correct (score >= 0.6)
        #         hint = feedback.explanation_or_hint
        #         is_correct = False
        #         requires_retry = True
        #         # Increment retry attempt
        #         retry_attempts[session_id][quiz_answer.question_id] = 1
        #         logger.info(f"SAQ RETRY ALLOWED: question={quiz_answer.question_id}, answer='{quiz_answer.answer}', score={feedback}, attempt=1")
                
        #     else:
        #         # Either incorrect OR this is a second attempt (no more retries)
        #         is_correct = False
        #         requires_retry = False
        #         if current_attempts > 0:
        #             explanation = f"After 1 retry attempt: {feedback.explanation_or_hint}"
        #             logger.info(f"SAQ NO MORE RETRIES: question={quiz_answer.question_id}, answer='{quiz_answer.answer}', attempts={current_attempts}")
        #         else:
        #             explanation = feedback.explanation_or_hint
        #             logger.info(f"SAQ INCORRECT FIRST TRY: question={quiz_answer.question_id}, answer='{quiz_answer.answer}', score=low")
                
        # except Exception as e:
        #     logger.error(f"Error in enhanced SAQ evaluation: {e}")
        #     # Fallback to simple string matching
        #     correct_answer = current_question.ideal_answer
        #     if correct_answer and quiz_answer.answer.lower() in correct_answer.lower():
        #         is_correct = True
        #         new_score += 1
        #         feedback_type = "correct"
        #     else:
        #         feedback_type = "incorrect"
        #     explanation = "Using fallback evaluation due to error"

    # Simple progression logic - always move to next question
    current_index = -1
    for i, q in enumerate(question_bank.questions):
        if q.question_id == current_question.question_id:
            current_index = i
            break

    next_question = None
    # Always advance to next question (no retry logic)
    if current_index != -1 and current_index + 1 < len(question_bank.questions):
        next_question = question_bank.questions[current_index + 1]

    final_score = None
    if not next_question:
        final_score = f"Quiz Complete! Your score: {new_score}/{new_total_questions_answered}"

    return QuizFeedback(
        is_correct=is_correct,
        correct_answer=correct_answer,
        next_question=next_question,
        final_score=final_score,
        new_score=new_score,
        new_total_questions_answered=new_total_questions_answered,
        feedback_type=feedback_type,
        hint=hint,
        explanation=explanation,
        requires_retry=requires_retry,
    )
