# Telematics Integration in Auto Insurance (UBI: PAYD/PHYD)

A production-quality POC for Usage-Based Insurance (UBI) that captures telematics data, computes behavioral risk scores, and provides dynamic pricing based on driving behavior.

## Architecture Overview

This system implements a complete telematics UBI pipeline:
- **Data Ingestion**: GPS + accelerometer telematics data with contextual information
- **Real-time Processing**: Redis Streams for near-real-time event processing
- **ML Pipeline**: Behavioral risk scoring using XGBoost/LightGBM models
- **Dynamic Pricing**: Risk-based premium adjustments with configurable bands
- **User Dashboard**: React frontend for trip visualization and score insights
- **Security**: JWT authentication with privacy-compliant data handling

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL + TimescaleDB
- **Streaming**: Redis Streams
- **ML**: scikit-learn, XGBoost, SHAP for explainability
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Infrastructure**: Docker Compose, Prometheus + Grafana
- **Feature Store**: DuckDB/Parquet files

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Make
- Python 3.11+ (for local development)

### Setup & Run

1. **Clone and setup**:
   ```bash
   git clone <repo-url>
   cd telematics-ubi
   cp .env.example .env
   ```

2. **Start services**:
   ```bash
   make up
   ```

3. **Seed sample data**:
   ```bash
   make seed
   ```

4. **Train ML models**:
   ```bash
   make train
   ```

5. **Evaluate models**:
   ```bash
   make eval
   ```

6. **Compute daily scores**:
   ```bash
   make score
   ```

### Access Points

- **API Documentation**: http://localhost:8000/docs
- **Frontend Dashboard**: http://localhost:5173
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)

### Default Credentials

- **Demo User**: `demo@example.com` / `password123`
- **Admin User**: `admin@example.com` / `admin123`

## Key Commands

```bash
# Development
make up          # Start all services
make down        # Stop all services
make logs        # View service logs

# Data & ML
make seed        # Generate sample users/vehicles/trips
make train       # Train risk scoring models
make eval        # Evaluate models and generate reports
make score       # Compute daily risk scores for all users

# Testing & Quality
make test        # Run all tests
make fmt         # Format code (ruff/black/prettier)
make lint        # Lint code

# Data Export
make export-data # Export sample data for submission
```

## Project Structure

```
/src
  /backend          # FastAPI backend with ML pipeline
  /frontend         # React TypeScript frontend
  /bin              # Utility scripts
  /docs             # Comprehensive documentation
  /models           # ML model artifacts
  /data             # Sample datasets
  /tests            # Test suites
/docker             # Docker configurations
compose.yaml        # Service orchestration
Makefile           # Development commands
```

## Dynamic Pricing Engine

The pricing engine maps risk scores to premium adjustments:

- **Band A (85-100)**: -20% to 0% adjustment
- **Band B (70-85)**: -10% adjustment  
- **Band C (55-70)**: 0% adjustment
- **Band D (40-55)**: +10% adjustment
- **Band E (<40)**: +25% adjustment

Risk scores are computed from:
- **Frequency Model**: Probability of claim within 12 months
- **Severity Model**: Expected claim cost for claimants
- **Combined**: Expected Loss = P(claim) × E[claim_cost]

## API Endpoints

### Core Endpoints
- `POST /telematics/events` - Bulk ingest telematics data
- `POST /telematics/trips/simulate` - Generate simulated trips
- `GET /score/user/{user_id}/latest` - Latest user risk score
- `POST /pricing/quote` - Get dynamic pricing quote
- `GET /users/me` - User profile and policies

### Admin Endpoints
- `POST /admin/reload_models` - Hot-reload ML models
- `GET /admin/users` - User management
- `POST /admin/retrain` - Trigger model retraining

## Sample Data

The system includes realistic synthetic data:
- **500+ simulated trips** with GPS traces
- **Contextual data**: weather, road conditions, crime indices
- **Driving behaviors**: speeding, harsh braking, night driving
- **Claim simulation**: Correlated with driving risk factors

## Model Performance

On synthetic data, models achieve:
- **Classification AUC**: >0.75 (claim probability)
- **Regression RMSE**: <$200 (claim severity)
- **Calibration**: Well-calibrated probability estimates
- **Explainability**: SHAP feature importance analysis

## Privacy & Security

- **PII Minimization**: GPS data bucketized to 5-decimal precision
- **Data Retention**: Configurable retention policies
- **Consent Management**: User consent flags and privacy notices
- **Rate Limiting**: API rate limiting and CORS protection
- **Authentication**: JWT tokens with secure password hashing

## Testing

```bash
make test                    # Run all tests
make test-api               # API contract tests
make test-ml                # ML pipeline tests
make test-pricing           # Pricing engine tests
```

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Data Model](docs/data_model.md)
- [ML Pipeline](docs/ml_notes.md)
- [API Contract](docs/api_contract.md)
- [Privacy & Security](docs/privacy_security.md)

## Submission Instructions

To export for submission:

```bash
# Create submission archive
zip -r Lastname_Firstname_TelematicsUBI.zip . \
  -x "*.git*" "node_modules/*" "__pycache__/*" "*.pyc" ".env"

# Place in submission field as: Lastname_Firstname_ProjectName.zip
```

## Limitations & Notes

This is a POC with the following limitations:
- **Synthetic Data**: All telematics data is simulated
- **Model Scope**: Trained on synthetic claims data
- **Privacy**: Basic POC-level privacy controls
- **Scale**: Designed for demonstration, not production scale

## Development

### Local Development Setup

```bash
# Backend development
cd src/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload

# Frontend development  
cd src/frontend
npm install
npm run dev
```

### Adding New Features

1. **Backend**: Add routes in `/src/backend/api/`
2. **ML**: Extend features in `/src/backend/ml/features.py`
3. **Frontend**: Add components in `/src/frontend/src/components/`
4. **Tests**: Add tests in `/tests/`

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure ports 8000, 5173, 5432, 6379 are available
2. **Docker Issues**: Run `make down && make up` to restart services
3. **Model Loading**: Check `/models/` directory has trained artifacts
4. **Database**: Run `make seed` if tables are empty

### Logs

```bash
make logs              # All services
make logs-api          # Backend only
make logs-frontend     # Frontend only
make logs-db           # Database only
```

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Run `make fmt` before committing
5. Ensure `make test` passes

## License

This is a demonstration project for educational purposes.
