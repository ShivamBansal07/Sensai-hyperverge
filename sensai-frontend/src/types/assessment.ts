export interface MCQOption {
    option_id: number;
    text: string;
    is_correct: boolean;
}

export interface Question {
    question_id: string;
    page_number: number;
    question_type: 'mcq' | 'saq';
    question_text: string;
    mcq_options?: MCQOption[];
    ideal_answer?: string;
}

export interface QuestionBank {
    questions: Question[];
}

export interface QuizFeedback {
    is_correct: boolean;
    correct_answer?: string;
    next_question?: Question;
    final_score?: string;
    new_score?: number;
    new_total_questions_answered?: number;
    
    // Enhanced SAQ evaluation fields
    feedback_type?: 'correct' | 'partially_correct' | 'incorrect';
    hint?: string;
    explanation?: string;
    requires_retry: boolean;
}

export interface QuizAnswerRequest {
    question_id: string;
    answer: string;
    question_bank: QuestionBank;
    current_score: number;
    total_questions_answered: number;
    session_id?: string;
}
