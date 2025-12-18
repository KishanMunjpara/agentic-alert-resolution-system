"""
Authentication Service
Handles user registration, login, and credential management
"""

import logging
from typing import Optional, Dict
import bcrypt
from auth.jwt_handler import JWTHandler
from database.neo4j_connector import Neo4jConnector
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service for user management
    """
    
    def __init__(self):
        """Initialize authentication service"""
        self.db = Neo4jConnector()
        self.jwt_handler = JWTHandler()
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify password against hash
        
        Args:
            password: Plain text password
            hashed_password: Hashed password to verify against
            
        Returns:
            True if password matches
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    async def register_user(self, username: str, email: str, password: str) -> Dict:
        """
        Register a new user
        
        Args:
            username: Username
            email: Email address
            password: Password
            
        Returns:
            User data with created user ID
        """
        try:
            # Check if user already exists
            query_check = "MATCH (u:User {username: $username}) RETURN u"
            existing = self.db.execute_query(query_check, {"username": username})
            if existing:
                return {"error": "User already exists", "success": False}
            
            # Hash password
            hashed_password = self.hash_password(password)
            
            # Create user node
            user_id = f"usr-{uuid.uuid4().hex[:8]}"
            query = """
            CREATE (u:User {
                user_id: $user_id,
                username: $username,
                email: $email,
                password_hash: $password_hash,
                created_at: $timestamp,
                updated_at: $timestamp
            })
            RETURN u
            """
            
            params = {
                "user_id": user_id,
                "username": username,
                "email": email,
                "password_hash": hashed_password,
                "timestamp": datetime.now().isoformat()
            }
            
            self.db.execute_write(query, params)
            
            logger.info(f"✓ User registered: {username}")
            
            return {
                "success": True,
                "user_id": user_id,
                "username": username,
                "email": email
            }
            
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return {"error": str(e), "success": False}
    
    async def login_user(self, username: str, password: str) -> Dict:
        """
        Login user and generate tokens
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Tokens and user data or error
        """
        try:
            # Get user
            query = "MATCH (u:User {username: $username}) RETURN u"
            results = self.db.execute_query(query, {"username": username})
            
            if not results:
                logger.warning(f"Login failed: User not found - {username}")
                return {"error": "Invalid username or password", "success": False}
            
            user = dict(results[0]["u"])
            
            # Verify password
            if not self.verify_password(password, user.get("password_hash", "")):
                logger.warning(f"Login failed: Invalid password - {username}")
                return {"error": "Invalid username or password", "success": False}
            
            # Generate tokens
            token_data = {
                "sub": user.get("user_id"),
                "username": user.get("username"),
                "email": user.get("email")
            }
            
            access_token = self.jwt_handler.create_access_token(token_data)
            refresh_token = self.jwt_handler.create_refresh_token(token_data)
            
            logger.info(f"✓ User logged in: {username}")
            
            return {
                "success": True,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user_id": user.get("user_id"),
                "username": user.get("username")
            }
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return {"error": str(e), "success": False}
    
    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Generate new access token from refresh token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New access token
        """
        try:
            payload = self.jwt_handler.verify_token(refresh_token)
            
            if not payload or payload.get("type") != "refresh":
                return {"error": "Invalid refresh token", "success": False}
            
            # Generate new access token
            token_data = {
                "sub": payload.get("sub"),
                "username": payload.get("username"),
                "email": payload.get("email")
            }
            
            access_token = self.jwt_handler.create_access_token(token_data)
            
            logger.info(f"✓ Access token refreshed for user: {payload.get('username')}")
            
            return {
                "success": True,
                "access_token": access_token,
                "token_type": "bearer"
            }
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return {"error": str(e), "success": False}
    
    async def get_current_user(self, token: str) -> Optional[Dict]:
        """
        Get current user from token
        
        Args:
            token: JWT access token
            
        Returns:
            User data or None
        """
        payload = self.jwt_handler.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        query = "MATCH (u:User {user_id: $user_id}) RETURN u"
        
        try:
            results = self.db.execute_query(query, {"user_id": user_id})
            if results:
                return dict(results[0]["u"])
            return None
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None

