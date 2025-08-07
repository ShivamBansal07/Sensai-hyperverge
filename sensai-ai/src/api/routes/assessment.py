import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models import QuestionBank
from ..services.pdf_processor import process_pdf
from ..utils.logging import logger

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_PAGES = 50

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
