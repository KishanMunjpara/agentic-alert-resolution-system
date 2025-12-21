"""
OSINT (Open Source Intelligence) Service
Provides adverse media search capabilities for customer due diligence
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class OSINTService:
    """
    OSINT Service for Adverse Media Search
    
    In a production environment, this would integrate with:
    - Dow Jones Risk & Compliance
    - World-Check
    - LexisNexis
    - Other commercial OSINT providers
    
    For this implementation, we provide mock responses based on customer data
    """
    
    def __init__(self):
        """Initialize OSINT Service"""
        self.logger = logger
        self.enabled = True  # Can be controlled via environment variable
    
    def is_enabled(self) -> bool:
        """Check if OSINT service is enabled"""
        return self.enabled
    
    async def search_adverse_media(self, customer_name: str, 
                                  customer_id: str,
                                  occupation: Optional[str] = None,
                                  employer: Optional[str] = None) -> Dict:
        """
        Search for adverse media mentions
        
        Args:
            customer_name: Full name of customer
            customer_id: Customer ID
            occupation: Customer occupation
            employer: Customer employer
            
        Returns:
            Dictionary with search results including:
            - has_adverse_media: bool
            - risk_level: str (LOW, MEDIUM, HIGH)
            - matches: List of match details
            - confidence: float
            - search_timestamp: str
        """
        self.logger.info(f"🔍 OSINT search for: {customer_name} ({customer_id})")
        
        # Mock implementation - in production, this would call external APIs
        # For now, we simulate based on occupation and name patterns
        
        result = {
            "customer_name": customer_name,
            "customer_id": customer_id,
            "has_adverse_media": False,
            "risk_level": "LOW",
            "matches": [],
            "confidence": 0.95,
            "search_timestamp": datetime.now().isoformat(),
            "search_sources": ["mock_osint_provider"]
        }
        
        # Simulate adverse media detection based on occupation patterns
        # High-risk occupations or suspicious patterns
        high_risk_occupations = ["Unknown", "Unemployed", "Cash Business Owner"]
        suspicious_keywords = ["fraud", "money laundering", "sanctions", "terrorism"]
        
        # Check if occupation suggests higher risk
        if occupation and occupation in high_risk_occupations:
            result["risk_level"] = "MEDIUM"
            result["matches"].append({
                "type": "occupation_risk",
                "description": f"Occupation '{occupation}' associated with higher risk profiles",
                "severity": "MEDIUM"
            })
        
        # For specific test scenarios, we can simulate findings
        # A-003: KYC Inconsistency - if occupation is Teacher/Student with precious metals transaction
        # This would be flagged as suspicious
        if occupation in ["Teacher", "Student"]:
            # In real OSINT, we might find news articles about teachers involved in fraud
            # For now, we return low risk but note the inconsistency
            result["risk_level"] = "LOW"
            result["matches"].append({
                "type": "profile_inconsistency",
                "description": "Profile shows low-risk occupation but high-value transaction pattern",
                "severity": "LOW"
            })
        
        # If customer name matches known patterns (for testing)
        # In production, this would be actual database lookups
        if "test" in customer_name.lower() or "suspicious" in customer_name.lower():
            result["has_adverse_media"] = True
            result["risk_level"] = "HIGH"
            result["matches"].append({
                "type": "adverse_media",
                "description": "Found adverse media mentions in public records",
                "severity": "HIGH",
                "source": "mock_news_database"
            })
            result["confidence"] = 0.85
        
        self.logger.info(f"✓ OSINT search complete: risk={result['risk_level']}, "
                        f"adverse_media={result['has_adverse_media']}")
        
        return result
    
    async def search_by_entity_name(self, entity_name: str) -> Dict:
        """
        Search for adverse media by entity/counterparty name
        
        Args:
            entity_name: Name of entity to search
            
        Returns:
            Dictionary with search results
        """
        self.logger.info(f"🔍 OSINT entity search for: {entity_name}")
        
        result = {
            "entity_name": entity_name,
            "has_adverse_media": False,
            "risk_level": "LOW",
            "matches": [],
            "confidence": 0.95,
            "search_timestamp": datetime.now().isoformat()
        }
        
        # Mock implementation
        # In production, would search entity databases
        
        return result

