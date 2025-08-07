import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models import QuestionBank
from ..models import Question, QuestionBank
from ..services.pdf_processor import process_pdf
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

class QuizFeedback(BaseModel):
    is_correct: bool
    correct_answer: Optional[str] = None
    next_question: Optional[Question] = None
    final_score: Optional[str] = None
    new_score: Optional[int] = None
    new_total_questions_answered: Optional[int] = None

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

    if current_question.question_type == 'mcq':
        correct_option = next((opt for opt in current_question.mcq_options if opt.is_correct), None)
        if correct_option:
            correct_answer = correct_option.text
            if quiz_answer.answer == correct_option.text:
                is_correct = True
                new_score += 1
    elif current_question.question_type == 'saq':
        correct_answer = current_question.ideal_answer
        if correct_answer and quiz_answer.answer.lower() in correct_answer.lower():
            is_correct = True
            new_score += 1

    # Simple progression logic with unique question IDs
    current_index = -1
    for i, q in enumerate(question_bank.questions):
        if q.question_id == current_question.question_id:
            current_index = i
            break

    next_question = None
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
    )
