"""
Models Package

This package contains all SQLAlchemy models for the application.
By importing them here, we ensure they are registered with SQLAlchemy's metadata
and are discoverable by tools like Alembic for migrations.
"""

from .user import User
from .transaction import Transaction
from .payment import PaymentIntent, PaymentProvider, PaymentIntentStatus, PaymentMethod
from .audit_log import AuditLog
# from .admin import AdminUser, AdminScope, AdminUserScopeAssociation # admin.py is empty

# Additional models from the directory
from .audit_mixin import AuditMixin # Mixins might not be strictly necessary here but including for completeness
from .consent import DocumentVersion, UserConsent # Changed import
from .investment import InvestmentFund, UserInvestment, InvestmentTransaction # Changed import
from .linked_accounts import LinkedAccount # Assuming model name is LinkedAccount
from .notification import Notification
from .portfolio_rebalance import RebalanceLog # Changed import
from .reconciliation import ReconciliationReport # Changed import
from .webhooks import WebhookEvent # Changed import

# Ensure all models that inherit from Base are imported here
# so that Base.metadata.create_all() or Alembic can find them.

__all__ = [
    "User",
    "Transaction",
    "PaymentIntent",
    "PaymentProvider",
    "PaymentIntentStatus",
    "PaymentMethod",
    "AuditLog",
    # "AdminUser", # admin.py is empty
    # "AdminScope", # admin.py is empty
    # "AdminUserScopeAssociation", # admin.py is empty
    "AuditMixin",
    "DocumentVersion", # Changed export
    "UserConsent", # Added export
    "InvestmentFund", # Changed export
    "UserInvestment", # Added export
    "InvestmentTransaction", # Added export
    "LinkedAccount",
    "Notification",
    "RebalanceLog", # Changed export
    "ReconciliationReport", # Changed export
    "WebhookEvent", # Changed export
]
