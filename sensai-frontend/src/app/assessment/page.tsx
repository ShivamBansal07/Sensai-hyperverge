'use client';

import React, { useState, useEffect } from 'react';
import { Upload, FileText, Download, Loader2, CheckCircle, XCircle, Trash2, List } from 'lucide-react';
import { Question } from '@/types/assessment';
import { useRouter } from 'next/navigation';

interface QuestionBank {
    questions: Question[];
}

interface CachedQuiz {
    id: string;
    questions: Question[];
    fileName: string;
    timestamp: number;
}

const CACHE_KEY = 'ai_question_generator_quizzes';
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

export default function AssessmentPage() {
    const router = useRouter();
    const [file, setFile] = useState<File | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [questions, setQuestions] = useState<Question[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<boolean>(false);
    const [cachedQuizzes, setCachedQuizzes] = useState<CachedQuiz[]>([]);
    const [selectedQuizId, setSelectedQuizId] = useState<string | null>(null);

    // Load cached quizzes on component mount
    useEffect(() => {
        const loadCachedQuizzes = () => {
            try {
                const cached = localStorage.getItem(CACHE_KEY);
                if (cached) {
                    const quizzes: CachedQuiz[] = JSON.parse(cached);
                    const now = Date.now();
                    const validQuizzes = quizzes.filter(quiz => now - quiz.timestamp < CACHE_DURATION);
                    setCachedQuizzes(validQuizzes);
                    if (validQuizzes.length !== quizzes.length) {
                        localStorage.setItem(CACHE_KEY, JSON.stringify(validQuizzes));
                    }
                }
            } catch (error) {
                console.error('Error loading cached quizzes:', error);
                localStorage.removeItem(CACHE_KEY);
            }
        };
        loadCachedQuizzes();
    }, []);

    // Save a new quiz to cache
    const saveToCache = (newQuiz: CachedQuiz) => {
        try {
            const updatedQuizzes = [...cachedQuizzes, newQuiz];
            localStorage.setItem(CACHE_KEY, JSON.stringify(updatedQuizzes));
            setCachedQuizzes(updatedQuizzes);
        } catch (error) {
            console.error('Error saving to cache:', error);
        }
    };

    // Delete a specific quiz from cache
    const deleteFromCache = (quizId: string) => {
        try {
            const updatedQuizzes = cachedQuizzes.filter(quiz => quiz.id !== quizId);
            localStorage.setItem(CACHE_KEY, JSON.stringify(updatedQuizzes));
            setCachedQuizzes(updatedQuizzes);
            if (selectedQuizId === quizId) {
                setQuestions([]);
                setSelectedQuizId(null);
                setSuccess(false);
            }
        } catch (error) {
            console.error('Error deleting from cache:', error);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            if (selectedFile.type !== 'application/pdf') {
                setError('Please select a PDF file only');
                return;
            }
            if (selectedFile.size > 5 * 1024 * 1024) { // 5MB limit
                setError('File size should be less than 5MB');
                return;
            }
            setFile(selectedFile);
            setError(null);
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setError('Please select a file first');
            return;
        }

        setIsLoading(true);
        setError(null);
        setSuccess(false);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('http://localhost:8001/assessment/generate-questions', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data: QuestionBank = await response.json();
            const quizId = `${file.name.replace('.pdf', '')}_${Date.now()}`;
            const newQuiz: CachedQuiz = {
                id: quizId,
                questions: data.questions,
                fileName: file.name,
                timestamp: Date.now()
            };

            saveToCache(newQuiz);
            setQuestions(data.questions);
            setSelectedQuizId(quizId);
            setSuccess(true);
        } catch (err) {
            console.error('Upload error:', err);
            setError(err instanceof Error ? err.message : 'An error occurred while processing the file');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSelectQuiz = (quizId: string) => {
        const quiz = cachedQuizzes.find(q => q.id === quizId);
        if (quiz) {
            setQuestions(quiz.questions);
            setSelectedQuizId(quiz.id);
            setSuccess(true);
            setFile(null);
        }
    };

    const downloadJSON = () => {
        const quiz = cachedQuizzes.find(q => q.id === selectedQuizId);
        if (!quiz) return;

        const dataStr = JSON.stringify({ questions: quiz.questions }, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
        const exportFileDefaultName = `questions_${quiz.fileName.replace('.pdf', '')}.json`;

        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
    };

    const startQuiz = () => {
        if (selectedQuizId) {
            router.push(`/quiz/${selectedQuizId}`);
        }
    };

    return (
        <div className="min-h-screen bg-black text-white py-8 px-4">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <div className="text-center mb-12">
                    <h1 className="text-4xl font-bold text-white mb-4">
                        AI Question Generator
                    </h1>
                    <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                        Upload your PDF document and let AI generate comprehensive questions for assessment purposes
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {/* Left Column: Upload and Cached Quizzes */}
                    <div className="md:col-span-1">
                        {/* Upload Section */}
                        <div className="bg-[#111111] border border-[#333333] rounded-2xl p-6 mb-8">
                            <h2 className="text-2xl font-semibold text-white mb-4">Upload PDF</h2>
                            <div className="mb-4">
                                <input
                                    type="file"
                                    accept=".pdf"
                                    onChange={handleFileChange}
                                    className="hidden"
                                    id="pdf-upload"
                                />
                                <label
                                    htmlFor="pdf-upload"
                                    className="w-full inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg cursor-pointer transition-colors"
                                >
                                    <FileText className="w-5 h-5" />
                                    Select PDF File
                                </label>
                            </div>
                            {file && (
                                <div className="bg-[#222222] border border-blue-600 rounded-lg p-3 mb-4 text-sm">
                                    <p className="text-white font-medium truncate">{file.name}</p>
                                    <p className="text-gray-400">({(file.size / 1024 / 1024).toFixed(1)} MB)</p>
                                </div>
                            )}
                            <button
                                onClick={handleUpload}
                                disabled={!file || isLoading}
                                className="w-full inline-flex items-center justify-center gap-2 bg-white text-black hover:bg-gray-100 disabled:bg-gray-600 disabled:text-gray-400 disabled:cursor-not-allowed px-8 py-3 rounded-full font-medium transition-colors"
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                        Generating...
                                    </>
                                ) : (
                                    'Generate Questions'
                                )}
                            </button>
                        </div>

                        {/* Cached Quizzes List */}
                        <div className="bg-[#111111] border border-[#333333] rounded-2xl p-6">
                            <h2 className="text-2xl font-semibold text-white mb-4">Cached Quizzes</h2>
                            {cachedQuizzes.length > 0 ? (
                                <ul className="space-y-3">
                                    {cachedQuizzes.map(quiz => (
                                        <li key={quiz.id} className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${selectedQuizId === quiz.id ? 'bg-blue-600/20 border-blue-500 border' : 'bg-[#222222] hover:bg-[#333333]'}`} onClick={() => handleSelectQuiz(quiz.id)}>
                                            <div className="flex items-center gap-3">
                                                <List className="w-5 h-5 text-gray-400" />
                                                <span className="text-white truncate">{quiz.fileName}</span>
                                            </div>
                                            <button onClick={(e) => { e.stopPropagation(); deleteFromCache(quiz.id); }} className="p-1 text-red-500 hover:text-red-400">
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="text-gray-500 text-center">No cached quizzes found.</p>
                            )}
                        </div>
                    </div>

                    {/* Right Column: Results Section */}
                    <div className="md:col-span-2">
                        {error && (
                            <div className="bg-red-900/30 border border-red-600 rounded-lg p-4 mb-6 flex items-center gap-2 text-red-400">
                                <XCircle className="w-5 h-5" />
                                <span>{error}</span>
                            </div>
                        )}
                        {questions.length > 0 ? (
                            <div className="bg-[#111111] border border-[#333333] rounded-2xl p-8">
                                <div className="flex items-center justify-between mb-8">
                                    <div>
                                        <h2 className="text-2xl font-semibold text-white">
                                            Generated Questions ({questions.length})
                                        </h2>
                                        <p className="text-sm text-gray-400 mt-1">
                                            From: {cachedQuizzes.find(q => q.id === selectedQuizId)?.fileName}
                                        </p>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={downloadJSON}
                                            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
                                        >
                                            <Download className="w-5 h-5" />
                                            JSON
                                        </button>
                                        <button
                                            onClick={startQuiz}
                                            className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors"
                                        >
                                            Start Quiz
                                        </button>
                                    </div>
                                </div>

                                <div className="space-y-6">
                                    {questions.map((question, index) => (
                                        <div key={`${question.question_id}-${question.page_number}-${index}`} className="border border-[#333333] rounded-lg p-6 bg-[#0a0a0a]">
                                            <div className="flex items-start justify-between mb-4">
                                                <div className="flex items-center gap-3">
                                                    <span className="bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-medium">
                                                        Q{index + 1}
                                                    </span>
                                                    <span className="bg-[#333333] text-gray-300 px-3 py-1 rounded-full text-sm">
                                                        Page {question.page_number}
                                                    </span>
                                                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${question.question_type === 'mcq'
                                                        ? 'bg-green-600 text-white'
                                                        : 'bg-purple-600 text-white'
                                                        }`}>
                                                        {question.question_type.toUpperCase()}
                                                    </span>
                                                </div>
                                            </div>

                                            <h3 className="text-lg font-medium text-white mb-4">
                                                {question.question_text}
                                            </h3>

                                            {question.question_type === 'mcq' && question.mcq_options && (
                                                <div className="space-y-2">
                                                    <h4 className="font-medium text-gray-300 mb-2">Options:</h4>
                                                    {question.mcq_options.map((option) => (
                                                        <div
                                                            key={option.option_id}
                                                            className={`p-3 rounded-lg border ${option.is_correct
                                                                ? 'bg-green-900/30 border-green-600 text-green-300'
                                                                : 'bg-[#222222] border-[#444444] text-gray-300'
                                                                }`}
                                                        >
                                                            <div className="flex items-center gap-2">
                                                                <span className="font-medium">
                                                                    {String.fromCharCode(65 + option.option_id - 1)}.
                                                                </span>
                                                                <span>{option.text}</span>
                                                                {option.is_correct && (
                                                                    <span className="ml-auto text-sm font-medium text-green-400">
                                                                        ✓ Correct
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}

                                            {question.question_type === 'saq' && question.ideal_answer && (
                                                <div className="bg-blue-900/30 border border-blue-600 rounded-lg p-4">
                                                    <h4 className="font-medium text-blue-300 mb-2">Ideal Answer:</h4>
                                                    <p className="text-blue-200">{question.ideal_answer}</p>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div className="text-center py-20 bg-[#111111] border border-[#333333] rounded-2xl">
                                <p className="text-gray-400">
                                    Upload a new PDF or select a cached quiz to view questions.
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
