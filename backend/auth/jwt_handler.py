"""
JWT Token Handler
Handles JWT token generation, validation, and refresh
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
from config import config

logger = logging.getLogger(__name__)


class JWTHandler:
    """
    JWT token handler for authentication
    """
    
    @staticmethod
    def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        
        Args:
            data: Data to encode in token
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=config.JWT_EXPIRATION_HOURS)
        
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(
                to_encode,
                config.JWT_SECRET_KEY,
                algorithm=config.JWT_ALGORITHM
            )
            logger.debug(f"Access token created for user: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise
    
    @staticmethod
    def create_refresh_token(data: Dict) -> str:
        """
        Create JWT refresh token with longer expiration
        
        Args:
            data: Data to encode in token
            
        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=config.JWT_REFRESH_EXPIRATION_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        try:
            encoded_jwt = jwt.encode(
                to_encode,
                config.JWT_SECRET_KEY,
                algorithm=config.JWT_ALGORITHM
            )
            logger.debug(f"Refresh token created for user: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token data or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                config.JWT_SECRET_KEY,
                algorithms=[config.JWT_ALGORITHM]
            )
            logger.debug(f"Token verified for user: {payload.get('sub')}")
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[str]:
        """
        Extract user ID from token
        
        Args:
            token: JWT token
            
        Returns:
            User ID or None
        """
        payload = JWTHandler.verify_token(token)
        if payload:
            return payload.get("sub")
        return None

