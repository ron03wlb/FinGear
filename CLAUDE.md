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

1. **Layer 1 - Fundamental**: `FactorEngine` calculates 7 weighted factors (ROE, EPS YoY, FCF, etc.) → Top 30 from Top 500
2. **Layer 2 - Chips**: Validates institutional trading (5-day net buy) + major holder changes
3. **Layer 3 - Technical**: Calculates bias ratio vs MA60, KD crossover → Generates buy/sell/hold signals

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

- **System Overview**: `Requirement/Overview.md` - Overall architecture and build guide
- **Implementation Details**: `Requirement/Implementation.md` - Complete architecture with 12 Mermaid diagrams
- **Financial Indicators**: `Requirement/FunctionalIndicators.md` - 50+ indicator definitions

When implementing new features, always reference the corresponding section in `Implementation.md` for pseudocode and architecture diagrams.
