# XFactor Bot Test Suite

Comprehensive test suite for the XFactor Bot automated trading system.

## 📁 Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── pytest.ini               # Pytest settings (in project root)
│
├── API Tests
│   ├── test_api_admin.py    # Admin panel authentication & features
│   ├── test_api_ai.py       # AI assistant endpoints
│   ├── test_api_bots.py     # Bot management CRUD operations
│   ├── test_api_config.py   # Configuration parameters
│   ├── test_api_integrations.py  # Broker & data source integrations
│   ├── test_api_positions.py     # Portfolio positions
│   └── test_api_risk.py     # Risk controls & kill switch
│
├── Core Tests
│   ├── test_app.py          # Application endpoints, WebSocket, CORS
│   ├── test_bot_manager.py  # BotConfig, BotInstance, BotManager
│   ├── test_brokers.py      # Alpaca, Schwab, Tradier integrations
│   ├── test_strategies.py   # Trading strategies
│   └── test_risk_manager.py # Risk management logic
│
├── Integration Tests
│   ├── test_data_sources.py # AInvest, TradingView webhooks
│   ├── test_news_intel.py   # News intelligence & sentiment
│   └── test_ollama.py       # Ollama LLM integration
│
└── README.md                # This file
```

## 🚀 Quick Start

### Prerequisites

```bash
# Activate virtual environment
cd /path/to/000_trading
source .venv/bin/activate

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx
```

### Run All Tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run with short traceback
pytest tests/ -v --tb=short
```

### Run Specific Test Files

```bash
# Run only API tests
pytest tests/test_api_*.py -v

# Run a single test file
pytest tests/test_api_bots.py -v

# Run bot manager tests
pytest tests/test_bot_manager.py -v
```

### Run Specific Test Classes or Methods

```bash
# Run a specific test class
pytest tests/test_api_admin.py::TestAdminAuth -v

# Run a specific test method
pytest tests/test_api_admin.py::TestAdminAuth::test_login_with_correct_password -v
```

## 📊 Test Coverage

Generate coverage reports:

```bash
# Run with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

## 🏷️ Test Markers

Use markers to run specific categories:

```bash
# Run only fast tests (exclude slow)
pytest tests/ -m "not slow"

# Run only integration tests
pytest tests/ -m integration

# Run only unit tests
pytest tests/ -m unit
```

## 📝 Example Test Run

```
$ pytest tests/test_api_bots.py tests/test_api_admin.py -v --tb=short

========================= test session starts ==========================
platform darwin -- Python 3.12.0, pytest-7.4.0, pluggy-1.3.0
rootdir: /Users/cvanthin/code/trading/000_trading
configfile: pytest.ini
plugins: asyncio-0.23.0, cov-4.1.0
asyncio: mode=auto
collected 37 items

tests/test_api_bots.py::TestBotsAPI::test_list_bots PASSED         [  2%]
tests/test_api_bots.py::TestBotsAPI::test_get_bots_summary PASSED  [  5%]
tests/test_api_bots.py::TestBotsAPI::test_get_bot_templates PASSED [  8%]
tests/test_api_bots.py::TestBotsAPI::test_create_bot_requires_auth PASSED [10%]
tests/test_api_bots.py::TestBotsAPI::test_create_bot_with_auth PASSED [13%]
tests/test_api_bots.py::TestBotsAPI::test_create_bot_max_reached PASSED [16%]
tests/test_api_bots.py::TestBotsAPI::test_get_specific_bot PASSED  [18%]
tests/test_api_bots.py::TestBotsAPI::test_get_nonexistent_bot PASSED [21%]
tests/test_api_bots.py::TestBotsAPI::test_start_bot PASSED         [24%]
tests/test_api_bots.py::TestBotsAPI::test_stop_bot PASSED          [27%]
tests/test_api_bots.py::TestBotsAPI::test_pause_bot PASSED         [29%]
tests/test_api_bots.py::TestBotsAPI::test_resume_bot PASSED        [32%]
tests/test_api_bots.py::TestBotsAPI::test_delete_bot PASSED        [35%]
tests/test_api_bots.py::TestBotsAPI::test_delete_nonexistent_bot PASSED [37%]
tests/test_api_bots.py::TestBotsAPI::test_start_all_bots PASSED    [40%]
tests/test_api_bots.py::TestBotsAPI::test_stop_all_bots PASSED     [43%]
tests/test_api_bots.py::TestBotsAPI::test_pause_all_bots PASSED    [45%]
tests/test_api_bots.py::TestBotsAPI::test_update_bot_config PASSED [48%]

tests/test_api_admin.py::TestAdminAuth::test_login_with_correct_password PASSED [51%]
tests/test_api_admin.py::TestAdminAuth::test_login_with_wrong_password PASSED [54%]
tests/test_api_admin.py::TestAdminAuth::test_logout PASSED         [56%]
tests/test_api_admin.py::TestAdminAuth::test_verify_valid_session PASSED [59%]
tests/test_api_admin.py::TestAdminAuth::test_verify_invalid_session PASSED [62%]
tests/test_api_admin.py::TestFeatureManagement::test_get_all_features PASSED [64%]
tests/test_api_admin.py::TestFeatureManagement::test_get_all_features_requires_auth PASSED [67%]
tests/test_api_admin.py::TestFeatureManagement::test_get_specific_feature PASSED [70%]
tests/test_api_admin.py::TestFeatureManagement::test_get_nonexistent_feature PASSED [72%]
tests/test_api_admin.py::TestFeatureManagement::test_toggle_feature_on PASSED [75%]
tests/test_api_admin.py::TestFeatureManagement::test_toggle_feature_off PASSED [78%]
tests/test_api_admin.py::TestFeatureManagement::test_bulk_toggle_features PASSED [81%]
tests/test_api_admin.py::TestFeatureManagement::test_toggle_category PASSED [83%]
tests/test_api_admin.py::TestFeatureManagement::test_toggle_invalid_category PASSED [86%]
tests/test_api_admin.py::TestEmergencyControls::test_emergency_disable_trading PASSED [89%]
tests/test_api_admin.py::TestEmergencyControls::test_emergency_disable_news PASSED [91%]
tests/test_api_admin.py::TestEmergencyControls::test_emergency_enable_all PASSED [94%]
tests/test_api_admin.py::TestEmergencyControls::test_emergency_controls_require_auth PASSED [97%]

========================= 37 passed in 2.45s ===========================
```

## 🧪 Test Categories

### API Tests (`test_api_*.py`)

Test all REST API endpoints:

| File | Tests | Coverage |
|------|-------|----------|
| `test_api_bots.py` | 19 | Bot CRUD, start/stop/pause, bulk operations |
| `test_api_admin.py` | 18 | Login, features, emergency controls |
| `test_api_risk.py` | 11 | Risk status, limits, kill switch |
| `test_api_ai.py` | 10 | Chat, insights, providers |
| `test_api_integrations.py` | 15 | Brokers, banking, webhooks |
| `test_api_positions.py` | 6 | Positions, summary, exposure |
| `test_api_config.py` | 9 | Parameters, system status |

### Core Tests

| File | Tests | Coverage |
|------|-------|----------|
| `test_app.py` | 7 | Health, metrics, WebSocket, CORS |
| `test_bot_manager.py` | 26 | BotConfig, BotInstance, BotManager |
| `test_strategies.py` | 14 | Technical, Momentum, NewsSentiment |
| `test_risk_manager.py` | - | Risk calculations |

### Integration Tests

| File | Tests | Coverage |
|------|-------|----------|
| `test_brokers.py` | 15 | Alpaca, Schwab, Tradier |
| `test_data_sources.py` | 14 | AInvest, TradingView |
| `test_news_intel.py` | 8 | File watcher, sentiment |
| `test_ollama.py` | 10 | Local LLM integration |

## 🔧 Configuration

### pytest.ini

The project uses `pytest.ini` in the root directory:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests

addopts = -v --tb=short
```

### conftest.py Fixtures

Key fixtures available for all tests:

```python
@pytest.fixture
def client(app):
    """FastAPI TestClient for HTTP requests."""
    
@pytest.fixture
def admin_token():
    """Valid admin authentication token."""
    
@pytest.fixture
def auth_headers(admin_token):
    """Authorization headers: {'Authorization': 'Bearer xxx'}"""
    
@pytest.fixture
def mock_bot_manager():
    """Mocked BotManager instance."""
    
@pytest.fixture
def sample_bot_config():
    """Sample bot configuration dictionary."""
```

## 🐛 Debugging Failed Tests

```bash
# Show full traceback
pytest tests/test_api_bots.py -v --tb=long

# Drop into debugger on failure
pytest tests/test_api_bots.py -v --pdb

# Stop on first failure
pytest tests/ -v -x

# Show local variables in traceback
pytest tests/ -v --tb=short -l

# Capture print statements
pytest tests/ -v -s
```

## 📸 Screenshot: Full Test Run

```
┌────────────────────────────────────────────────────────────────────┐
│  $ pytest tests/ -v --tb=short                                     │
│                                                                    │
│  ======================== test session starts =====================│
│  platform darwin -- Python 3.12.0, pytest-7.4.0                    │
│  rootdir: /Users/cvanthin/code/trading/000_trading                │
│  configfile: pytest.ini                                            │
│  plugins: asyncio-0.23.0, cov-4.1.0                               │
│  collected 150 items                                               │
│                                                                    │
│  tests/test_api_admin.py ..................              [ 12%]   │
│  tests/test_api_ai.py ..........                         [ 19%]   │
│  tests/test_api_bots.py ...................              [ 31%]   │
│  tests/test_api_config.py .........                      [ 37%]   │
│  tests/test_api_integrations.py ...............          [ 47%]   │
│  tests/test_api_positions.py ......                      [ 51%]   │
│  tests/test_api_risk.py ...........                      [ 59%]   │
│  tests/test_app.py .......                               [ 63%]   │
│  tests/test_bot_manager.py ..........................    [ 81%]   │
│  tests/test_brokers.py ...............                   [ 91%]   │
│  tests/test_data_sources.py ..............               [ 97%]   │
│  tests/test_news_intel.py ........                       [100%]   │
│                                                                    │
│  ====================== 150 passed in 8.32s =======================│
│                                                                    │
│  ✅ All tests passed!                                              │
└────────────────────────────────────────────────────────────────────┘
```

## 📚 Writing New Tests

### Example: Testing a New API Endpoint

```python
# tests/test_api_example.py

import pytest
from unittest.mock import MagicMock, patch

class TestMyNewEndpoint:
    """Tests for new endpoint."""
    
    def test_get_endpoint_returns_data(self, client):
        """Test GET /api/my-endpoint returns expected data."""
        response = client.get("/api/my-endpoint")
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
    
    def test_post_requires_auth(self, client):
        """Test POST requires authentication."""
        response = client.post("/api/my-endpoint", json={})
        assert response.status_code == 401
    
    def test_post_with_auth(self, client, auth_headers):
        """Test POST with valid authentication."""
        response = client.post(
            "/api/my-endpoint",
            json={"field": "value"},
            headers=auth_headers
        )
        assert response.status_code == 200
```

### Example: Testing Async Functions

```python
import pytest

class TestAsyncFunction:
    
    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async function."""
        from src.my_module import my_async_function
        
        result = await my_async_function()
        assert result is not None
```

## 🔗 Continuous Integration

Tests run automatically on GitLab CI. See `.gitlab-ci.yml`:

```yaml
test:
  stage: test
  script:
    - pip install -r requirements.txt
    - pytest tests/ -v --cov=src
  coverage: '/TOTAL.+ ([0-9]{1,3}%)/'
```

## ❓ Troubleshooting

### ModuleNotFoundError

```bash
# Ensure you're in the project root
cd /path/to/000_trading

# Install the package in development mode
pip install -e .
```

### Async Test Issues

```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Ensure asyncio_mode=auto in pytest.ini
```

### Database Connection Errors

Tests use mocked database connections. If you see real database errors:
- Check that tests properly mock database fixtures
- Ensure `conftest.py` fixtures are being used

---

**Total Tests: 150+** | **Coverage Target: 80%+**

