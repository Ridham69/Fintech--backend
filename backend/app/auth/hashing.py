"""Password hashing utilities using Argon2 with bcrypt fallback."""
import logging
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import HashingError, VerificationError
import bcrypt

logger = logging.getLogger(__name__)

# Configure Argon2 with secure parameters
# These parameters are based on OWASP recommendations
ph = PasswordHasher(
    time_cost=2,        # Number of iterations
    memory_cost=102400,  # 100MB in KiB
    parallelism=8,      # Number of parallel threads
    hash_len=32,        # Length of the hash in bytes
    salt_len=16         # Length of the salt in bytes
)

def hash_password(password: str) -> str:
    """
    Hash a password using Argon2 with bcrypt fallback.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
        
    Raises:
        RuntimeError: If both Argon2 and bcrypt fail
    """
    try:
        return ph.hash(password)
    except HashingError as e:
        logger.warning("[AUTH] Argon2 hashing failed, falling back to bcrypt", exc_info=e)
        try:
            # Generate a salt and hash the password using bcrypt
            salt = bcrypt.gensalt(rounds=12)  # 2^12 rounds
            return bcrypt.hashpw(password.encode(), salt).decode()
        except Exception as e:
            logger.error("[AUTH] Password hashing failed with both Argon2 and bcrypt", exc_info=e)
            raise RuntimeError("Failed to hash password") from e

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash using Argon2 or bcrypt.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Previously hashed password
        
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        # Try Argon2 first
        ph.verify(hashed_password, plain_password)
        
        # Check if the hash needs to be updated
        if ph.check_needs_rehash(hashed_password):
            logger.info("[AUTH] Password hash needs rehashing")
            return True, True
            
        return True, False
    except VerificationError:
        # If Argon2 fails, try bcrypt
        try:
            is_valid = bcrypt.checkpw(
                plain_password.encode(),
                hashed_password.encode()
            )
            # If valid with bcrypt, we should rehash with Argon2
            return is_valid, is_valid
        except Exception as e:
            logger.error("[AUTH] Password verification failed", exc_info=e)
            return False, False
    except Exception as e:
        logger.error("[AUTH] Unexpected error during password verification", exc_info=e)
        return False, False 