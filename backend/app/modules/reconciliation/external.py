"""
External Provider Mock

This module provides mock implementations of external provider APIs for reconciliation testing.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.core.logging import logger

class MockProviderAPI:
    """Base class for mock provider APIs."""
    
    def __init__(self, provider: str):
        """Initialize mock provider."""
        self.provider = provider
        self._accounts: Dict[str, float] = {}
        self._last_updated: Dict[str, datetime] = {}
    
    async def get_balances(self, account_ids: List[str]) -> Dict[str, float]:
        """Get account balances from provider."""
        raise NotImplementedError
    
    async def get_last_updated(self, account_ids: List[str]) -> Dict[str, datetime]:
        """Get last update timestamps for accounts."""
        raise NotImplementedError

class MockBankAPI(MockProviderAPI):
    """Mock implementation of bank API."""
    
    def __init__(self):
        """Initialize mock bank API."""
        super().__init__("bank")
        # Initialize with some test data
        self._accounts = {
            "BANK001": 10000.00,
            "BANK002": 25000.50,
            "BANK003": 5000.75
        }
        now = datetime.utcnow()
        self._last_updated = {
            "BANK001": now - timedelta(hours=2),
            "BANK002": now - timedelta(hours=1),
            "BANK003": now - timedelta(minutes=30)
        }
    
    async def get_balances(self, account_ids: List[str]) -> Dict[str, float]:
        """Get bank account balances."""
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        # Add some random noise to simulate real-world discrepancies
        balances = {}
        for account_id in account_ids:
            if account_id in self._accounts:
                base_balance = self._accounts[account_id]
                # Add random noise between -0.01% and +0.01%
                noise = random.uniform(-0.0001, 0.0001)
                balances[account_id] = round(base_balance * (1 + noise), 2)
            else:
                logger.warning(f"Account not found in mock bank: {account_id}")
        
        return balances
    
    async def get_last_updated(self, account_ids: List[str]) -> Dict[str, datetime]:
        """Get last update timestamps for bank accounts."""
        return {
            account_id: self._last_updated[account_id]
            for account_id in account_ids
            if account_id in self._last_updated
        }

class MockPaymentAPI(MockProviderAPI):
    """Mock implementation of payment processor API."""
    
    def __init__(self):
        """Initialize mock payment API."""
        super().__init__("payment")
        # Initialize with some test data
        self._accounts = {
            "PAY001": 5000.00,
            "PAY002": 15000.25,
            "PAY003": 3000.50
        }
        now = datetime.utcnow()
        self._last_updated = {
            "PAY001": now - timedelta(hours=3),
            "PAY002": now - timedelta(hours=2),
            "PAY003": now - timedelta(hours=1)
        }
    
    async def get_balances(self, account_ids: List[str]) -> Dict[str, float]:
        """Get payment account balances."""
        # Simulate API delay
        await asyncio.sleep(0.2)
        
        # Add some random noise to simulate real-world discrepancies
        balances = {}
        for account_id in account_ids:
            if account_id in self._accounts:
                base_balance = self._accounts[account_id]
                # Add random noise between -0.02% and +0.02%
                noise = random.uniform(-0.0002, 0.0002)
                balances[account_id] = round(base_balance * (1 + noise), 2)
            else:
                logger.warning(f"Account not found in mock payment: {account_id}")
        
        return balances
    
    async def get_last_updated(self, account_ids: List[str]) -> Dict[str, datetime]:
        """Get last update timestamps for payment accounts."""
        return {
            account_id: self._last_updated[account_id]
            for account_id in account_ids
            if account_id in self._last_updated
        }

class MockInvestmentAPI(MockProviderAPI):
    """Mock implementation of investment API."""
    
    def __init__(self):
        """Initialize mock investment API."""
        super().__init__("investment")
        # Initialize with some test data
        self._accounts = {
            "INV001": 25000.00,
            "INV002": 50000.75,
            "INV003": 10000.25
        }
        now = datetime.utcnow()
        self._last_updated = {
            "INV001": now - timedelta(hours=4),
            "INV002": now - timedelta(hours=3),
            "INV003": now - timedelta(hours=2)
        }
    
    async def get_balances(self, account_ids: List[str]) -> Dict[str, float]:
        """Get investment account balances."""
        # Simulate API delay
        await asyncio.sleep(0.3)
        
        # Add some random noise to simulate real-world discrepancies
        balances = {}
        for account_id in account_ids:
            if account_id in self._accounts:
                base_balance = self._accounts[account_id]
                # Add random noise between -0.03% and +0.03%
                noise = random.uniform(-0.0003, 0.0003)
                balances[account_id] = round(base_balance * (1 + noise), 2)
            else:
                logger.warning(f"Account not found in mock investment: {account_id}")
        
        return balances
    
    async def get_last_updated(self, account_ids: List[str]) -> Dict[str, datetime]:
        """Get last update timestamps for investment accounts."""
        return {
            account_id: self._last_updated[account_id]
            for account_id in account_ids
            if account_id in self._last_updated
        }

def get_provider_api(provider: str) -> MockProviderAPI:
    """Get appropriate mock provider API."""
    providers = {
        "bank": MockBankAPI,
        "payment": MockPaymentAPI,
        "investment": MockInvestmentAPI
    }
    
    if provider not in providers:
        raise ValueError(f"Unsupported provider: {provider}")
    
    return providers[provider]() 
