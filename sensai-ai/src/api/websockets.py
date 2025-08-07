import asyncio
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from pydantic import BaseModel
from .models import QuestionBank, Question, QuestionType, MCQOption # Assuming these models exist or will be created
from .utils.logging import logger

router = APIRouter()


# Existing ConnectionManager for course generation updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, course_id: int):
        await websocket.accept()
        if course_id not in self.active_connections:
            self.active_connections[course_id].add(websocket)

    def disconnect(self, websocket: WebSocket, course_id: int):
        if course_id in self.active_connections:
            self.active_connections[course_id].discard(websocket)
            if not self.active_connections[course_id]:
                del self.active_connections[course_id]

    async def send_item_update(self, course_id: int, item_data: Dict):
        if course_id in self.active_connections:
            disconnected_websockets = set()
            for websocket in self.active_connections[course_id]:
                try:
                    await websocket.send_json(item_data)
                except Exception as exception:
                    print(exception)
                    disconnected_websockets.add(websocket)

            for websocket in disconnected_websockets:
                self.disconnect(websocket, course_id)


# Create a connection manager instance
manager = ConnectionManager()


# WebSocket endpoint for course generation updates
@router.websocket("/course/{course_id}/generation")
async def websocket_course_generation(websocket: WebSocket, course_id: int):
    try:
        await manager.connect(websocket, course_id)

        # Keep the connection alive until client disconnects
        while True:
            # Wait for any message from the client to detect disconnection
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, course_id)


# Function to get the connection manager instance
def get_manager() -> ConnectionManager:
    return manager


# New QuizManager and QuizSession for conversational quiz
class QuizSession:
    def __init__(self, session_id: str, websocket: WebSocket, question_bank: QuestionBank):
        self.session_id = session_id
        self.websocket = websocket
        self.question_bank = question_bank
        self.current_question_index = 0
        self.score = 0
        self.quiz_completed = False

    async def send_question(self):
        if self.current_question_index < len(self.question_bank.questions):
            question = self.question_bank.questions[self.current_question_index]
            payload = {
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "options": [option.model_dump() for option in question.mcq_options] if question.mcq_options else [],
            }
            await self.websocket.send_json({"type": "NEW_QUESTION", "payload": payload})
        else:
            await self.send_quiz_complete()

    async def evaluate_answer(self, answer: str):
        if self.quiz_completed:
            return

        current_question = self.question_bank.questions[self.current_question_index]
        is_correct = False
        correct_answer_text = ""

        if current_question.question_type == QuestionType.MCQ:
            # For MCQ, 'answer' is expected to be the option_id
            selected_option = next((opt for opt in current_question.mcq_options if str(opt.option_id) == answer), None)
            if selected_option and selected_option.is_correct:
                is_correct = True
            correct_option = next((opt for opt in current_question.mcq_options if opt.is_correct), None)
            correct_answer_text = correct_option.text if correct_option else "N/A"
        elif current_question.question_type == QuestionType.SAQ:
            # For SAQ, 'answer' is the text, perform case-insensitive substring check
            if current_question.ideal_answer and answer.lower() in current_question.ideal_answer.lower():
                is_correct = True
            correct_answer_text = current_question.ideal_answer or "N/A"

        if is_correct:
            self.score += 1

        await self.websocket.send_json({
            "type": "ANSWER_FEEDBACK",
            "payload": {
                "is_correct": is_correct,
                "correct_answer": correct_answer_text,
                "your_answer": answer
            }
        })

        self.current_question_index += 1
        await asyncio.sleep(1) # Small delay before sending next question for better UX
        await self.send_question()

    async def send_quiz_complete(self):
        self.quiz_completed = True
        await self.websocket.send_json({
            "type": "QUIZ_COMPLETE",
            "payload": {
                "final_score": f"{self.score}/{len(self.question_bank.questions)}"
            }
        })
        await self.websocket.close()


class QuizManager:
    def __init__(self):
        self.active_quiz_sessions: Dict[str, QuizSession] = {}

    async def connect(self, websocket: WebSocket, session_id: str, question_bank: QuestionBank):
        await websocket.accept()
        if session_id in self.active_quiz_sessions:
            # Close existing connection if a new one is made for the same session_id
            logger.warning(f"Session {session_id} already active. Closing old connection.")
            await self.active_quiz_sessions[session_id].websocket.close()
            del self.active_quiz_sessions[session_id]

        session = QuizSession(session_id, websocket, question_bank)
        self.active_quiz_sessions[session_id] = session
        logger.info(f"Quiz session {session_id} connected.")
        await session.send_question() # Send the first question upon connection

    def disconnect(self, session_id: str):
        if session_id in self.active_quiz_sessions:
            del self.active_quiz_sessions[session_id]
            logger.info(f"Quiz session {session_id} disconnected.")

quiz_manager = QuizManager()

@router.websocket("/ws/quiz/{session_id}")
async def websocket_quiz(websocket: WebSocket, session_id: str):
    # TODO: In a real application, retrieve the QuestionBank based on session_id
    # For now, we'll use a mock QuestionBank for demonstration
    mock_question_bank = QuestionBank(
        questions=[
            Question(
                question_id="q1",
                question_text="What is the capital of France?",
                question_type=QuestionType.MCQ,
                mcq_options=[
                    MCQOption(option_id=1, text="Berlin", is_correct=False),
                    MCQOption(option_id=2, text="Paris", is_correct=True),
                    MCQOption(option_id=3, text="Rome", is_correct=False),
                ],
                ideal_answer=None,
            ),
            Question(
                question_id="q2",
                question_text="The chemical symbol for water is H2O. True or False?",
                question_type=QuestionType.SAQ,
                mcq_options=[],
                ideal_answer="True",
            ),
            Question(
                question_id="q3",
                question_text="What is 2 + 2?",
                question_type=QuestionType.SAQ,
                mcq_options=[],
                ideal_answer="4",
            ),
        ]
    )

    try:
        await quiz_manager.connect(websocket, session_id, mock_question_bank)
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "SUBMIT_ANSWER":
                answer = data.get("payload", {}).get("answer")
                if answer is not None:
                    session = quiz_manager.active_quiz_sessions.get(session_id)
                    if session:
                        await session.evaluate_answer(str(answer))
                    else:
                        logger.error(f"No active session found for {session_id} during answer submission.")
                        await websocket.send_json({"type": "ERROR", "payload": {"message": "Quiz session not found."}})
                else:
                    logger.warning(f"Received SUBMIT_ANSWER without 'answer' payload for session {session_id}.")
                    await websocket.send_json({"type": "ERROR", "payload": {"message": "Missing answer in payload."}})
            else:
                logger.warning(f"Received unknown message type: {data.get('type')} for session {session_id}.")
                await websocket.send_json({"type": "ERROR", "payload": {"message": "Unknown message type."}})

    except WebSocketDisconnect:
        quiz_manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"Error in quiz WebSocket for session {session_id}: {e}")
        quiz_manager.disconnect(session_id)
        # Optionally send an error message before closing
        try:
            await websocket.send_json({"type": "ERROR", "payload": {"message": "An unexpected error occurred."}})
        except RuntimeError:
            pass # WebSocket already closed or in closing state
