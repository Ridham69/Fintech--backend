
# AutoInvest India Backend

A robust, async FastAPI backend powering a secure fintech platform that automatically invests a portion of each user transaction into index funds. Designed for extensibility, compliance, and high reliability in the Indian financial ecosystem.

---

## ✅ Features

- [x] Async FastAPI architecture for high performance
- [x] Automated investment of user transactions into index funds
- [x] Modular codebase (`auth`, `transactions`, `investments`, `notifications`, `kyc`, `feature_flags`)
- [x] JWT-based authentication and RBAC
- [x] PostgreSQL (async SQLAlchemy) for persistent storage
- [x] Redis for caching and Celery for background task processing
- [x] Real-time notifications and investment tracking
- [x] Comprehensive logging and exception handling
- [x] Prometheus & Grafana monitoring integration
- [x] Sentry for error tracking
- [x] Fully covered with Pytest test cases
- [x] Docker & docker-compose support for easy deployment
- [x] .env-based configuration for secure secrets management
- [x] Extensible for future features (subscriptions, ML fraud detection, etc.)

---

## 🛠 Tech Stack

- **Framework:** FastAPI (async)
- **Database:** PostgreSQL (async SQLAlchemy)
- **Cache/Queue:** Redis, Celery
- **Monitoring:** Prometheus, Grafana
- **Error Tracking:** Sentry
- **Auth:** JWT (PyJWT)
- **Testing:** Pytest
- **Containerization:** Docker, docker-compose
- **Other:** dotenv, logging, modular Python structure

---

## 📁 Directory Structure

```
backend/
├── app/
│   ├── auth/              # Authentication & RBAC
│   ├── transactions/      # Payment & transaction logic
│   ├── investments/       # Investment automation logic
│   ├── notifications/     # Notification services
│   ├── kyc/               # KYC and compliance
│   ├── feature_flags/     # Feature flag management
│   ├── core/              # Core configs, logging, security
│   ├── db/                # Database models & session
│   ├── tasks/             # Celery tasks
│   ├── integrations/      # Third-party APIs (brokers, payment gateways)
│   ├── utils/             # Utility functions
│   └── main.py            # FastAPI entrypoint
├── tests/                 # Pytest test cases
├── alembic/               # DB migrations
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Ridham69/Fintech--backend
cd fintech-backend/backend
```

### 2. Local Development Setup

#### a. Python Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### b. Environment Variables

- Copy .env.example to .env and fill in variables like:

DATABASE_URL

SECRET_KEY

REDIS_URL

SENTRY_DSN

#### c. Database & Redis

- Ensure PostgreSQL and Redis are running locally, or use Docker Compose (see below).

#### d. Run Migrations

```bash
alembic upgrade head
```

#### e. Start the FastAPI Server

```bash
uvicorn app.main:app --reload
```

### 3. Docker Setup (Recommended)

```bash
docker-compose up --build
```

- This will start FastAPI, PostgreSQL, Redis, and Celery worker containers.

---

## 📖 Usage Instructions

- The API will be available at: `http://localhost:8000`
- Interactive API docs: `http://localhost:8000/docs`
- Use JWT tokens for authenticated endpoints (see `/auth/login`).

---

## 🧪 Running Tests

```bash
pytest
```

- All modules are covered with unit and integration tests.
- Coverage reports are generated in `htmlcov/` if enabled.

---

## 📊 Monitoring & Error Tracking

- **Prometheus** metrics exposed at `/metrics` (enable in config).
- **Grafana** dashboards can be configured to visualize metrics.
- **Sentry** is integrated for real-time error logging (configure DSN in `.env`).

---

## 🤝 Contributing

1. Fork the repository and create your branch.
2. Write clear, well-tested code.
3. Ensure all tests pass (`pytest`).
4. Submit a pull request with a clear description.

See [CONTRIBUTING.md](../docs/CONTRIBUTING.md) for more details.

---

## 📬 Contact & License

- **Contact:** [ridhamking12345@gmail.com]
- **License:** Proprietary – All rights reserved.

---

> _This backend is designed for extensibility and compliance with Indian fintech regulations. For architecture details, see `ARCHITECTURE.md`._

