# Changelog

## Version 1.0.0 (August 8, 2025)

### Added
- **Advanced AI-Powered SAQ Evaluation System:**
    - **Semantic Analysis:** Implemented a multi-step LLM-based evaluation system (`sensai-ai/src/api/services/saq_evaluator.py`) for Short Answer Questions (SAQ), utilizing `gpt-4o-mini` and `instructor` for semantic understanding of student responses. This provides a `correctness` score (0.0-1.0) and a `feedback_category` (correct, partially_correct, incorrect).
    - **Dynamic Feedback Generation:** The system now generates tailored, contextual feedback, including encouraging hints for partially correct answers and constructive explanations for incorrect ones, promoting an interactive learning loop.
    - **New Pydantic Models:** Introduced `SemanticEvaluationResult`, `DynamicFeedback`, and `SAQEvaluationRequest` in `sensai-ai/src/api/models.py` to ensure structured data exchange for the SAQ evaluation process.
- **Quiz Integrity Monitoring:**
    - **Behavioral Tracking:** Added `IntegrityEvent` and `IntegrityLog` models in `sensai-ai/src/api/models.py` to capture user behaviors during quizzes (e.g., `TAB_UNFOCUSED`, `PASTE_DETECTED`, `PAGE_UNLOADED`).
    - **API Endpoints:** New endpoints (`/assessment/integrity-log`, `/assessment/clear-session/{session_id}`) in `sensai-ai/src/api/routes/assessment.py` to receive and manage these integrity logs.
- **Comprehensive Testing Framework:**
    - **Automated Checkpoint Tests:** Introduced `run_checkpoint_tests.py` and `test_runner.bat` for automated, structured testing of the SAQ evaluation system, including backend server management.
    - **Extensive Test Suite:** Developed `test_saq_evaluation_integration.py` with tests for model validation, service layer logic (mocking LLM calls), API endpoint behavior, and full integration flows.
    - **Testing Utilities:** Added `test_utils.py` with a custom `TestLogger` (for detailed LLM interaction logging), `TestDataFactory`, `MockDataGenerator`, and `TestResultsAnalyzer` to enhance test development and reporting.
    - **Test Data & Configuration:** New `test_scenarios.json`, `test_data.json`, and `pytest.ini` for structured test data and pytest configuration.
- **Enhanced Quiz User Interface (Frontend):**
    - **AI Question Generator Page:** New `sensai-frontend/src/app/assessment/page.tsx` for uploading PDFs and generating questions, with client-side caching and JSON download functionality.
    - **Interactive Quiz Session:** New `sensai-frontend/src/app/quiz/[sessionId]/page.tsx` and `sensai-frontend/src/components/QuizChat.tsx` provide a dynamic, chat-based quiz experience with real-time feedback and integrity event logging.
    - **Reviewer Timeline:** New `sensai-frontend/src/components/ReviewerTimeline.tsx` to visualize integrity logs for a quiz session.
    - **Question Type Mapping:** Added utility functions in `LearnerQuizView.tsx` and `QuizEditor.tsx` to map frontend question types to backend API enum values for consistency.
- **Streamlined Development Environment:**
    - **Docker Compose:** Added `docker-compose.yml` for easy setup and orchestration of both backend and frontend services.
- **Project Scaffolding:** Initial setup of `sensai-ai` (FastAPI backend) and `sensai-frontend` (Next.js frontend) with core structures, API routes, and component libraries.

### Changed
- **Backend API Enhancements:**
    - `sensai-ai/src/api/routes/assessment.py`: Modified to integrate the `SAQEvaluatorService` into the `/quiz/answer` endpoint, enabling dynamic SAQ evaluation and feedback. Expanded `QuizAnswer` and `QuizFeedback` models.
    - `sensai-ai/src/api/models.py`: Updated `IntegrityEvent` to use string `session_id` and added new `event_type` values. Refined `QuestionType` enum to `MCQ` and `SAQ`.
    - `sensai-ai/src/api/services/pdf_processor.py`: Modified to generate unique question IDs for each question.
    - `sensai-ai/src/api/websockets.py`: Refactored to include `QuizManager` and `QuizSession` for managing real-time quiz sessions, now expecting `QuestionBank` from the client.
    - `sensai-ai/src/api/llm.py`: Updated `get_llm_client` to use `AsyncOpenAI` and `settings.openai_base_url`.
    - `sensai-ai/src/api/main.py`: Included the new `assessment` router.
    - `sensai-ai/src/api/routes/ai.py`: Adjusted imports and removed `tracer` related code.
    - `sensai-ai/src/api/routes/file.py`: Added a fallback for `file_extension` if `content_type` is not in the expected format.
    - `sensai-ai/src/api/settings.py`: Added `openai_base_url` to settings and commented out Phoenix tracer setup.
- **Frontend UI Updates:**
    - `sensai-frontend/src/app/assessment/page.tsx`: Enhanced caching logic to manage multiple cached quizzes and added UI for quiz selection and starting a quiz session.
    - `sensai-frontend/src/app/page.tsx`: Added a prominent section for the new AI Question Generator feature.
    - `sensai-frontend/src/app/layout.tsx`: Added `suppressHydrationWarning` to the `<html>` tag.
    - `sensai-frontend/src/components/LearnerQuizView.tsx` and `sensai-frontend/src/components/QuizEditor.tsx`: Updated to use new question type mapping utilities.
- **Dependency Management:**
    - `sensai-ai/requirements.txt`: Updated `python-multipart` version and added `PyMuPDF`.
    - `sensai-frontend/package-lock.json`: Significant changes reflecting dependency updates and removals (e.g., `cypress` related packages).

### Fixed
- **Backend Initialization Issue:** Resolved an issue affecting backend initialization, ensuring smoother application startup.

### Removed
- `cypress` and related testing dependencies from `sensai-frontend/package-lock.json`.
- Phoenix tracer setup from `sensai-ai/src/api/settings.py`.
