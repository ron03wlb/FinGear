# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FinGear is a Taiwan stock quantitative analysis system with a **no-database architecture** using Apache Parquet for storage. The system implements a three-layer stock screening pipeline combining fundamental, chip (institutional trading), and technical analysis.

## Core Architecture

### Data Flow & Storage Strategy

The system uses a **dual-partition strategy** for Parquet files:

1. **Time Partition** (`/data/daily/date=YYYY-MM-DD/`): For cross-sectional analysis
   - Written first during daily updates (15:00)
   - Contains all stocks' OHLCV data for a specific date

2. **Symbol Partition** (`/data/history/symbol=XXXX/`): For time-series analysis
   - Transposed from time partitions via ETL pipeline
   - Contains complete historical data for individual stocks
   - Used by factor calculations and technical indicators

### Three-Layer Screening Pipeline

The `StockScreener` (Pipeline Pattern) processes stocks through:

1. **Layer 1 - Fundamental**: `FactorEngine` calculates 7 weighted factors → Top 30 from Top 500
   - **Factor Weights** (configured in `config/parameters.yaml`):
     - PE Relative: **30%** (emphasizes valuation)
     - ROE: 15%, EPS YoY: 15%
     - FCF: 10%, Gross Margin Trend: 10%, Revenue YoY: 10%, Debt Ratio: 10%
   - Score range: 40-200 points

2. **Layer 2 - Chips**: Multi-factor scoring system (0-100 points)
   - Institutional consecutive buying days (30%)
   - Foreign investor position (25%)
   - Dealer activity (15%)
   - Total institutional strength (20%)
   - Major holder trend (10%)
   - Pass threshold: ≥ 60 points

3. **Layer 3 - Technical**: Multi-factor scoring system (0-100 points)
   - MA trend (25%), MACD momentum (20%), RSI (15%), KD (15%), Volume (15%), Bollinger Bands (10%)
   - Signals: STRONG_BUY (≥65), BUY (50-64), WATCH (35-49), HOLD/REDUCE (<35)

### Design Patterns in Use

- **Singleton**: `ShioajiClient` ensures single API connection
- **Repository**: `ParquetManager` abstracts data access
- **Strategy**: `FactorEngine` allows pluggable factor calculations
- **Pipeline**: `StockScreener` chains three filtering stages
- **Observer**: `NotificationService` for Line/Telegram notifications

## Development Commands

### Environment Setup
```bash
python -m venv fingear_env
# Windows
fingear_env\Scripts\activate
# macOS/Linux
source fingear_env/bin/activate

pip install -r requirements.txt
```

### Configuration
Before running, configure API credentials:
```bash
cp config/api_keys.example.json config/api_keys.json
# Edit config/api_keys.json with Shioaji API keys
```

Strategy parameters are in `config/parameters.yaml` (factor weights, thresholds, schedules).

### Running Scripts

**Daily data update** (scheduled 15:00):
```bash
python scripts/update_data.py
```

**Stock screening** (scheduled 16:00):
```bash
python scripts/run_strategy.py
```

**Backtesting**:
```bash
python scripts/backtest.py
```

### Testing

**Run all tests**:
```bash
pytest
```

**Run specific test file**:
```bash
pytest tests/test_factors.py
```

**Run specific test**:
```bash
pytest tests/test_factors.py::TestFactorEngine::test_calculate_roe_正常情況
```

**With coverage**:
```bash
pytest --cov=src --cov-report=html
```

**Test fixtures** are defined in `tests/conftest.py`:
- `mock_data_manager`: Mocked ParquetManager with sample financial data
- `sample_price_data`: 100-day OHLCV data for testing

### Docker Deployment
```bash
docker-compose up -d
```

Cron jobs (defined in `crontab`):
- 15:00 Mon-Fri: Data update
- 16:00 Mon-Fri: Strategy execution
- 02:00 Sunday: Log cleanup (30+ days)

## Python Implementation Standards

### Code Quality Requirements

**Type Hints** (MANDATORY):
```python
# ✅ CORRECT - Full type annotations
def calculate_factor(
    symbol: str,
    data: pd.DataFrame,
    weight: float = 1.0
) -> dict[str, float]:
    """Calculate weighted factor score."""
    pass

# ❌ WRONG - Missing type hints
def calculate_factor(symbol, data, weight=1.0):
    pass
```

**Docstrings** (MANDATORY for all public functions/classes):
```python
def screen_stocks(
    fundamental_top_n: int,
    chip_threshold: float
) -> list[str]:
    """
    Execute three-layer stock screening pipeline.
    
    Args:
        fundamental_top_n: Number of stocks to select in Layer 1
        chip_threshold: Minimum institutional buy ratio for Layer 2
        
    Returns:
        List of stock symbols that pass all three layers
        
    Raises:
        ValueError: If fundamental_top_n < 1 or chip_threshold not in [0, 1]
        DataNotFoundError: If required date partition is missing
        
    Example:
        >>> screener = StockScreener()
        >>> symbols = screener.screen_stocks(30, 0.05)
        >>> print(f"Selected {len(symbols)} stocks")
    """
    pass
```

**Naming Conventions**:
- **Classes**: `PascalCase` (e.g., `FactorEngine`, `ParquetManager`)
- **Functions/Variables**: `snake_case` (e.g., `calculate_roe`, `max_retries`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_WORKERS`, `DEFAULT_TIMEOUT`)
- **Private members**: Prefix with `_` (e.g., `_validate_data`, `_cache`)
- **Avoid single-letter names** except for iterators (`i`, `j`) and standard math variables (`x`, `y`)

**Code Organization** (within each `.py` file):
```python
"""Module docstring."""

# 1. Standard library imports
import os
from datetime import datetime
from typing import Optional

# 2. Third-party imports
import pandas as pd
import numpy as np

# 3. Local imports
from src.utils import logger
from src.parquet_manager import ParquetManager

# 4. Constants
MAX_RETRIES = 3
DEFAULT_CACHE_TTL = 3600

# 5. Classes/Functions (ordered by dependency)
class MyClass:
    pass

def helper_function():
    pass
```

### Error Handling Standards

**Exception Handling** (MANDATORY):
```python
# ✅ CORRECT - Specific exceptions with context
def load_price_data(symbol: str, date: str) -> pd.DataFrame:
    """Load price data with comprehensive error handling."""
    try:
        df = self.parquet_manager.read_by_symbol(symbol, date)
    except FileNotFoundError:
        logger.error(f"Price data not found: {symbol} on {date}")
        raise DataNotFoundError(f"No data for {symbol} on {date}")
    except pa.ArrowInvalid as e:
        logger.error(f"Parquet file corrupted: {symbol}/{date}: {e}")
        raise DataCorruptionError(f"Invalid parquet for {symbol}")
    except Exception as e:
        logger.error(f"Unexpected error loading {symbol}: {e}", exc_info=True)
        raise
    
    # Validate data before returning
    if df.empty:
        raise ValueError(f"Empty DataFrame for {symbol} on {date}")
    
    return df

# ❌ WRONG - Bare except or generic exceptions
def load_price_data(symbol, date):
    try:
        df = self.parquet_manager.read_by_symbol(symbol, date)
    except:  # Never use bare except!
        return None  # Silent failure - debugging nightmare!
```

**Logging Requirements**:
```python
import logging
from src.utils import logger

# Use appropriate log levels:
logger.debug(f"Cache hit for {symbol}_fundamental_{date}")  # Verbose details
logger.info(f"Screening completed: {len(results)} stocks selected")  # Key events
logger.warning(f"Missing chip data for {symbol}, skipping Layer 2")  # Recoverable issues
logger.error(f"Failed to fetch {symbol}: {e}", exc_info=True)  # Errors with stack trace
logger.critical(f"Database connection lost, terminating")  # System failures

# Include context in logs:
logger.info(f"Factor calculation", extra={
    'symbol': symbol,
    'date': date,
    'duration_ms': elapsed_time * 1000
})
```

**Custom Exceptions** (already defined in `src/utils/exceptions.py`):
```python
# Use project-specific exceptions for clarity
from src.utils.exceptions import (
    DataNotFoundError,      # Missing parquet partitions
    DataCorruptionError,    # Invalid/corrupted files
    APIConnectionError,     # Shioaji API failures
    RateLimitExceeded,      # API quota exceeded
    ValidationError         # Data schema violations
)
```

### Data Validation Standards

**Input Validation** (MANDATORY for all public methods):
```python
def calculate_roc(prices: pd.Series, period: int = 5) -> pd.Series:
    """
    Calculate Rate of Change.
    
    Args:
        prices: Price series (must have datetime index)
        period: Lookback period (must be >= 1)
    """
    # 1. Validate types
    if not isinstance(prices, pd.Series):
        raise TypeError(f"Expected Series, got {type(prices)}")
    
    # 2. Validate ranges
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    
    # 3. Validate data integrity
    if prices.empty:
        raise ValueError("Cannot calculate ROC on empty series")
    
    if not isinstance(prices.index, pd.DatetimeIndex):
        raise ValidationError("prices must have DatetimeIndex")
    
    if prices.isna().any():
        logger.warning(f"NaN values detected in prices, filling forward")
        prices = prices.ffill()
    
    # 4. Perform calculation
    return (prices / prices.shift(period) - 1) * 100
```

**DataFrame Schema Validation**:
```python
def validate_price_schema(df: pd.DataFrame) -> None:
    """Validate price data schema before processing."""
    required_columns = {'date', 'open', 'high', 'low', 'close', 'volume'}
    missing = required_columns - set(df.columns)
    
    if missing:
        raise ValidationError(f"Missing columns: {missing}")
    
    # Check data types
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        raise ValidationError(f"'date' must be datetime, got {df['date'].dtype}")
    
    for col in ['open', 'high', 'low', 'close']:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValidationError(f"'{col}' must be numeric, got {df[col].dtype}")
    
    # Check value ranges
    if (df['high'] < df['low']).any():
        raise ValidationError("High price cannot be lower than low price")
    
    if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
        raise ValidationError("Prices must be positive")
```

### Testing Requirements

**Test Coverage** (MANDATORY):
- **Minimum 80% coverage** for all modules in `src/`
- **100% coverage required** for critical modules: `factors.py`, `screener.py`, `parquet_manager.py`

**Test Structure** (use pytest):
```python
# tests/test_factors.py
import pytest
import pandas as pd
from src.factors import FactorEngine

class TestFactorEngine:
    """Test suite for FactorEngine."""
    
    @pytest.fixture
    def engine(self, mock_parquet_manager):
        """Initialize FactorEngine with mocked data."""
        return FactorEngine(data_manager=mock_parquet_manager)
    
    @pytest.fixture
    def sample_financial_data(self):
        """Create valid financial data for testing."""
        return pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=4, freq='Q'),
            'net_income': [100, 120, 130, 140],
            'equity': [1000, 1050, 1100, 1150]
        })
    
    def test_calculate_roe_正常情況(self, engine, sample_financial_data):
        """Test ROE calculation with valid data."""
        result = engine.calculate_roe('2330', sample_financial_data)
        
        # Expected ROE = 140 / 1150 = 0.1217
        assert result == pytest.approx(0.1217, abs=0.0001)
        assert 0 <= result <= 1  # Sanity check
    
    def test_calculate_roe_缺少欄位(self, engine):
        """Test ROE raises error when columns missing."""
        invalid_data = pd.DataFrame({'revenue': [100, 200]})
        
        with pytest.raises(ValidationError, match="Missing columns"):
            engine.calculate_roe('2330', invalid_data)
    
    def test_calculate_roe_負數股本(self, engine):
        """Test ROE handles negative equity."""
        data = pd.DataFrame({
            'net_income': [100],
            'equity': [-500]  # Invalid
        })
        
        with pytest.raises(ValueError, match="equity must be positive"):
            engine.calculate_roe('2330', data)
    
    @pytest.mark.parametrize("net_income,equity,expected", [
        (100, 1000, 0.10),
        (0, 1000, 0.00),
        (50, 500, 0.10),
    ])
    def test_calculate_roe_多種場景(self, engine, net_income, equity, expected):
        """Test ROE calculation with various inputs."""
        data = pd.DataFrame({
            'net_income': [net_income],
            'equity': [equity]
        })
        result = engine.calculate_roe('2330', data)
        assert result == pytest.approx(expected, abs=0.01)
```

**Mock Usage** (fixtures in `tests/conftest.py`):
```python
import pytest
from unittest.mock import Mock, MagicMock

@pytest.fixture
def mock_parquet_manager():
    """Mock ParquetManager to avoid file I/O in tests."""
    manager = Mock()
    manager.read_by_symbol.return_value = pd.DataFrame({
        'date': pd.date_range('2023-01-01', periods=100),
        'close': np.random.uniform(100, 200, 100)
    })
    return manager

@pytest.fixture
def mock_shioaji_client():
    """Mock Shioaji API client."""
    client = Mock()
    client.fetch_quotes.return_value = [...]
    client.is_connected.return_value = True
    return client
```

### Implementation Workflow

**Step-by-Step Process** (MUST FOLLOW IN ORDER):

**1. Planning Phase**:
   - [ ] Read relevant documentation in `docs/Implementation.md`
   - [ ] Identify affected modules and dependencies
   - [ ] Check module import order (see Module Dependencies section)
   - [ ] Design function signatures with full type hints
   - [ ] Plan test cases (normal, edge, error scenarios)

**2. Implementation Phase**:
   - [ ] Create/update function with docstring and type hints
   - [ ] Implement input validation first
   - [ ] Add logging statements (debug/info level)
   - [ ] Implement core logic
   - [ ] Add error handling with specific exceptions
   - [ ] Add result validation before returning

**3. Testing Phase**:
   - [ ] Write unit tests covering:
     - Normal cases (typical inputs)
     - Edge cases (empty data, boundary values)
     - Error cases (invalid inputs, missing data)
   - [ ] Run tests: `pytest tests/test_<module>.py -v`
   - [ ] Check coverage: `pytest --cov=src.<module> --cov-report=term-missing`
   - [ ] Ensure minimum 80% coverage (100% for critical modules)

**4. Integration Phase**:
   - [ ] Run full test suite: `pytest`
   - [ ] Test with real data if possible (use `scripts/run_strategy.py`)
   - [ ] Check log output for warnings/errors
   - [ ] Verify performance (no regression)

**5. Documentation Phase**:
   - [ ] Update docstrings if behavior changed
   - [ ] Update `CLAUDE.md` if new patterns introduced
   - [ ] Add inline comments for complex logic only

### Common Pitfalls and Solutions

**❌ AVOID: Modifying DataFrames In-Place**
```python
# WRONG - Modifies original DataFrame
def add_ma(df):
    df['ma5'] = df['close'].rolling(5).mean()
    return df

# CORRECT - Return new DataFrame
def add_ma(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(ma5=df['close'].rolling(5).mean())
```

**❌ AVOID: Chained Indexing**
```python
# WRONG - May trigger SettingWithCopyWarning
df[df['volume'] > 1000]['signal'] = 'BUY'

# CORRECT - Use .loc
df.loc[df['volume'] > 1000, 'signal'] = 'BUY'
```

**❌ AVOID: Ignoring NaN Values**
```python
# WRONG - Silently produces NaN results
def calculate_return(prices):
    return (prices[-1] / prices[0]) - 1

# CORRECT - Handle NaN explicitly
def calculate_return(prices: pd.Series) -> float:
    """Calculate total return, handling missing values."""
    clean_prices = prices.dropna()
    if len(clean_prices) < 2:
        raise ValueError("Insufficient data for return calculation")
    return (clean_prices.iloc[-1] / clean_prices.iloc[0]) - 1
```

**❌ AVOID: Hardcoded Paths/Dates**
```python
# WRONG
df = pd.read_parquet('C:/data/2024-01-01/prices.parquet')

# CORRECT - Use configuration and parameters
from src.config import DATA_DIR
def load_prices(date: str) -> pd.DataFrame:
    path = DATA_DIR / 'daily' / f'date={date}' / 'prices.parquet'
    return pd.read_parquet(path)
```

**❌ AVOID: Silent Failures**
```python
# WRONG - Returns None on error
def get_stock_info(symbol):
    try:
        return api.fetch(symbol)
    except:
        return None  # Caller has no idea what went wrong

# CORRECT - Let exceptions propagate or raise custom ones
def get_stock_info(symbol: str) -> dict:
    """Fetch stock info from API."""
    try:
        return self.api.fetch(symbol)
    except ConnectionError as e:
        raise APIConnectionError(f"Failed to fetch {symbol}: {e}")
```

### Performance Guidelines

**Vectorization** (MANDATORY for DataFrame operations):
```python
# ❌ SLOW - Row iteration
for idx, row in df.iterrows():
    df.at[idx, 'return'] = (row['close'] / row['open']) - 1

# ✅ FAST - Vectorized operation
df['return'] = (df['close'] / df['open']) - 1
```

**Caching** (use for expensive calculations):
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def calculate_factor(symbol: str, date: str) -> float:
    """Cache factor results by (symbol, date) key."""
    # Expensive calculation here
    pass
```

**Parquet Optimization**:
```python
# Use predicate pushdown to read only required data
dataset = pq.ParquetDataset(
    path,
    filters=[
        ('date', '>=', start_date),
        ('date', '<=', end_date)
    ]
)

# Read only required columns
df = dataset.read(columns=['symbol', 'close', 'volume']).to_pandas()
```

**Parallel Processing** (for independent operations):
```python
from concurrent.futures import ThreadPoolExecutor
from src.config import MAX_WORKERS

def process_symbols_parallel(symbols: list[str]) -> list[dict]:
    """Process multiple symbols concurrently."""
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_symbol, s): s for s in symbols}
        results = []
        for future in futures:
            try:
                results.append(future.result(timeout=30))
            except Exception as e:
                symbol = futures[future]
                logger.error(f"Failed processing {symbol}: {e}")
    return results
```

### Security Best Practices

**API Keys** (NEVER hardcode):
```python
# ❌ WRONG
api_key = "YOUR_API_KEY_HERE"

# ✅ CORRECT - Load from config file (not in version control)
import json
from pathlib import Path

def load_api_config() -> dict:
    """Load API credentials from config file."""
    config_path = Path('config/api_keys.json')
    if not config_path.exists():
        raise FileNotFoundError(
            "API config not found. Copy config/api_keys.example.json "
            "to config/api_keys.json and fill in your credentials."
        )
    with open(config_path) as f:
        return json.load(f)
```

**Data Sanitization** (validate external inputs):
```python
def fetch_stock_data(symbol: str) -> pd.DataFrame:
    """Fetch stock data with input sanitization."""
    # Validate symbol format (Taiwan stocks: 4-6 digits)
    if not symbol.isdigit() or len(symbol) not in (4, 5, 6):
        raise ValueError(f"Invalid symbol format: {symbol}")
    
    # Prevent path traversal attacks
    if '..' in symbol or '/' in symbol or '\\' in symbol:
        raise ValueError(f"Invalid symbol characters: {symbol}")
    
    return self.api.fetch(symbol)
```

## Key Implementation Notes

### Module Dependencies
Core modules in `src/` must be imported in this order to avoid circular dependencies:
1. `utils` (no dependencies)
2. `parquet_manager` (depends on utils)
3. `api_client` (depends on utils)
4. `data_validator` (depends on parquet_manager)
5. `factors` (depends on parquet_manager)
6. `screener` (depends on factors, parquet_manager)
7. `notification` (depends on utils)
8. `etl_pipeline` (depends on parquet_manager)

### Parquet File Operations

When implementing `ParquetManager` methods:
- Use `pyarrow` engine for best performance
- Apply `snappy` compression
- For time partitions, use `filters` parameter for predicate pushdown:
  ```python
  dataset = pq.ParquetDataset(path, filters=[('date', '>=', start_date)])
  ```

### Factor Calculation Caching

`FactorEngine` caches results with key format: `{symbol}_fundamental_{date}`. Always check cache before recalculating.

### API Rate Limiting

`ShioajiClient` includes `RateLimiter` (60 requests/60 seconds). All API methods must call `self.rate_limiter.wait_if_needed()` before requests.

### Error Retry Pattern

Use `@APIErrorHandler.retry_on_failure(max_retries=3)` decorator for network operations. Implements exponential backoff: delay × (attempt + 1).

## Data Schema

### Time Partition Schema
```
Columns: symbol, date, open, high, low, close, volume, amount
```

### Symbol Partition Schema
```
Columns: date, open, high, low, close, volume,
         ma5, ma20, ma60, rsi_14, k, d
```

### Fundamental Data Schema
```
Columns: date, revenue, gross_profit, operating_income, net_income,
         eps, equity, total_assets, total_liabilities,
         operating_cash_flow, capital_expenditure
```

## Reference Documentation

- **System Overview**: `docs/Overview.md` - Overall architecture and build guide
- **Implementation Details**: `docs/Implementation.md` - Complete architecture with 12 Mermaid diagrams
- **Financial Indicators**: `docs/FunctionalIndicators.md` - 50+ indicator definitions

When implementing new features, always reference the corresponding section in `Implementation.md` for pseudocode and architecture diagrams.
