"""
Load seed data into Neo4j database
This script reads seed_data.cypher and executes all Cypher statements
"""

import os
import re
import logging
from pathlib import Path
from database.neo4j_connector import Neo4jConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_cypher_file(file_path: str) -> str:
    """Read Cypher file and return content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def split_cypher_statements(content: str) -> list:
    """
    Split Cypher file into individual statements
    Handles multi-line statements and comments
    """
    # Remove comment lines (starting with #)
    lines = []
    for line in content.split('\n'):
        stripped = line.strip()
        # Skip comment-only lines
        if stripped.startswith('#'):
            continue
        # Remove inline comments (//)
        if '//' in line:
            line = line[:line.index('//')]
        lines.append(line)
    
    # Join and split by semicolons
    full_text = '\n'.join(lines)
    
    # Split by semicolons
    statements = []
    for statement in full_text.split(';'):
        statement = statement.strip()
        # Skip empty statements
        if not statement:
            continue
        # Skip statements that are only whitespace/comments
        if re.match(r'^\s*$', statement):
            continue
        statements.append(statement)
    
    return statements


def load_seed_data():
    """Load seed data from seed_data.cypher into Neo4j"""
    # Get the path to seed_data.cypher
    script_dir = Path(__file__).parent
    seed_file = script_dir / 'database' / 'seed_data.cypher'
    
    if not seed_file.exists():
        logger.error(f"Seed data file not found: {seed_file}")
        return False
    
    logger.info(f"Reading seed data from: {seed_file}")
    content = read_cypher_file(str(seed_file))
    
    # Split into statements
    statements = split_cypher_statements(content)
    logger.info(f"Found {len(statements)} Cypher statements to execute")
    
    # Connect to Neo4j
    db = Neo4jConnector()
    
    if not db.test_connection():
        logger.error("Failed to connect to Neo4j. Check your .env configuration.")
        return False
    
    logger.info("✓ Connected to Neo4j")
    
    # Execute each statement
    success_count = 0
    error_count = 0
    
    for i, statement in enumerate(statements, 1):
        try:
            # Skip empty statements
            if not statement.strip():
                continue
            
            # Execute statement
            result = db.execute_write(statement, {})
            success_count += 1
            
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(statements)} statements executed")
        
        except Exception as e:
            error_count += 1
            logger.warning(f"Error executing statement {i}: {str(e)[:100]}")
            # Continue with next statement
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Seed data loading complete!")
    logger.info(f"  ✓ Successfully executed: {success_count} statements")
    if error_count > 0:
        logger.info(f"  ✗ Errors: {error_count} statements")
    logger.info(f"{'='*60}")
    
    # Verify data was loaded
    logger.info("\nVerifying loaded data...")
    try:
        # Check customers
        customer_query = "MATCH (c:Customer) RETURN COUNT(c) as count"
        result = db.execute_query(customer_query, {})
        customer_count = result[0]["count"] if result else 0
        logger.info(f"  ✓ Customers: {customer_count}")
        
        # Check accounts
        account_query = "MATCH (a:Account) RETURN COUNT(a) as count"
        result = db.execute_query(account_query, {})
        account_count = result[0]["count"] if result else 0
        logger.info(f"  ✓ Accounts: {account_count}")
        
        # Check transactions
        txn_query = "MATCH (t:Transaction) RETURN COUNT(t) as count"
        result = db.execute_query(txn_query, {})
        txn_count = result[0]["count"] if result else 0
        logger.info(f"  ✓ Transactions: {txn_count}")
        
        # Check SOPs
        sop_query = "MATCH (s:SOP) RETURN COUNT(s) as count"
        result = db.execute_query(sop_query, {})
        sop_count = result[0]["count"] if result else 0
        logger.info(f"  ✓ SOPs: {sop_count}")
        
        if customer_count >= 5 and account_count >= 5 and txn_count >= 6 and sop_count >= 10:
            logger.info("\n✓ Seed data loaded successfully!")
            return True
        else:
            logger.warning("\n⚠ Some data may be missing. Expected:")
            logger.warning("  - Customers: >= 5")
            logger.warning("  - Accounts: >= 5")
            logger.warning("  - Transactions: >= 6")
            logger.warning("  - SOPs: >= 10")
            return False
    
    except Exception as e:
        logger.error(f"Error verifying data: {e}")
        return False


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Loading Neo4j Seed Data")
    logger.info("="*60)
    
    success = load_seed_data()
    
    if success:
        logger.info("\n✓ You can now run the backend server and test scenarios!")
    else:
        logger.error("\n✗ Seed data loading had issues. Check the errors above.")
        exit(1)

