"""
Referral Utilities

This module provides utility functions for the referral system.
"""

import random
import string
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral import ReferralCode

async def generate_referral_code(
    db: AsyncSession,
    length: int = 6
) -> str:
    """
    Generate a unique referral code.
    
    Args:
        db: Database session
        length: Length of the code
        
    Returns:
        Unique referral code
        
    Raises:
        ValueError: If unable to generate unique code
    """
    # Characters to use in code
    chars = string.ascii_uppercase + string.digits
    
    # Try to generate unique code
    max_attempts = 10
    for _ in range(max_attempts):
        # Generate random code
        code = "".join(random.choices(chars, k=length))
        
        # Check if code exists
        result = await db.execute(
            select(ReferralCode).where(ReferralCode.code == code)
        )
        if not result.scalar_one_or_none():
            return code
    
    raise ValueError("Unable to generate unique referral code")

def validate_referral_code(code: str) -> bool:
    """
    Validate referral code format.
    
    Args:
        code: Referral code to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not code:
        return False
    
    # Check length
    if not 6 <= len(code) <= 10:
        return False
    
    # Check characters
    valid_chars = set(string.ascii_uppercase + string.digits)
    if not all(c in valid_chars for c in code):
        return False
    
    return True

def check_abuse_indicators(
    ip_address: Optional[str] = None,
    device_fingerprint: Optional[str] = None,
    user_agent: Optional[str] = None
) -> bool:
    """
    Check for potential abuse indicators.
    
    Args:
        ip_address: IP address
        device_fingerprint: Device fingerprint
        user_agent: User agent string
        
    Returns:
        True if suspicious, False otherwise
    """
    # TODO: Implement abuse detection logic
    # This could include:
    # - IP address reputation check
    # - Device fingerprint analysis
    # - User agent analysis
    # - Rate limiting
    # - Geographic location check
    # - VPN/Tor detection
    return False

def format_referral_link(
    base_url: str,
    code: str,
    campaign_id: Optional[str] = None
) -> str:
    """
    Format referral link.
    
    Args:
        base_url: Base URL
        code: Referral code
        campaign_id: Optional campaign ID
        
    Returns:
        Formatted referral link
    """
    link = f"{base_url}/signup?ref={code}"
    if campaign_id:
        link += f"&campaign={campaign_id}"
    return link

def calculate_reward_amount(
    base_amount: float,
    campaign_multiplier: float = 1.0,
    user_tier_multiplier: float = 1.0
) -> float:
    """
    Calculate reward amount with multipliers.
    
    Args:
        base_amount: Base reward amount
        campaign_multiplier: Campaign multiplier
        user_tier_multiplier: User tier multiplier
        
    Returns:
        Calculated reward amount
    """
    return base_amount * campaign_multiplier * user_tier_multiplier 
