import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from api.routes.assessment import QuizAnswer, answer_quiz_question
from api.models import QuestionBank, Question
import json

async def test_backend_response():
    # Load test question
    with open('questions_leec201.json', 'r') as f:
        data = json.load(f)
        
    # Find an SAQ question
    saq_question = None
    for q in data['questions']:
        if q['question_type'] == 'saq':
            saq_question = q
            break

    if saq_question:
        print('Testing with SAQ question:')
        print(f'Question: {saq_question["question_text"]}')
        print(f'Testing answer: "gibberish"')
        
        # Create test objects
        question_obj = Question(**saq_question)
        bank = QuestionBank(questions=[question_obj])
        answer = QuizAnswer(
            question_id=saq_question['question_id'],
            answer='gibberish',
            question_bank=bank,
            session_id='test-123'
        )
        
        try:
            result = await answer_quiz_question(answer)
            print(f'\nBackend response:')
            print(f'feedback_type: {result.feedback_type}')
            print(f'requires_retry: {result.requires_retry}')
            print(f'hint: {result.hint}')
            print(f'explanation: {result.explanation}')
            print(f'is_correct: {result.is_correct}')
            print(f'correct_answer: {result.correct_answer}')
        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()
    else:
        print('No SAQ question found')

if __name__ == "__main__":
    asyncio.run(test_backend_response())
