# 🧪 SAQ Evaluation Test Suite

## Overview

This comprehensive test suite validates the enhanced SAQ (Short Answer Question) evaluation system with multi-step LLM processing, semantic analysis, and dynamic feedback generation.

## 🚀 Quick Start

### Windows

```bash
# Run all checkpoints
test_runner.bat

# Run specific checkpoint
test_runner.bat phase_1_models
test_runner.bat phase_3_api
test_runner.bat full_integration
```

### Manual Execution

```bash
# Initialize environment
cd sensai-ai
venv\Scripts\activate
pip install pytest pytest-asyncio pytest-json-report requests psutil

# Run specific test phase
python run_checkpoint_tests.py phase_1_models

# Run all tests
python run_checkpoint_tests.py
```

## 📋 Test Phases

### Phase 1: Backend Models
- **File**: `TestSAQModels`
- **Tests**: Pydantic model validation
- **Backend Required**: No
- **Duration**: ~30 seconds

### Phase 1: Service Layer
- **File**: `TestSAQEvaluatorService`
- **Tests**: SAQ evaluator service functionality
- **Backend Required**: Yes
- **Duration**: ~2 minutes

### Phase 3: API Enhancement
- **File**: `TestAPIEndpointEnhancement`
- **Tests**: Enhanced quiz/answer endpoint
- **Backend Required**: Yes
- **Duration**: ~3 minutes

### Full Integration
- **File**: `TestIntegrationFlow`
- **Tests**: Complete end-to-end flow
- **Backend Required**: Yes
- **Duration**: ~5 minutes

## 📁 Directory Structure

```
tests/
├── logs/                          # Test execution logs
│   └── checkpoint_runner_*.log    # Timestamped logs
├── reports/                       # Test reports
│   └── *_report_*.json           # Detailed test results
├── data/                         # Test data
│   └── test_scenarios.json      # Sample questions & answers
├── test_saq_evaluation_integration.py  # Main test file
├── test_utils.py                # Testing utilities
└── run_checkpoint_tests.py     # Test runner script
```

## 🔧 Features

### ✅ Automated Backend Management
- Starts/stops backend server automatically
- Health checks and graceful shutdown
- Virtual environment activation
- Dependency installation

### ✅ Comprehensive Logging
- Timestamped execution logs
- Detailed error tracking
- Progress monitoring
- JSON-formatted reports

### ✅ Test Categories
1. **Model Validation**: Pydantic schema validation
2. **Service Testing**: LLM service mocking and testing
3. **API Testing**: Endpoint enhancement validation
4. **Integration Testing**: End-to-end flow validation
5. **Error Handling**: Fallback and recovery testing

### ✅ Mock LLM Responses
- Semantic evaluation simulation
- Dynamic feedback generation
- Error condition testing
- Performance validation

## 📊 Test Reports

### Console Output
```
🧪 SAQ Evaluation Test Runner
============================
✅ Found virtual environment
🔧 Activating virtual environment...
✅ Virtual environment activated
📦 Installing/updating test dependencies...
✅ Test dependencies ready
🧪 Running tests...
[2025-08-08 10:30:15] [CHECKPOINT] 🎯 Running checkpoint: phase_1_models
[2025-08-08 10:30:16] [SUCCESS] ✅ SemanticEvaluationResult model validation passed
✅ All tests passed!
```

### JSON Reports
```json
{
  "checkpoint": "phase_1_models",
  "timestamp": "2025-08-08T10:30:15",
  "test_results": {
    "passed": 3,
    "failed": 0,
    "return_code": 0
  },
  "success": true
}
```

## 🎯 Usage Examples

### Development Workflow
1. Make code changes
2. Run relevant checkpoint: `test_runner.bat phase_1_models`
3. Check logs in `tests/logs/` if issues
4. Fix issues and re-run

### CI/CD Integration
```yaml
- name: Run SAQ Tests
  run: |
    cd sensai-ai
    python run_checkpoint_tests.py
```

### Debugging Failed Tests
1. Check latest log file in `tests/logs/`
2. Review detailed JSON report in `tests/reports/`
3. Run specific test with verbose output:
   ```bash
   python -m pytest tests/test_saq_evaluation_integration.py::TestSAQModels::test_semantic_evaluation_result_valid -v
   ```

## 🔍 Test Data

Sample test scenarios in `tests/data/test_scenarios.json`:
- Valid/invalid model data
- Progressive answer improvements
- Error conditions
- Expected LLM response patterns

## 📈 Performance Metrics

- **Model Tests**: < 1 second
- **Service Tests**: < 30 seconds (with mocking)
- **API Tests**: < 60 seconds (with backend)
- **Integration Tests**: < 120 seconds (full flow)

## 🛠️ Troubleshooting

### Common Issues

**Backend won't start**
- Check virtual environment activation
- Verify uvicorn installation: `pip install uvicorn`
- Check port 8001 availability

**Import errors**
- Ensure in sensai-ai directory
- Activate virtual environment
- Install dependencies: `pip install -r requirements.txt`

**Test timeouts**
- Increase timeout in `run_checkpoint_tests.py`
- Check backend health manually: `curl http://localhost:8001/health`

**LLM service errors**
- Tests use mocking by default
- Check OpenAI API key if testing real LLM calls
- Review mock configurations in test files

## 📝 Adding New Tests

1. Add test method to appropriate class in `test_saq_evaluation_integration.py`
2. Update test phases in `run_checkpoint_tests.py` if needed
3. Add test data to `test_scenarios.json`
4. Run new test: `test_runner.bat your_checkpoint_name`

## 🎉 Success Criteria

All tests passing indicates:
- ✅ Models validate correctly
- ✅ SAQ evaluator service works
- ✅ API endpoints enhanced properly
- ✅ Integration flow complete
- ✅ Error handling robust
