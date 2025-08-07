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
