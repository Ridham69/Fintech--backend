# AutoInvest India - Architecture Overview

## Project Structure

```
├── frontend/                      # Next.js frontend application
│   ├── src/
│   │   ├── app/                  # Next.js 14 app directory
│   │   │   ├── (auth)/          # Authentication routes
│   │   │   │   ├── login/
│   │   │   │   ├── register/
│   │   │   │   └── forgot-password/
│   │   │   ├── dashboard/        # User dashboard routes
│   │   │   ├── admin/           # Admin portal routes
│   │   │   └── api/             # Frontend API routes
│   │   ├── components/
│   │   │   ├── common/          # Shared components
│   │   │   ├── forms/           # Form components
│   │   │   ├── layout/          # Layout components
│   │   │   └── dashboard/        # Dashboard-specific components
│   │   ├── hooks/               # Custom React hooks
│   │   ├── services/            # API service layers
│   │   ├── store/               # State management
│   │   ├── types/               # TypeScript types
│   │   └── utils/               # Utility functions
│   ├── public/                  # Static assets
│   └── tests/                   # Frontend tests
│
├── backend/                     # FastAPI backend application
│   ├── app/
│   │   ├── api/                # API endpoints
│   │   │   ├── v1/
│   │   │   │   ├── auth.py     # Authentication endpoints
│   │   │   │   ├── users.py    # User management
│   │   │   │   ├── kyc.py      # KYC verification
│   │   │   │   ├── payments.py  # Payment processing
│   │   │   │   ├── investments.py # Investment operations
│   │   │   │   └── webhooks.py  # Webhook handlers
│   │   │   └── deps.py         # API dependencies
│   │   ├── core/               # Core application code
│   │   │   ├── config.py       # Configuration
│   │   │   ├── security.py     # Security utilities
│   │   │   └── logging.py      # Logging configuration
│   │   ├── db/                 # Database
│   │   │   ├── models/         # SQLAlchemy models
│   │   │   ├── migrations/     # Alembic migrations
│   │   │   └── session.py      # Database session
│   │   ├── services/           # Business logic
│   │   │   ├── auth.py         # Authentication service
│   │   │   ├── kyc.py          # KYC service
│   │   │   ├── payment.py      # Payment service
│   │   │   ├── investment.py   # Investment service
│   │   │   └── notification.py # Notification service
│   │   ├── tasks/              # Async tasks
│   │   │   ├── investment_execution.py
│   │   │   ├── notifications.py
│   │   │   └── scheduled_jobs.py
│   │   ├── integrations/       # Third-party integrations
│   │   │   ├── brokers/        # Broker APIs
│   │   │   ├── payment_gateways/
│   │   │   └── kyc_providers/
│   │   └── utils/              # Utility functions
│   ├── tests/                  # Backend tests
│   └── worker/                 # Celery worker
│
├── infrastructure/             # Infrastructure as code
│   ├── docker/                # Docker configurations
│   ├── terraform/             # AWS infrastructure
│   └── k8s/                   # Kubernetes configs
│
└── docs/                      # Documentation
    ├── api/                   # API documentation
    ├── architecture/          # Architecture details
    └── compliance/           # Compliance docs
```

## Component Details

### Frontend Components

#### Authentication & User Management
- `components/auth/LoginForm.tsx`: User login form with 2FA support
- `components/auth/RegisterForm.tsx`: User registration with email verification
- `components/auth/KYCFlow.tsx`: Step-by-step KYC process
- `components/auth/BankLinking.tsx`: Bank account linking interface
- `components/auth/BrokerLinking.tsx`: Broker account linking

#### Dashboard
- `components/dashboard/Overview.tsx`: Main dashboard view
- `components/dashboard/InvestmentRules.tsx`: Investment rule configuration
- `components/dashboard/TransactionHistory.tsx`: Payment and investment history
- `components/dashboard/Analytics.tsx`: Investment performance charts
- `components/dashboard/Notifications.tsx`: User notifications center

#### Admin Portal
- `components/admin/UserManagement.tsx`: User administration
- `components/admin/ComplianceMonitoring.tsx`: Compliance dashboard
- `components/admin/SystemMetrics.tsx`: System health monitoring
- `components/admin/AuditLogs.tsx`: Audit log viewer

### Backend Services

#### User Management & KYC
- `services/auth.py`: Authentication and authorization
- `services/kyc.py`: KYC verification workflow
- `services/user.py`: User profile management

#### Payment Processing
- `services/payment.py`: Payment processing and tracking
- `services/upi.py`: UPI payment integration
- `services/webhook_handler.py`: Payment gateway webhooks

#### Investment Engine
- `services/investment_rules.py`: Investment rule processing
- `services/order_execution.py`: Broker order execution
- `services/portfolio.py`: Portfolio tracking and rebalancing

#### Notification System
- `services/notification.py`: Multi-channel notification dispatch
- `services/templates.py`: Notification template management
- `services/delivery.py`: Email/SMS/Push notification delivery

### Database Models

```python
# Example model structure in models/user.py
class User(Base):
    id: UUID
    email: str
    phone: str
    kyc_status: KYCStatus
    investment_profile: JSON
    audit_log: List[AuditLog]
    created_at: datetime
    updated_at: datetime

# Example model structure in models/investment_rule.py
class InvestmentRule(Base):
    id: UUID
    user_id: UUID
    trigger_type: TriggerType
    conditions: JSON
    investment_target: JSON
    is_active: bool
    created_at: datetime
```

### Security Features

1. Authentication & Authorization
   - JWT-based authentication
   - Role-based access control
   - Session management
   - IP whitelisting for admin access

2. Data Security
   - End-to-end encryption for sensitive data
   - Field-level encryption for PII
   - Secure key management
   - Data masking in logs

3. Audit & Compliance
   - Comprehensive audit logging
   - Transaction tracking
   - Regulatory reporting
   - Data retention policies

### Async Jobs & Workers

1. Investment Execution
   - Order placement and tracking
   - Retry mechanisms
   - Failure handling
   - Status updates

2. Notification Processing
   - Email/SMS queuing
   - Push notification dispatch
   - Delivery status tracking

3. Scheduled Tasks
   - Portfolio rebalancing
   - Report generation
   - Data cleanup
   - Compliance checks

### Monitoring & Logging

1. Application Monitoring
   - Request/response logging
   - Performance metrics
   - Error tracking
   - User activity monitoring

2. System Monitoring
   - Resource utilization
   - Service health checks
   - Database performance
   - Cache hit rates

3. Business Monitoring
   - Transaction success rates
   - Investment execution rates
   - User engagement metrics
   - Compliance violations

### Error Handling

Every component implements comprehensive error handling:
- Input validation
- Business rule validation
- Integration error handling
- Retry mechanisms
- Fallback strategies
- Error reporting
- User-friendly error messages 