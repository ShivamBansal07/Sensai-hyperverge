## 🎯 **MVP4 Step-by-Step Implementation Plan**

### **Phase 1: Backend Data Architecture (2-3 days)**

**1.1 Enhanced Models & Confidence Scoring**
```python
# New models for sophisticated integrity analysis
class IntegrityEvent(BaseModel):
    event_id: str
    event_type: Literal["PASTE_DETECTED", "UNUSUAL_TIMING", "TAB_SWITCH", "MULTIPLE_ATTEMPTS"]
    timestamp: datetime
    confidence_score: float  # 0.0-1.0 risk assessment
    severity_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    evidence: dict
    analysis_notes: Optional[str]

class SessionIntegrityProfile(BaseModel):
    session_id: str
    overall_integrity_score: float  # Weighted average
    total_events: int
    high_risk_events: int
    medium_risk_events: int
    low_risk_events: int
    timeline_summary: List[IntegrityEvent]
    behavioral_patterns: dict
```

**1.2 Confidence Scoring Algorithm**
```python
class IntegrityAnalyzer:
    def calculate_confidence_score(self, event_type: str, payload: dict) -> tuple[float, str]:
        confidence_mapping = {
            "PASTE_DETECTED": (0.85, "HIGH"),  # Strong indicator of cheating
            "UNUSUAL_TIMING": self._analyze_timing_pattern(payload),
            "TAB_SWITCH": (0.6, "MEDIUM"),  # Could be legitimate multitasking
            "MULTIPLE_ATTEMPTS": (0.7, "MEDIUM")
        }
        return confidence_mapping.get(event_type, (0.3, "LOW"))
    
    def _analyze_timing_pattern(self, payload: dict) -> tuple[float, str]:
        time_taken = payload.get("time_taken_ms", 0)
        question_complexity = payload.get("expected_time_ms", 10000)
        
        ratio = time_taken / question_complexity
        if ratio < 0.1:  # Answered in <10% expected time
            return (0.9, "HIGH")
        elif ratio < 0.3:
            return (0.7, "MEDIUM")
        else:
            return (0.4, "LOW")
```

### **Phase 2: Advanced Evidence Processing (2-3 days)**

**2.1 Multi-dimensional Evidence Collection**
```python
class EvidenceProcessor:
    def process_paste_evidence(self, event_data: dict) -> dict:
        return {
            "evidence_type": "PASTE_CONTENT_ANALYSIS",
            "pasted_text_length": len(event_data.get("pasted_text", "")),
            "similarity_to_correct_answer": self._calculate_similarity(
                event_data.get("pasted_text", ""), 
                event_data.get("correct_answer", "")
            ),
            "contains_external_formatting": self._detect_external_formatting(
                event_data.get("pasted_text", "")
            ),
            "timestamp_analysis": self._analyze_paste_timing(event_data)
        }
    
    def process_timing_evidence(self, event_data: dict) -> dict:
        return {
            "evidence_type": "TIMING_BEHAVIORAL_PATTERN",
            "response_time_ms": event_data.get("time_taken_ms"),
            "question_complexity_score": self._assess_question_complexity(event_data),
            "historical_timing_comparison": self._compare_with_user_history(event_data),
            "deviation_from_expected": self._calculate_timing_deviation(event_data)
        }
```

**2.2 Pattern Recognition Engine**
```python
class BehavioralPatternAnalyzer:
    def analyze_session_patterns(self, events: List[IntegrityEvent]) -> dict:
        return {
            "suspicious_timing_clusters": self._detect_timing_clusters(events),
            "paste_frequency_analysis": self._analyze_paste_frequency(events),
            "tab_switching_patterns": self._analyze_focus_patterns(events),
            "overall_behavioral_consistency": self._assess_consistency(events),
            "risk_escalation_timeline": self._track_risk_escalation(events)
        }
```

### **Phase 3: Frontend Dashboard Components (3-4 days)**

**3.1 Comprehensive Dashboard Architecture**
```typescript
// Main Dashboard Container
const ReviewerTimeline: React.FC<{sessionId: string}> = ({sessionId}) => {
    const [integrityProfile, setIntegrityProfile] = useState<SessionIntegrityProfile | null>(null);
    const [selectedEvent, setSelectedEvent] = useState<IntegrityEvent | null>(null);
    const [viewMode, setViewMode] = useState<'timeline' | 'heatmap' | 'details'>('timeline');
    
    return (
        <div className="reviewer-dashboard">
            <SessionSummaryCard profile={integrityProfile} />
            <ViewModeSelector currentMode={viewMode} onModeChange={setViewMode} />
            
            {viewMode === 'timeline' && (
                <InteractiveTimeline 
                    events={integrityProfile?.timeline_summary || []}
                    onEventSelect={setSelectedEvent}
                />
            )}
            
            {viewMode === 'heatmap' && (
                <IntegrityHeatmap events={integrityProfile?.timeline_summary || []} />
            )}
            
            {selectedEvent && (
                <EventDetailsSidebar 
                    event={selectedEvent}
                    onClose={() => setSelectedEvent(null)}
                />
            )}
        </div>
    );
};
```

**3.2 Advanced UI Components**
```typescript
// Interactive Timeline with Risk Visualization
const InteractiveTimeline: React.FC = ({events, onEventSelect}) => {
    return (
        <div className="timeline-container">
            {events.map(event => (
                <TimelineEvent 
                    key={event.event_id}
                    event={event}
                    onClick={() => onEventSelect(event)}
                    riskLevel={event.severity_level}
                    confidenceScore={event.confidence_score}
                />
            ))}
        </div>
    );
};

// Risk-based Color Coding Component
const ConfidenceIndicator: React.FC<{score: number}> = ({score}) => {
    const getRiskColor = (score: number) => {
        if (score >= 0.8) return 'bg-red-500';      // High risk
        if (score >= 0.6) return 'bg-yellow-500';   // Medium risk
        if (score >= 0.4) return 'bg-orange-500';   // Low-medium risk
        return 'bg-green-500';                      // Low risk
    };
    
    return (
        <div className={`confidence-badge ${getRiskColor(score)}`}>
            {(score * 100).toFixed(0)}% confidence
        </div>
    );
};
```

### **Phase 4: Evidence Rendering System (2-3 days)**

**4.1 Multi-format Evidence Display**
```typescript
const EvidenceRenderer: React.FC<{evidence: any}> = ({evidence}) => {
    switch(evidence.evidence_type) {
        case 'PASTE_CONTENT_ANALYSIS':
            return <PasteEvidenceView evidence={evidence} />;
        case 'TIMING_BEHAVIORAL_PATTERN':
            return <TimingAnalysisView evidence={evidence} />;
        case 'TAB_FOCUS_PATTERN':
            return <FocusPatternView evidence={evidence} />;
        default:
            return <GenericEvidenceView evidence={evidence} />;
    }
};

const PasteEvidenceView: React.FC = ({evidence}) => (
    <div className="evidence-panel">
        <h3>Paste Detection Analysis</h3>
        <div className="evidence-metrics">
            <MetricCard 
                label="Similarity to Correct Answer" 
                value={`${evidence.similarity_to_correct_answer}%`}
                risk={evidence.similarity_to_correct_answer > 80 ? 'high' : 'medium'}
            />
            <MetricCard 
                label="External Formatting Detected" 
                value={evidence.contains_external_formatting ? 'Yes' : 'No'}
                risk={evidence.contains_external_formatting ? 'high' : 'low'}
            />
        </div>
        <div className="paste-content-preview">
            <pre>{evidence.pasted_text_preview}</pre>
        </div>
    </div>
);
```

### **Phase 5: Advanced Analytics & Reporting (2-3 days)**

**5.1 Statistical Analysis Engine**
```python
class SessionAnalytics:
    def generate_integrity_report(self, session_id: str) -> dict:
        events = self._get_session_events(session_id)
        
        return {
            "executive_summary": self._create_executive_summary(events),
            "risk_assessment": self._calculate_overall_risk(events),
            "behavioral_analysis": self._analyze_behavioral_patterns(events),
            "evidence_strength": self._assess_evidence_quality(events),
            "recommendations": self._generate_recommendations(events),
            "detailed_timeline": self._create_detailed_timeline(events)
        }
    
    def _calculate_overall_risk(self, events: List[IntegrityEvent]) -> dict:
        high_risk_count = len([e for e in events if e.severity_level == "HIGH"])
        total_events = len(events)
        
        return {
            "overall_risk_score": self._weighted_risk_calculation(events),
            "risk_category": self._categorize_risk_level(events),
            "confidence_in_assessment": self._calculate_assessment_confidence(events)
        }
```

**5.2 Comparative Analysis Dashboard**
```typescript
const ComparativeAnalysisView: React.FC = ({sessionId, cohortData}) => {
    return (
        <div className="comparative-dashboard">
            <SessionVsCohortChart 
                sessionData={sessionData}
                cohortAverages={cohortData}
            />
            <BehavioralDeviationMetrics 
                userPatterns={userBehavior}
                normalPatterns={cohortBehavior}
            />
            <RiskDistributionChart 
                sessionEvents={events}
                cohortDistribution={cohortRiskDistribution}
            />
        </div>
    );
};
```
