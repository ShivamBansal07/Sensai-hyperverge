'use client';

import React, { useState, useEffect } from 'react';
import { Upload, FileText, Download, Loader2, CheckCircle, XCircle } from 'lucide-react';

interface MCQOption {
    option_id: number;
    text: string;
    is_correct: boolean;
}

interface Question {
    question_id: string;
    page_number: number;
    question_type: 'mcq' | 'saq';
    question_text: string;
    mcq_options?: MCQOption[];
    ideal_answer?: string;
}

interface QuestionBank {
    questions: Question[];
}

interface CachedData {
    questions: Question[];
    fileName: string;
    timestamp: number;
}

const CACHE_KEY = 'ai_question_generator_cache';
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

export default function AssessmentPage() {
    const [file, setFile] = useState<File | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [questions, setQuestions] = useState<Question[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<boolean>(false);
    const [cachedFileName, setCachedFileName] = useState<string | null>(null);

    // Load cached data on component mount
    useEffect(() => {
        const loadCachedData = () => {
            try {
                const cached = localStorage.getItem(CACHE_KEY);
                if (cached) {
                    const cachedData: CachedData = JSON.parse(cached);
                    const now = Date.now();

                    // Check if cache is still valid
                    if (now - cachedData.timestamp < CACHE_DURATION && cachedData.questions.length > 0) {
                        setQuestions(cachedData.questions);
                        setCachedFileName(cachedData.fileName);
                        setSuccess(true);
                    } else {
                        // Cache expired, remove it
                        localStorage.removeItem(CACHE_KEY);
                    }
                }
            } catch (error) {
                console.error('Error loading cached data:', error);
                localStorage.removeItem(CACHE_KEY);
            }
        };

        loadCachedData();
    }, []);

    // Save data to cache
    const saveToCache = (questions: Question[], fileName: string) => {
        try {
            const cachedData: CachedData = {
                questions,
                fileName,
                timestamp: Date.now()
            };
            localStorage.setItem(CACHE_KEY, JSON.stringify(cachedData));
        } catch (error) {
            console.error('Error saving to cache:', error);
        }
    };

    // Clear cache
    const clearCache = () => {
        try {
            localStorage.removeItem(CACHE_KEY);
            setCachedFileName(null);
        } catch (error) {
            console.error('Error clearing cache:', error);
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
            setQuestions(data.questions);
            setSuccess(true);

            // Save to cache
            saveToCache(data.questions, file.name);
            setCachedFileName(file.name);
        } catch (err) {
            console.error('Upload error:', err);
            setError(err instanceof Error ? err.message : 'An error occurred while processing the file');
        } finally {
            setIsLoading(false);
        }
    };

    const downloadJSON = () => {
        const dataStr = JSON.stringify({ questions }, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);

        const exportFileDefaultName = `questions_${file?.name?.replace('.pdf', '') || 'generated'}.json`;

        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
    };

    const resetState = () => {
        setFile(null);
        setQuestions([]);
        setError(null);
        setSuccess(false);
        clearCache();
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

                {/* Upload Section */}
                <div className="bg-[#111111] border border-[#333333] rounded-2xl p-8 mb-8">
                    <div className="text-center">
                        <div className="w-32 h-32 mx-auto mb-6 bg-[#222222] border border-[#333333] rounded-full flex items-center justify-center">
                            <Upload className="w-16 h-16 text-blue-400" />
                        </div>

                        <h2 className="text-2xl font-semibold text-white mb-4">Upload PDF Document</h2>
                        <p className="text-gray-400 mb-6">Choose a PDF file (max 5MB) to generate questions from</p>

                        <div className="mb-6">
                            <input
                                type="file"
                                accept=".pdf"
                                onChange={handleFileChange}
                                className="hidden"
                                id="pdf-upload"
                            />
                            <label
                                htmlFor="pdf-upload"
                                className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg cursor-pointer transition-colors"
                            >
                                <FileText className="w-5 h-5" />
                                Select PDF File
                            </label>
                        </div>

                        {file && (
                            <div className="bg-[#222222] border border-blue-600 rounded-lg p-4 mb-6">
                                <div className="flex items-center justify-center gap-2">
                                    <FileText className="w-5 h-5 text-blue-400" />
                                    <span className="text-white font-medium">{file.name}</span>
                                    <span className="text-gray-400 text-sm">({(file.size / 1024 / 1024).toFixed(1)} MB)</span>
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="bg-red-900/30 border border-red-600 rounded-lg p-4 mb-6">
                                <div className="flex items-center justify-center gap-2 text-red-400">
                                    <XCircle className="w-5 h-5" />
                                    <span>{error}</span>
                                </div>
                            </div>
                        )}

                        {success && (
                            <div className="bg-green-900/30 border border-green-600 rounded-lg p-4 mb-6">
                                <div className="flex items-center justify-center gap-2 text-green-400">
                                    <CheckCircle className="w-5 h-5" />
                                    <span>
                                        {cachedFileName
                                            ? `Questions loaded from cache (${cachedFileName})`
                                            : 'Questions generated successfully!'
                                        }
                                    </span>
                                </div>
                            </div>
                        )}

                        <div className="flex gap-4 justify-center">
                            <button
                                onClick={handleUpload}
                                disabled={!file || isLoading}
                                className="inline-flex items-center gap-2 bg-white text-black hover:bg-gray-100 disabled:bg-gray-600 disabled:text-gray-400 disabled:cursor-not-allowed px-8 py-3 rounded-full font-medium transition-colors"
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                        Generating Questions...
                                    </>
                                ) : (
                                    <>
                                        Generate Questions
                                    </>
                                )}
                            </button>

                            {questions.length > 0 && (
                                <button
                                    onClick={resetState}
                                    className="inline-flex items-center gap-2 bg-[#333333] hover:bg-[#444444] text-white px-6 py-3 rounded-full transition-colors"
                                >
                                    Reset
                                </button>
                            )}
                        </div>
                    </div>
                </div>

                {/* Results Section */}
                {questions.length > 0 && (
                    <div className="bg-[#111111] border border-[#333333] rounded-2xl p-8">
                        <div className="flex items-center justify-between mb-8">
                            <div>
                                <h2 className="text-2xl font-semibold text-white">
                                    Generated Questions ({questions.length})
                                </h2>
                                {cachedFileName && (
                                    <p className="text-sm text-gray-400 mt-1">
                                        📦 Loaded from cache • {cachedFileName}
                                    </p>
                                )}
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={downloadJSON}
                                    className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
                                >
                                    <Download className="w-5 h-5" />
                                    Download JSON
                                </button>
                                {cachedFileName && (
                                    <button
                                        onClick={clearCache}
                                        className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded-lg transition-colors text-sm"
                                        title="Clear cached data"
                                    >
                                        Clear Cache
                                    </button>
                                )}
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
                )}

                {/* API Information */}
                <div className="bg-[#111111] border border-[#333333] rounded-lg p-6 mt-8">
                    <h3 className="text-lg font-semibold text-white mb-4">API Information</h3>
                    <div className="bg-[#0a0a0a] border border-[#444444] rounded p-4">
                        <p className="text-sm text-gray-400 mb-2"><strong className="text-gray-300">Endpoint:</strong></p>
                        <code className="text-sm bg-[#222222] text-green-400 px-2 py-1 rounded">POST http://localhost:8001/assessment/generate-questions</code>
                        <p className="text-sm text-gray-400 mt-4 mb-2"><strong className="text-gray-300">cURL Example:</strong></p>
                        <code className="text-xs bg-[#222222] text-gray-300 p-2 rounded block overflow-x-auto">
                            curl -X 'POST' \<br />
                            &nbsp;&nbsp;'http://localhost:8001/assessment/generate-questions' \<br />
                            &nbsp;&nbsp;-H 'accept: application/json' \<br />
                            &nbsp;&nbsp;-H 'Content-Type: multipart/form-data' \<br />
                            &nbsp;&nbsp;-F 'file=@your-document.pdf;type=application/pdf'
                        </code>
                    </div>
                </div>
            </div>
        </div>
    );
}
