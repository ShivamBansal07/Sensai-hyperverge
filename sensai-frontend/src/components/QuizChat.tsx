import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Loader2, MessageSquare, Clipboard, Clock, CheckCircle, XCircle } from 'lucide-react';
import { Question, MCQOption } from '@/types/assessment';

interface ChatMessage {
    id: string;
    sender: 'user' | 'bot';
    text: string;
    isTyping?: boolean;
    options?: MCQOption[];
    feedbackType?: 'correct' | 'partially_correct' | 'incorrect';
}

interface QuizChatProps {
    sessionId: string;
    initialQuestions?: Question[];
}

const QuizChat: React.FC<QuizChatProps> = ({ sessionId, initialQuestions }) => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [isBotTyping, setIsBotTyping] = useState(false);
    const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
    const [questionBank, setQuestionBank] = useState<Question[]>([]);
    const [quizCompleted, setQuizCompleted] = useState(false);
    const [currentScore, setCurrentScore] = useState(0);
    const [totalQuestionsAnswered, setTotalQuestionsAnswered] = useState(0);
    const [answerStartTime, setAnswerStartTime] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isTabFocused, setIsTabFocused] = useState(true);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

    const API_URL = `http://localhost:8001/assessment/quiz/answer`;
    const INTEGRITY_LOG_URL = `http://localhost:8001/assessment/integrity-log`;
    const CLEAR_SESSION_URL = `http://localhost:8001/assessment/clear-session`;

    const clearSessionLogs = useCallback(async () => {
        try {
            console.log(`Clearing previous logs for session ${sessionId}`);
            const response = await fetch(`${CLEAR_SESSION_URL}/${sessionId}`, {
                method: 'POST',
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Session logs cleared:', result.message);
            } else {
                console.warn('Failed to clear session logs:', response.status);
            }
        } catch (clearError) {
            console.warn('Failed to clear session logs:', clearError);
        }
    }, [sessionId, CLEAR_SESSION_URL]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        if (initialQuestions && initialQuestions.length > 0) {
            console.log(`QuizChat: Received ${initialQuestions.length} initial questions.`);
            
            // Clear any previous integrity logs for this session
            clearSessionLogs();
            
            setQuestionBank(initialQuestions);
            const firstQuestion = initialQuestions[0];
            setCurrentQuestion(firstQuestion);
            setMessages([
                {
                    id: `q-${firstQuestion.question_id}-${Date.now()}`,
                    sender: 'bot',
                    text: firstQuestion.question_text,
                    options: firstQuestion.mcq_options,
                },
            ]);
            setAnswerStartTime(Date.now());
        } else {
            console.log("QuizChat: No initial questions received or initialQuestions is empty.");
        }
    }, [initialQuestions, clearSessionLogs]);

    const sendIntegrityLog = useCallback(async (eventType: string, payload: any = {}) => {
        console.log('Sending integrity log:', eventType, payload); // Debug logging
        try {
            const response = await fetch(INTEGRITY_LOG_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    event_type: eventType,
                    timestamp: Date.now(),
                    ...payload,
                }),
            });
            
            if (response.ok) {
                console.log('Integrity log sent successfully:', eventType);
            } else {
                console.error('Integrity log failed with status:', response.status);
            }
        } catch (logError) {
            console.error('Failed to send integrity log:', logError);
        }
    }, [sessionId, INTEGRITY_LOG_URL]);

    useEffect(() => {
        const handleVisibilityChange = () => {
            if (document.hidden) {
                sendIntegrityLog('TAB_UNFOCUSED');
                setIsTabFocused(false);
            } else {
                sendIntegrityLog('TAB_FOCUSED');
                setIsTabFocused(true);
            }
        };

        const handleBeforeUnload = () => {
            sendIntegrityLog('PAGE_UNLOADED');
        };

        document.addEventListener('visibilitychange', handleVisibilityChange);
        window.addEventListener('beforeunload', handleBeforeUnload);

        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange);
            window.removeEventListener('beforeunload', handleBeforeUnload);
        };
    }, [sendIntegrityLog]);

    const handleSubmit = useCallback(async (answer: string) => {
        if (!currentQuestion || isBotTyping || quizCompleted) return;

        const timeTakenMs = answerStartTime ? Date.now() - answerStartTime : null;

        if (timeTakenMs !== null && currentQuestion.question_type === 'saq' && timeTakenMs < 2000) {
            sendIntegrityLog('UNUSUAL_TIMING', { time_taken_ms: timeTakenMs, question_id: currentQuestion.question_id });
        }

        setMessages((prev) => [
            ...prev,
            { id: `user-${Date.now()}`, sender: 'user', text: answer },
        ]);
        setInput('');
        setIsBotTyping(true);

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question_id: currentQuestion.question_id,
                    answer: answer,
                    question_bank: { questions: questionBank },
                    current_score: currentScore,
                    total_questions_answered: totalQuestionsAnswered,
                }),
            });
            console.log(`QuizChat: Sending answer for question ${currentQuestion.question_id}. Question bank size: ${questionBank.length}`);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const feedback = await response.json();
            const feedbackType = feedback.is_correct ? 'correct' : 'incorrect'; setCurrentScore(feedback.new_score);
            setTotalQuestionsAnswered(feedback.new_total_questions_answered);

            setMessages((prev) => [
                ...prev,
                {
                    id: `feedback-${Date.now()}`,
                    sender: 'bot',
                    text: feedback.is_correct ? 'Correct!' : `Incorrect. The correct answer is: ${feedback.correct_answer}`,
                    feedbackType: feedbackType,
                },
            ]);

            if (feedback.next_question) {
                setCurrentQuestion(feedback.next_question);
                setMessages((prev) => [
                    ...prev,
                    {
                        id: `q-${feedback.next_question.question_id}-${Date.now()}`,
                        sender: 'bot',
                        text: feedback.next_question.question_text,
                        options: feedback.next_question.mcq_options,
                    },
                ]);
                setAnswerStartTime(Date.now());
            } else {
                setCurrentQuestion(null);
                setQuizCompleted(true);
                setMessages((prev) => [
                    ...prev,
                    { id: `complete-${Date.now()}`, sender: 'bot', text: feedback.final_score || `Quiz complete! Your score: ${currentScore}/${totalQuestionsAnswered}` },
                ]);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred.');
        } finally {
            setIsBotTyping(false);
        }
    }, [currentQuestion, isBotTyping, quizCompleted, answerStartTime, sendIntegrityLog, questionBank, API_URL, currentScore, totalQuestionsAnswered]);

    const handleOptionClick = (optionText: string, optionId: number) => {
        if (currentQuestion?.question_type === 'mcq') {
            handleSubmit(optionText); // For MCQ, the answer is the option text
        }
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setInput(e.target.value);
    };

    const handlePaste = useCallback((e: React.ClipboardEvent<HTMLTextAreaElement>) => {
        console.log('Paste detected!', currentQuestion?.question_type); // Debug logging
        if (currentQuestion?.question_type === 'saq') {
            const pastedText = e.clipboardData.getData('text');
            console.log('Pasted text:', pastedText); // Debug logging
            sendIntegrityLog('PASTE_DETECTED', { question_id: currentQuestion.question_id, pasted_text: pastedText });
        }
    }, [currentQuestion, sendIntegrityLog]);

    const renderMessage = (message: ChatMessage) => {
        const isUser = message.sender === 'user';
        const messageClass = isUser ? 'bg-blue-600 self-end rounded-br-none' : 'bg-[#222222] self-start rounded-bl-none';
        const textColor = isUser ? 'text-white' : 'text-gray-200';

        let feedbackIcon = null;
        if (message.feedbackType === 'correct') {
            feedbackIcon = <CheckCircle className="w-4 h-4 text-green-400 mr-1" />;
        } else if (message.feedbackType === 'partially_correct') {
            feedbackIcon = <MessageSquare className="w-4 h-4 text-yellow-400 mr-1" />;
        } else if (message.feedbackType === 'incorrect') {
            feedbackIcon = <XCircle className="w-4 h-4 text-red-400 mr-1" />;
        }

        return (
            <div key={message.id} className={`flex flex-col max-w-[70%] ${isUser ? 'items-end' : 'items-start'}`}>
                <div className={`p-3 rounded-xl ${messageClass} ${textColor} shadow-md`}>
                    <div className="flex items-center">
                        {feedbackIcon}
                        {message.text}
                        {message.isTyping && (
                            <span className="ml-2 animate-pulse">...</span>
                        )}
                    </div>
                </div>
                {message.options && message.options.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                        {message.options.map((option) => (
                            <button
                                key={option.option_id}
                                onClick={() => handleOptionClick(option.text, option.option_id)}
                                disabled={isBotTyping}
                                className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {String.fromCharCode(65 + option.option_id - 1)}. {option.text}
                            </button>
                        ))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="flex flex-col h-full bg-black text-white rounded-lg shadow-lg">
            {/* Header */}
            <div className="p-4 border-b border-[#333333] flex items-center justify-between">
                <h2 className="text-xl font-semibold">AI Quiz Tutor</h2>
                <span className={`text-sm px-3 py-1 rounded-full ${'bg-green-600'}`}>
                    Online
                </span>
            </div>

            {/* Chat History */}
            <div className="flex-1 p-4 overflow-y-auto space-y-4 custom-scrollbar">
                {messages.map(renderMessage)}
                {isBotTyping && (
                    <div className="flex items-center self-start">
                        <div className="bg-[#222222] p-3 rounded-xl rounded-bl-none text-gray-200 shadow-md">
                            <Loader2 className="w-5 h-5 animate-spin inline-block mr-2" />
                            <span className="animate-pulse">Typing...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-[#333333] flex items-center gap-2">
                {currentQuestion?.question_type === 'saq' ? (
                    <textarea
                        ref={inputRef as React.RefObject<HTMLTextAreaElement>}
                        className="flex-1 bg-[#222222] border border-[#444444] rounded-lg p-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
                        placeholder="Type your answer here..."
                        value={input}
                        onChange={handleInputChange}
                        onPaste={handlePaste}
                        rows={1}
                        disabled={isBotTyping || quizCompleted}
                    />
                ) : (
                    <input
                        ref={inputRef as React.RefObject<HTMLInputElement>}
                        type="text"
                        className="flex-1 bg-[#222222] border border-[#444444] rounded-lg p-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                        placeholder="Select an option or type your answer..."
                        value={input}
                        onChange={handleInputChange}
                        disabled={isBotTyping || quizCompleted || currentQuestion?.question_type === 'mcq'}
                    />
                )}
                <button
                    onClick={() => handleSubmit(input)}
                    disabled={isBotTyping || quizCompleted || !input.trim() || currentQuestion?.question_type === 'mcq'}
                    className="bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg disabled:bg-gray-600 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
                >
                    <Send className="w-5 h-5" />
                </button>
            </div>
        </div>
    );
};

export default QuizChat;
