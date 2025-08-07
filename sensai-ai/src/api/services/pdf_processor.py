import fitz  # PyMuPDF
import instructor
import asyncio
from openai import OpenAI
from typing import IO
from fastapi import HTTPException
from ..models import QuestionBank, Question
from ..llm import get_llm_client
from ..utils.logging import logger

async def process_pdf(pdf_content: bytes, max_pages: int) -> QuestionBank:
    """
    Processes a PDF file page by page to extract text and generate questions.
    """
    try:
        # Run the synchronous, blocking fitz.open call in a separate thread
        pdf_document = await asyncio.to_thread(fitz.open, stream=pdf_content, filetype="pdf")
    except Exception as e:
        logger.error(f"Failed to open PDF: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to open PDF: {e}")

    if len(pdf_document) > max_pages:
        raise HTTPException(status_code=400, detail=f"PDF exceeds the maximum of {max_pages} pages.")

    all_questions = []
    client = get_llm_client()
    global_question_counter = 0  # Counter for unique question IDs

    for page_num in range(len(pdf_document)):
        logger.info(f"Processing page {page_num + 1} of {len(pdf_document)}")
        page = pdf_document.load_page(page_num)
        text_content = page.get_text()

        if not text_content.strip():
            logger.info(f"Skipping page {page_num + 1} as it contains no text.")
            # Skip pages with no text content
            continue

        try:
            # Use instructor to get structured output from the LLM
            question_bank_for_page = await client.chat.completions.create(
                model="openai/gpt-4o-mini",
                response_model=QuestionBank,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a university-level educator designing a challenging quiz. "
                            "Based *only* on the provided text, generate a mix of 2-3 Multiple Choice Questions (MCQ) "
                            "and 1-2 Short Answer Questions (SAQ). "
                            "For MCQs, provide exactly 4 options, with only one marked as correct. "
                            "For SAQs, provide a concise, ideal answer."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Text from Page {page_num + 1}:\n\n{text_content}",
                    },
                ],
            )
            
            # Add the page number to each question and assign unique IDs
            for question in question_bank_for_page.questions:
                global_question_counter += 1
                question.page_number = page_num + 1
                # Generate unique question ID: original_type + global_counter
                original_type = question.question_type.value  # 'mcq' or 'saq'
                question.question_id = f"{original_type}_{global_question_counter}"
                all_questions.append(question)

        except Exception as e:
            # In a real scenario, you might want to log this error and continue
            # For the MVP, we can be strict and fail the request
            raise HTTPException(status_code=500, detail=f"Failed to generate questions for page {page_num + 1}: {e}")

    if not all_questions:
        raise HTTPException(status_code=400, detail="This PDF contains no text or question generation failed for all pages.")

    return QuestionBank(questions=all_questions)
