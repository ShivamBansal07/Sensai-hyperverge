import React from 'react';

interface IntegrityLog {
    session_id: string;
    event_type: string;
    timestamp: number;
    payload?: Record<string, any>;
}

interface ReviewerTimelineProps {
    logs: IntegrityLog[];
}

const ReviewerTimeline: React.FC<ReviewerTimelineProps> = ({ logs }) => {
    return (
        <div className="bg-[#111111] border border-[#333333] rounded-2xl p-6 text-white h-full overflow-y-auto">
            <h2 className="text-2xl font-semibold mb-4">Quiz Session Timeline</h2>
            <div className="space-y-4">
                {logs.length === 0 ? (
                    <p className="text-gray-500 text-center">No integrity events logged yet.</p>
                ) : (
                    logs.map((log, index) => (
                        <div key={index} className="flex items-start gap-3">
                            <div className="w-3 h-3 bg-blue-500 rounded-full flex-shrink-0 mt-2"></div>
                            <div>
                                <p className="text-sm text-gray-400">
                                    {new Date(log.timestamp).toLocaleString()}
                                </p>
                                <p className="font-medium">{log.event_type.replace(/_/g, ' ')}</p>
                                {log.payload && Object.keys(log.payload).length > 0 && (
                                    <p className="text-xs text-gray-500 mt-1">
                                        Details: {JSON.stringify(log.payload)}
                                    </p>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default ReviewerTimeline;
