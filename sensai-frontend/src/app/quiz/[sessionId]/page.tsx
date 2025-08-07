'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import ReviewerTimeline from '@/components/ReviewerTimeline';
import { Question } from '@/types/assessment';

// Dynamically import QuizChat to prevent SSR hydration issues
const QuizChat = dynamic(() => import('@/components/QuizChat'), {
    ssr: false,
    loading: () => (
        <div className="flex items-center justify-center h-full">
            <p className="text-white">Loading quiz...</p>
        </div>
    )
});

const CACHE_KEY = 'ai_question_generator_quizzes';

interface IntegrityLog {
    session_id: string;
    event_type: string;
    timestamp: number;
    payload?: Record<string, any>;
}

interface CachedQuiz {
    id: string;
    questions: Question[];
    fileName: string;
    timestamp: number;
}

export default function QuizSessionPage() {
    const params = useParams();
    const sessionId = params.sessionId as string;
    const [initialQuestions, setInitialQuestions] = useState<Question[] | undefined>(undefined);
    const [integrityLogs, setIntegrityLogs] = useState<IntegrityLog[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchQuizDataAndLogs = async () => {
            if (!sessionId) return;

            try {
                // Load cached quiz questions
                const cached = localStorage.getItem(CACHE_KEY);
                if (cached) {
                    const quizzes: CachedQuiz[] = JSON.parse(cached);
                    const currentQuiz = quizzes.find(quiz => quiz.id === sessionId);
                    if (currentQuiz) {
                        setInitialQuestions(currentQuiz.questions);
                    }
                }

                // Fetch integrity logs
                const response = await fetch(`http://localhost:8001/assessment/integrity-logs/${sessionId}`);
                console.log('Integrity logs response status:', response.status);
                if (response.ok) {
                    const logs: IntegrityLog[] = await response.json();
                    console.log('Fetched integrity logs:', logs);
                    setIntegrityLogs(logs);
                } else {
                    console.error('Failed to fetch integrity logs:', response.statusText);
                }

            } catch (error) {
                console.error('Error loading quiz data or integrity logs:', error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchQuizDataAndLogs();
    }, [sessionId]);

    // Poll for new integrity logs every 5 seconds
    useEffect(() => {
        if (!sessionId || isLoading) return;

        const pollLogs = async () => {
            try {
                const response = await fetch(`http://localhost:8001/assessment/integrity-logs/${sessionId}`);
                if (response.ok) {
                    const logs: IntegrityLog[] = await response.json();
                    setIntegrityLogs(logs);
                }
            } catch (error) {
                console.error('Error polling integrity logs:', error);
            }
        };

        const interval = setInterval(pollLogs, 5000); // Poll every 5 seconds
        return () => clearInterval(interval);
    }, [sessionId, isLoading]);

    if (isLoading) {
        return (
            <div className="min-h-screen bg-black text-white flex items-center justify-center">
                <p className="text-xl">Loading quiz...</p>
            </div>
        );
    }

    if (!sessionId) {
        return (
            <div className="min-h-screen bg-black text-white flex items-center justify-center">
                <p className="text-xl">Session ID not found.</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-black text-white p-4 flex justify-center items-center">
            <div className="w-full max-w-3xl h-[90vh] flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                    <QuizChat key={sessionId} sessionId={sessionId} initialQuestions={initialQuestions} />
                </div>
                <div className="md:w-1/3">
                    <ReviewerTimeline logs={integrityLogs} />
                    <div className="mt-2 text-xs text-gray-500">
                        Debug: {integrityLogs.length} logs loaded
                    </div>
                </div>
            </div>
        </div>
    );
}
