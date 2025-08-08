#!/usr/bin/env python3
"""
SAQ Evaluation Test Script

This script loads questions from a JSON file and allows testing the SAQ evaluation
pipeline in the terminal before integrating back to the frontend.
"""

import json
import asyncio
import sys
import os
from typing import List, Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api.services.saq_evaluator import SAQEvaluatorService
from src.api.models import SAQEvaluationRequest
from src.api.utils.logging import logger

class SAQTester:
    def __init__(self, questions_file: str):
        self.questions_file = questions_file
        self.questions = []
        self.evaluator = None
        
    def load_questions(self):
        """Load questions from JSON file"""
        try:
            with open(self.questions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.questions = data.get('questions', [])
                print(f"✅ Loaded {len(self.questions)} questions from {self.questions_file}")
                
                # Filter SAQ questions
                saq_questions = [q for q in self.questions if q.get('question_type') == 'saq']
                print(f"📝 Found {len(saq_questions)} SAQ questions")
                return True
        except Exception as e:
            print(f"❌ Error loading questions: {e}")
            return False
    
    async def initialize_evaluator(self):
        """Initialize the SAQ evaluator service"""
        try:
            self.evaluator = SAQEvaluatorService()
            print("✅ SAQ Evaluator service initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Error initializing evaluator: {e}")
            return False
    
    def get_saq_questions(self) -> List[Dict[str, Any]]:
        """Get only SAQ questions"""
        return [q for q in self.questions if q.get('question_type') == 'saq']
    
    async def test_saq_question(self, question: Dict[str, Any], student_answer: str) -> Dict[str, Any]:
        """Test a single SAQ question with student answer"""
        if not self.evaluator:
            raise Exception("Evaluator not initialized")
        
        # Create evaluation request
        evaluation_request = SAQEvaluationRequest(
            question_text=question.get('question_text', ''),
            ideal_answer=question.get('ideal_answer', ''),
            student_answer=student_answer,
            question_id=question.get('question_id', ''),
            session_id=f"test_session_{question.get('question_id', '')}"
        )
        
        print(f"\n📊 Evaluating SAQ: {question.get('question_id', 'unknown')}")
        print(f"❓ Question: {question.get('question_text', '')[:100]}...")
        print(f"💡 Ideal Answer: {question.get('ideal_answer', '')[:100]}...")
        print(f"🎯 Student Answer: {student_answer}")
        
        try:
            # Perform evaluation
            result = await self.evaluator.evaluate_saq_complete(evaluation_request)
            
            print(f"📈 Evaluation Result:")
            print(f"   ✅ Score: {result.evaluation}")
            print(f"   📝 Explanation: {result.explanation_or_hint}")
            print(f"   🔄 Requires Retry: {result.requires_retry}")
            
            return {
                'success': True,
                'result': result,
                'question_id': question.get('question_id', ''),
                'student_answer': student_answer
            }
            
        except Exception as e:
            print(f"❌ Evaluation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'question_id': question.get('question_id', ''),
                'student_answer': student_answer
            }
    
    def display_menu(self):
        """Display the main menu"""
        print("\n" + "="*60)
        print("🧠 SAQ Evaluation Test System")
        print("="*60)
        print("1. List all SAQ questions")
        print("2. Test specific SAQ question")
        print("3. Test all SAQ questions with sample answers")
        print("4. Interactive SAQ testing")
        print("5. Exit")
        print("="*60)
    
    def list_saq_questions(self):
        """List all SAQ questions"""
        saq_questions = self.get_saq_questions()
        if not saq_questions:
            print("❌ No SAQ questions found")
            return
        
        print(f"\n📋 SAQ Questions ({len(saq_questions)} total):")
        print("-" * 60)
        
        for i, question in enumerate(saq_questions, 1):
            print(f"{i}. ID: {question.get('question_id', 'unknown')}")
            print(f"   Question: {question.get('question_text', '')[:80]}...")
            print(f"   Ideal Answer: {question.get('ideal_answer', '')[:80]}...")
            print()
    
    async def interactive_saq_testing(self):
        """Interactive SAQ testing mode"""
        saq_questions = self.get_saq_questions()
        if not saq_questions:
            print("❌ No SAQ questions found")
            return
        
        while True:
            print(f"\n🎯 Interactive SAQ Testing ({len(saq_questions)} questions available)")
            print("-" * 60)
            
            # Show questions
            for i, question in enumerate(saq_questions, 1):
                print(f"{i}. {question.get('question_text', '')[:60]}...")
            
            print("\nEnter question number (1-{}) or 'q' to quit:".format(len(saq_questions)))
            choice = input("➤ ").strip()
            
            if choice.lower() == 'q':
                break
            
            try:
                question_idx = int(choice) - 1
                if 0 <= question_idx < len(saq_questions):
                    question = saq_questions[question_idx]
                    
                    print(f"\n📝 Question: {question.get('question_text', '')}")
                    print(f"💡 Ideal Answer: {question.get('ideal_answer', '')}")
                    print("\nEnter your answer (or 'skip' to skip):")
                    student_answer = input("➤ ").strip()
                    
                    if student_answer.lower() != 'skip' and student_answer:
                        await self.test_saq_question(question, student_answer)
                    
                    input("\nPress Enter to continue...")
                else:
                    print("❌ Invalid question number")
            except ValueError:
                print("❌ Please enter a valid number")
    
    async def test_sample_answers(self):
        """Test all SAQ questions with sample answers"""
        saq_questions = self.get_saq_questions()
        if not saq_questions:
            print("❌ No SAQ questions found")
            return
        
        print(f"\n🧪 Testing {len(saq_questions)} SAQ questions with sample answers...")
        
        results = []
        for i, question in enumerate(saq_questions, 1):
            print(f"\n[{i}/{len(saq_questions)}] Testing question: {question.get('question_id', 'unknown')}")
            
            # Test with different types of answers
            test_answers = [
                question.get('ideal_answer', '')[:50],  # Partial correct answer
                question.get('ideal_answer', ''),       # Full ideal answer
                "I don't know",                          # Clearly incorrect
                "gibberish random text xyz123"           # Gibberish
            ]
            
            for answer in test_answers:
                if answer:
                    result = await self.test_saq_question(question, answer)
                    results.append(result)
        
        # Summary
        print(f"\n📊 Testing Summary:")
        print(f"   Total tests: {len(results)}")
        print(f"   Successful evaluations: {sum(1 for r in results if r.get('success', False))}")
        print(f"   Failed evaluations: {sum(1 for r in results if not r.get('success', False))}")
    
    async def run(self):
        """Main run loop"""
        if not self.load_questions():
            return
        
        if not await self.initialize_evaluator():
            return
        
        while True:
            self.display_menu()
            choice = input("\nChoose an option (1-5): ").strip()
            
            if choice == '1':
                self.list_saq_questions()
                input("\nPress Enter to continue...")
            
            elif choice == '2':
                saq_questions = self.get_saq_questions()
                if saq_questions:
                    print("\nWhich question? Enter question ID or number:")
                    for i, q in enumerate(saq_questions, 1):
                        print(f"{i}. {q.get('question_id', 'unknown')}: {q.get('question_text', '')[:50]}...")
                    
                    test_choice = input("➤ ").strip()
                    question = None
                    
                    # Try by number first
                    try:
                        idx = int(test_choice) - 1
                        if 0 <= idx < len(saq_questions):
                            question = saq_questions[idx]
                    except ValueError:
                        # Try by question_id
                        question = next((q for q in saq_questions if q.get('question_id') == test_choice), None)
                    
                    if question:
                        answer = input("Enter student answer: ").strip()
                        if answer:
                            await self.test_saq_question(question, answer)
                    else:
                        print("❌ Question not found")
                    
                    input("\nPress Enter to continue...")
            
            elif choice == '3':
                await self.test_sample_answers()
                input("\nPress Enter to continue...")
            
            elif choice == '4':
                await self.interactive_saq_testing()
            
            elif choice == '5':
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please choose 1-5.")


async def main():
    """Main entry point"""
    # Default questions file path
    questions_file = "questions_leec201.json"
    
    # Check if file exists
    if not os.path.exists(questions_file):
        print(f"❌ Questions file not found: {questions_file}")
        print("Please ensure the questions JSON file is in the same directory as this script.")
        print("You can also specify a different file path as a command line argument.")
        
        if len(sys.argv) > 1:
            questions_file = sys.argv[1]
            if not os.path.exists(questions_file):
                print(f"❌ Specified file not found: {questions_file}")
                return
        else:
            return
    
    # Create and run tester
    tester = SAQTester(questions_file)
    await tester.run()


if __name__ == "__main__":
    print("🚀 Starting SAQ Evaluation Test Script...")
    asyncio.run(main())
