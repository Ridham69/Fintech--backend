# AutoInvest India - Automated Investment Platform

A secure, compliant fintech platform that automatically invests a portion of users' payments into index funds through Indian broker APIs. Built with Next.js, FastAPI, and PostgreSQL.

## Core Features

- Automated investment rules based on payment triggers
- UPI payment integration with major Indian payment gateways
- Broker integration (Zerodha, etc.) for automated investments
- Complete KYC and bank account linking flow
- Real-time notifications and investment tracking
- Secure user dashboard and analytics
- Admin portal for monitoring and compliance
- Comprehensive audit logging and error tracking

## Tech Stack

### Frontend
- Next.js 14+ with TypeScript
- TailwindCSS for styling
- React Query for state management
- React Hook Form for form handling
- NextAuth.js for authentication

### Backend
- FastAPI (Python 3.11+)
- PostgreSQL with SQLAlchemy ORM
- Redis for caching and rate limiting
- Celery for async task processing
- Alembic for database migrations

### Infrastructure
- Docker and Docker Compose
- AWS (ECS, RDS, ElastiCache, S3)
- GitHub Actions for CI/CD
- Prometheus and Grafana for monitoring
- Sentry for error tracking

### Security & Compliance
- JWT-based authentication
- Role-based access control (RBAC)
- End-to-end encryption for sensitive data
- Comprehensive audit logging
- Rate limiting and DDoS protection

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   # Frontend
   cd frontend
   npm install

   # Backend
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

3. Set up environment variables (see .env.example)
4. Start development servers:
   ```bash
   # Frontend
   npm run dev

   # Backend
   uvicorn app.main:app --reload
   ```

## Project Structure

See ARCHITECTURE.md for detailed component breakdown.

## Security and Compliance

This platform is designed to meet RBI and SEBI guidelines for fintech applications. All sensitive data is encrypted, and the system maintains comprehensive audit logs.

## Contributing

See CONTRIBUTING.md for development guidelines.

## License

Proprietary - All rights reserved 