"""
Update all customer emails to test email address
Run this script to update existing customer emails in Neo4j
"""

import asyncio
from database.neo4j_connection import Neo4jConnection
from config import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def update_customer_emails():
    """Update all customer emails to test email"""
    test_email = "kishanmunjpara2710@gmail.com"
    
    db = Neo4jConnection()
    
    try:
        # Step 1: Drop unique constraint on email (for testing purposes)
        logger.info("Step 1: Dropping unique constraint on customer email...")
        try:
            drop_constraint_query = "DROP CONSTRAINT customer_email IF EXISTS"
            db.execute_write(drop_constraint_query, {})
            logger.info("  ✓ Unique constraint dropped")
        except Exception as e:
            logger.warning(f"  ⚠ Could not drop constraint (may not exist): {e}")
        
        # Step 2: Update all customer emails
        logger.info("Step 2: Updating all customer emails...")
        query = """
        MATCH (c:Customer)
        SET c.email = $email
        RETURN c.customer_id as customer_id, c.email as email, c.first_name as first_name, c.last_name as last_name
        """
        
        results = db.execute_query(query, {"email": test_email})
        
        logger.info(f"✓ Updated {len(results)} customers to email: {test_email}")
        
        for result in results:
            logger.info(f"  - {result['customer_id']}: {result['first_name']} {result['last_name']} -> {test_email}")
        
        # Step 3: Note about constraint (we leave it off for testing)
        logger.info("\n⚠ Note: Unique constraint on email has been removed for testing.")
        logger.info("  All customers now have the same email address.")
        logger.info("  If you need the constraint back, run: CREATE CONSTRAINT customer_email ON (c:Customer) ASSERT c.email IS UNIQUE;")
        
        logger.info("\n✓ All customer emails updated successfully!")
        logger.info(f"  Test email: {test_email}")
        logger.info("  You can now test email functionality with any alert that results in RFI action.")
        
    except Exception as e:
        logger.error(f"✗ Failed to update customer emails: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(update_customer_emails())

