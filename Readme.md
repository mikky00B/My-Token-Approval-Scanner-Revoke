# Wallet Scanner

A Django-based security tool for scanning Ethereum wallets and detecting risky token approvals.

## Features

- 🔍 **Scan Ethereum wallets** for ERC20 and NFT approvals
-  **Risk evaluation** using deterministic rule-based engine
-  **Blacklist detection** for known malicious contracts
-  **Async scanning** with Celery for large wallets
-  **Caching** to reduce API calls and speed up repeated scans
-  **Admin panel** for managing blacklists and viewing results

## Architecture

```
Scan Pipeline:
├── Stage 1: Input Validation
├── Stage 2: Approval Discovery (Etherscan API)
├── Stage 3: Data Normalization
├── Stage 4: Risk Evaluation (Rule Engine)
├── Stage 5: Risk Aggregation
└── Stage 6: Persistence & Caching
```

## Quick Start

### Prerequisites

- Python 3.10+
- Redis (for Celery & caching)
- Etherscan API key (free at https://etherscan.io/apis)

### Installation

```bash
# Clone repository
git clone <your-repo>
cd wallet_scanner

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/dev.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your ETHERSCAN_API_KEY

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Seed blacklist (optional)
python manage.py seed_blacklist
```

### Running

**Terminal 1 - Django:**
```bash
python manage.py runserver
```

**Terminal 2 - Redis:**
```bash
redis-server
```

**Terminal 3 - Celery (for async scans):**
```bash
celery -A config worker --loglevel=info
```

## API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

#### 1. Health Check
```bash
GET /health/
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

#### 2. Scan Wallet
```bash
POST /scan-wallet/
Content-Type: application/json

{
  "wallet_address": "0xYourWalletAddress",
  "chain_id": 1,
  "async": false
}
```

**Parameters:**
- `wallet_address` (required): Ethereum wallet address
- `chain_id` (optional): Chain ID, default 1 (Ethereum)
- `async` (optional): If true, scan runs asynchronously

**Response (Sync):**
```json
{
  "scan_id": 1,
  "wallet_address": "0x...",
  "chain_id": 1,
  "status": "COMPLETED",
  "total_approvals": 15,
  "total_risk_score": 200,
  "risk_level": "MEDIUM",
  "high_risk_count": 5,
  "critical_risk_count": 0,
  "message": "Scan completed successfully"
}
```

**Response (Async):**
```json
{
  "scan_id": 1,
  "status": "PENDING",
  "message": "Scan queued successfully"
}
```

#### 3. Get Scan Status
```bash
GET /scan-status/{scan_id}/
```

**Response:**
```json
{
  "scan_id": 1,
  "wallet_address": "0x...",
  "status": "COMPLETED",
  "total_approvals": 15,
  "total_risk_score": 200,
  "risk_level": "MEDIUM",
  "approvals": [
    {
      "id": 1,
      "token_address": "0x...",
      "token_type": "ERC20",
      "spender_address": "0x...",
      "is_unlimited": true,
      "risk_level": "MEDIUM",
      "risk_points": 25,
      "risk_reasons": [
        "Unlimited ERC20 approval"
      ]
    }
  ]
}
```

#### 4. Get Scan Details
```bash
GET /scans/{scan_id}/
```

#### 5. Get Scan Approvals (with filtering)
```bash
GET /scans/{scan_id}/approvals/?risk_level=HIGH&token_type=ERC20
```

#### 6. Get Approval Details
```bash
GET /approvals/{approval_id}/
```

#### 7. Get Wallet History
```bash
GET /wallets/{wallet_address}/scans/
```

## Risk Evaluation Rules

The scanner uses a rule-based system:

1. **Unlimited ERC20 Approval** (+25 points)
   - Spender can transfer unlimited tokens

2. **NFT Operator Approval** (+30 points)
   - Spender can transfer all NFTs from collection

3. **Blacklisted Spender** (+50 points)
   - Approval to known malicious contract

4. **Unknown Spender** (+10 points)
   - Approval to unverified contract

### Risk Levels

- **LOW**: 0-19 points
- **MEDIUM**: 20-39 points
- **HIGH**: 40-59 points
- **CRITICAL**: 60+ points

## Admin Panel

Access at: http://localhost:8000/admin/

Features:
- View all scans with filtering
- Manage blacklist entries
- View approval details
- Track wallet scan history

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest apps/scans/tests/test_integration.py -v

# Run with coverage
pytest --cov=apps --cov-report=html
```

## Project Structure

```
wallet_scanner/
├── apps/
│   ├── wallets/        # Wallet models & validation
│   ├── scans/          # Scan orchestration & caching
│   ├── approvals/      # Approval models & discovery
│   ├── risk_engine/    # Risk evaluation rules
│   ├── blacklists/     # Malicious address tracking
│   └── chains/         # Chain constants & config
├── api/
│   └── v1/             # API endpoints
├── config/             # Django settings & Celery
└── shared/             # Shared schemas & utilities
```

## Environment Variables

```bash
# .env
DJANGO_SECRET_KEY=your-secret-key
ETHERSCAN_API_KEY=your-etherscan-key
DJANGO_ENV=local  # local | production
```

## Deployment Considerations

### Production Checklist

- [ ] Set `DEBUG=False` in production settings
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set up proper Redis with persistence
- [ ] Use environment-specific API keys
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Configure CORS for frontend
- [ ] Set up SSL/TLS
- [ ] Rate limit API endpoints
- [ ] Set up log aggregation

## Roadmap

### Phase 2: Smart Contract Integration
- Deploy Vyper inspection contract
- Reduce dependency on Etherscan
- Add on-chain allowance verification


## Contributing

This is a portfolio project. Feel free to fork and adapt for your use case.

## License

MIT

## Contact

Your Name - clevermike02@gmail.com

---

Built with Django, Celery, and web3.py