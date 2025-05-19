"""
Investment Service

This module provides investment and trading functionality.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.config import settings
from app.models.investment import (
    Asset,
    Holding,
    Order,
    OrderStatus,
    OrderType,
    Portfolio,
    RiskProfile,
    Trade
)
from app.models.user import User
from app.schemas.investment import (
    OrderCreate,
    OrderResponse,
    TradeResponse
)

class InvestmentService:
    """Service for investment and trading operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize service."""
        self.db = db
    
    async def execute_trade(
        self,
        user_id: UUID,
        asset_id: str,
        action: str,
        units: float,
        value: float
    ) -> TradeResponse:
        """
        Execute a trade with validation and risk checks.
        
        Args:
            user_id: User ID
            asset_id: Asset ID
            action: Trade action ("buy" or "sell")
            units: Number of units
            value: Trade value
            
        Returns:
            TradeResponse with execution details
            
        Raises:
            ValueError: If validation fails
            InsufficientFundsError: If user has insufficient funds
            InsufficientUnitsError: If user has insufficient units
            RiskLimitExceededError: If trade exceeds risk limits
            TradingError: For other trading errors
        """
        try:
            # Get user and validate
            user = await self.db.get(User, user_id)
            if not user:
                raise ValueError(f"User not found: {user_id}")
            
            if not user.is_active:
                raise ValueError(f"User account is inactive: {user_id}")
            
            # Get asset and validate
            asset = await self.db.get(Asset, asset_id)
            if not asset:
                raise ValueError(f"Asset not found: {asset_id}")
            
            if not asset.is_active:
                raise ValueError(f"Asset is not active: {asset_id}")
            
            # Get portfolio
            portfolio = await self.get_portfolio(user_id)
            if not portfolio:
                raise ValueError(f"No portfolio found for user: {user_id}")
            
            # Get risk profile
            risk_profile = await self.get_risk_profile(user_id)
            if not risk_profile:
                raise ValueError(f"No risk profile found for user: {user_id}")
            
            # Validate trade parameters
            if action not in ["buy", "sell"]:
                raise ValueError(f"Invalid action: {action}")
            
            if units <= 0:
                raise ValueError(f"Invalid units: {units}")
            
            if value <= 0:
                raise ValueError(f"Invalid value: {value}")
            
            # Calculate current allocations
            total_value = sum(holding.value for holding in portfolio.holdings)
            current_allocations = {
                holding.asset_id: holding.value / total_value
                for holding in portfolio.holdings
            }
            
            # Perform risk checks
            if action == "buy":
                # Check sufficient funds
                if value > portfolio.available_cash:
                    raise InsufficientFundsError(
                        f"Insufficient funds: required={value}, "
                        f"available={portfolio.available_cash}"
                    )
                
                # Check risk limits
                new_allocation = (
                    (current_allocations.get(asset_id, 0.0) * total_value + value) /
                    (total_value + value)
                )
                
                if new_allocation > risk_profile.max_asset_allocation:
                    raise RiskLimitExceededError(
                        f"Trade would exceed max allocation: "
                        f"new={new_allocation:.2%}, "
                        f"max={risk_profile.max_asset_allocation:.2%}"
                    )
                
                # Check daily limit
                daily_trades = await self._get_daily_trades(user_id)
                daily_value = sum(trade.value for trade in daily_trades)
                
                if daily_value + value > risk_profile.daily_trade_limit:
                    raise RiskLimitExceededError(
                        f"Trade would exceed daily limit: "
                        f"new={daily_value + value}, "
                        f"limit={risk_profile.daily_trade_limit}"
                    )
                
            else:  # sell
                # Check sufficient units
                holding = next(
                    (h for h in portfolio.holdings if h.asset_id == asset_id),
                    None
                )
                
                if not holding or holding.units < units:
                    raise InsufficientUnitsError(
                        f"Insufficient units: required={units}, "
                        f"available={holding.units if holding else 0}"
                    )
                
                # Check minimum holding period
                if holding.created_at > (
                    datetime.utcnow() - risk_profile.min_holding_period
                ):
                    raise RiskLimitExceededError(
                        f"Minimum holding period not met: "
                        f"required={risk_profile.min_holding_period}"
                    )
            
            # Create order
            order = Order(
                user_id=user_id,
                asset_id=asset_id,
                type=OrderType.MARKET,
                action=action,
                units=units,
                value=value,
                status=OrderStatus.PENDING
            )
            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)
            
            try:
                # Execute order through order management system
                execution = await self._execute_order(order)
                
                # Create trade record
                trade = Trade(
                    order_id=order.id,
                    user_id=user_id,
                    asset_id=asset_id,
                    action=action,
                    units=units,
                    value=value,
                    price=value / units,
                    execution_time=datetime.utcnow()
                )
                self.db.add(trade)
                
                # Update portfolio
                if action == "buy":
                    portfolio.available_cash -= value
                    
                    # Update or create holding
                    holding = next(
                        (h for h in portfolio.holdings if h.asset_id == asset_id),
                        None
                    )
                    
                    if holding:
                        holding.units += units
                        holding.value += value
                        holding.last_price = value / units
                        holding.updated_at = datetime.utcnow()
                    else:
                        holding = Holding(
                            portfolio_id=portfolio.id,
                            asset_id=asset_id,
                            units=units,
                            value=value,
                            last_price=value / units
                        )
                        self.db.add(holding)
                        
                else:  # sell
                    portfolio.available_cash += value
                    
                    # Update holding
                    holding = next(
                        (h for h in portfolio.holdings if h.asset_id == asset_id),
                        None
                    )
                    
                    if holding:
                        holding.units -= units
                        holding.value -= value
                        holding.last_price = value / units
                        holding.updated_at = datetime.utcnow()
                        
                        # Remove holding if no units left
                        if holding.units <= 0:
                            await self.db.delete(holding)
                
                # Update order status
                order.status = OrderStatus.COMPLETED
                order.executed_at = datetime.utcnow()
                
                await self.db.commit()
                
                return TradeResponse(
                    id=trade.id,
                    order_id=order.id,
                    user_id=user_id,
                    asset_id=asset_id,
                    action=action,
                    units=units,
                    value=value,
                    price=value / units,
                    execution_time=trade.execution_time
                )
                
            except Exception as e:
                # Update order status
                order.status = OrderStatus.FAILED
                order.error = str(e)
                order.executed_at = datetime.utcnow()
                
                await self.db.commit()
                raise TradingError(f"Order execution failed: {str(e)}")
            
        except Exception as e:
            logger.exception(f"Error executing trade: {str(e)}")
            raise
    
    async def _execute_order(self, order: Order) -> Dict:
        """
        Execute order through order management system.
        
        This is a placeholder for integration with your actual
        order management system. Implement the actual integration
        based on your requirements.
        
        Args:
            order: Order to execute
            
        Returns:
            Dict with execution details
            
        Raises:
            TradingError: If execution fails
        """
        # TODO: Implement actual order management system integration
        # For now, simulate successful execution
        return {
            "order_id": order.id,
            "status": "executed",
            "execution_time": datetime.utcnow()
        }
    
    async def _get_daily_trades(self, user_id: UUID) -> List[Trade]:
        """Get user's trades for today."""
        today = datetime.utcnow().date()
        
        query = select(Trade).where(
            Trade.user_id == user_id,
            Trade.execution_time >= today
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()

class InsufficientFundsError(Exception):
    """Raised when user has insufficient funds."""
    pass

class InsufficientUnitsError(Exception):
    """Raised when user has insufficient units."""
    pass

class RiskLimitExceededError(Exception):
    """Raised when trade exceeds risk limits."""
    pass

class TradingError(Exception):
    """Raised for trading-related errors."""
    pass 