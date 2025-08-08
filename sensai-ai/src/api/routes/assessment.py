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
    question_bank = quiz_answer.question_bank
    current_question = next((q for q in question_bank.questions if q.question_id == quiz_answer.question_id), None)

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
        # Existing MCQ logic remains unchanged
        correct_option = next((opt for opt in current_question.mcq_options if opt.is_correct), None)
        if correct_option:
            correct_answer = correct_option.text
            if quiz_answer.answer == correct_option.text:
                is_correct = True
                new_score += 1
                feedback_type = "correct"
            else:
                feedback_type = "incorrect"
    
    elif current_question.question_type == 'saq':
        # NEW: Enhanced SAQ evaluation using multi-step LLM process
        if not quiz_answer.session_id:
            logger.warning("No session_id provided for SAQ evaluation, using fallback")
            session_id = f"fallback-{quiz_answer.question_id}"
        else:
            session_id = quiz_answer.session_id
            
        try:
            # Initialize SAQ evaluator service
            evaluator = SAQEvaluatorService()
            
            # Create evaluation request
            evaluation_request = SAQEvaluationRequest(
                question_text=current_question.question_text,
                ideal_answer=current_question.ideal_answer or "No ideal answer provided",
                student_answer=quiz_answer.answer,
                question_id=quiz_answer.question_id,
                session_id=session_id
            )
            
            # Perform enhanced SAQ evaluation
            feedback = await evaluator.evaluate_saq_complete(evaluation_request)
            
            # Map evaluation results to response
            feedback_type = feedback.evaluation
            explanation = feedback.explanation_or_hint
            correct_answer = feedback.correct_answer
            requires_retry = feedback.requires_retry
            
            # Determine if answer is "correct enough" to proceed and award points
            if feedback.evaluation == "correct":
                is_correct = True
                new_score += 1
            elif feedback.evaluation == "partially_correct":
                # For partially correct, don't advance question but show hint
                hint = feedback.explanation_or_hint
                # Don't award points yet, but also don't mark as incorrect
                is_correct = False
                requires_retry = True
            else:  # incorrect
                is_correct = False
                
        except Exception as e:
            logger.error(f"Error in enhanced SAQ evaluation: {e}")
            # Fallback to simple string matching
            correct_answer = current_question.ideal_answer
            if correct_answer and quiz_answer.answer.lower() in correct_answer.lower():
                is_correct = True
                new_score += 1
                feedback_type = "correct"
            else:
                feedback_type = "incorrect"
            explanation = "Using fallback evaluation due to error"

    # Simple progression logic with unique question IDs
    current_index = -1
    for i, q in enumerate(question_bank.questions):
        if q.question_id == current_question.question_id:
            current_index = i
            break

    next_question = None
    # Only advance to next question if not requiring retry
    if not requires_retry and current_index != -1 and current_index + 1 < len(question_bank.questions):
        next_question = question_bank.questions[current_index + 1]
    elif requires_retry:
        # For partially correct SAQ answers, stay on same question
        next_question = current_question

    final_score = None
    if not next_question and not requires_retry:
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
