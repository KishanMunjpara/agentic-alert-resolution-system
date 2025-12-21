"""
Neo4j Database Connector Service
Handles connection pooling, query execution, and transaction management
"""

import logging
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import DriverError, Neo4jError
from config import config

logger = logging.getLogger(__name__)


class Neo4jConnector:
    """
    Neo4j connection manager with connection pooling
    Implements singleton pattern for single connection pool
    """
    
    _instance: Optional['Neo4jConnector'] = None
    _driver: Optional[Driver] = None
    
    def __new__(cls):
        """Ensure only one instance exists (singleton)"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Neo4j driver with connection pooling"""
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    config.NEO4J_URI,
                    auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
                    max_connection_pool_size=config.NEO4J_MAX_POOL_SIZE,
                    connection_timeout=config.NEO4J_CONNECTION_TIMEOUT
                )
                logger.info(f"✓ Neo4j driver initialized: {config.NEO4J_URI}")
            except DriverError as e:
                logger.error(f"✗ Failed to initialize Neo4j driver: {e}")
                raise
    
    def test_connection(self) -> bool:
        """Test Neo4j connection"""
        if not self._driver:
            logger.error("✗ Neo4j driver not initialized")
            return False
        
        try:
            # First, try to verify driver connectivity
            self._driver.verify_connectivity()
            
            # Then test with a simple query
            with self._driver.session(database=config.NEO4J_DATABASE) as session:
                result = session.run("RETURN 1 as test")
                result.consume()
            logger.info("✓ Neo4j connection test successful")
            return True
        except Neo4jError as e:
            error_code = getattr(e, 'code', 'UNKNOWN')
            error_message = str(e)
            
            logger.error(f"✗ Neo4j connection test failed: {error_message}")
            logger.error(f"  Error code: {error_code}")
            logger.error(f"  URI: {config.NEO4J_URI}")
            logger.error(f"  User: {config.NEO4J_USER}")
            logger.error(f"  Database: {config.NEO4J_DATABASE}")
            
            # Provide helpful suggestions based on error
            if "WRITE" in error_message.upper() or "routing" in error_message.lower():
                logger.error("  💡 Suggestion: Check if Neo4j is running and accessible")
                logger.error("     For Neo4j Aura, verify your instance is active")
                logger.error("     For local Neo4j, ensure it's started: neo4j start")
            elif "authentication" in error_message.lower() or "credentials" in error_message.lower():
                logger.error("  💡 Suggestion: Verify NEO4J_USER and NEO4J_PASSWORD in .env file")
            elif "database" in error_message.lower():
                logger.error(f"  💡 Suggestion: Database '{config.NEO4J_DATABASE}' might not exist")
                logger.error("     Try using 'neo4j' as the database name (default)")
            
            return False
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            logger.error(f"✗ Neo4j connection test failed with unexpected error: {error_message}")
            logger.error(f"  Error type: {error_type}")
            logger.error(f"  URI: {config.NEO4J_URI}")
            logger.error(f"  User: {config.NEO4J_USER}")
            logger.error(f"  Database: {config.NEO4J_DATABASE}")
            
            # Check if it's a connection-related error
            if "connection" in error_message.lower() or "refused" in error_message.lower():
                logger.error("  💡 Suggestion: Neo4j might not be running")
                logger.error("     For local Neo4j: Start with 'neo4j start' or check service status")
                logger.error("     For Neo4j Aura: Verify your instance URL and credentials")
            
            return False
    
    def close(self):
        """Close Neo4j driver connection"""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j driver closed")
            self._driver = None
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        Execute a Cypher query and return results
        
        Args:
            query: Cypher query string
            parameters: Query parameters (optional)
            
        Returns:
            List of result records as dictionaries
        """
        try:
            with self._driver.session(database=config.NEO4J_DATABASE) as session:
                result = session.run(query, parameters or {})
                records = [dict(record) for record in result]
                logger.debug(f"Query executed: {query[:50]}... ({len(records)} records)")
                return records
        except Neo4jError as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise
    
    def execute_write(self, query: str, parameters: Optional[Dict] = None) -> Dict:
        """
        Execute a write transaction
        
        Args:
            query: Cypher write query
            parameters: Query parameters
            
        Returns:
            Transaction summary
        """
        try:
            with self._driver.session(database=config.NEO4J_DATABASE) as session:
                def transaction_func(tx):
                    result = tx.run(query, parameters or {})
                    summary = result.consume()
                    return {
                        "nodes_created": summary.counters.nodes_created,
                        "relationships_created": summary.counters.relationships_created,
                        "properties_set": summary.counters.properties_set
                    }
                
                summary = session.write_transaction(transaction_func)
                logger.debug(f"Write transaction executed: {summary}")
                return summary
        except Neo4jError as e:
            logger.error(f"Write transaction failed: {e}")
            raise
    
    def get_node_by_id(self, label: str, id_field: str, id_value: str) -> Optional[Dict]:
        """
        Get a single node by ID
        
        Args:
            label: Node label (e.g., 'Customer')
            id_field: ID field name (e.g., 'customer_id')
            id_value: ID value to search for
            
        Returns:
            Node data as dictionary or None
        """
        query = f"MATCH (n:{label} {{{id_field}: $id}}) RETURN n"
        try:
            results = self.execute_query(query, {"id": id_value})
            return dict(results[0]["n"]) if results else None
        except Exception as e:
            logger.error(f"Failed to get {label} by {id_field}: {e}")
            return None
    
    def create_node(self, label: str, properties: Dict) -> Optional[str]:
        """
        Create a new node
        
        Args:
            label: Node label
            properties: Node properties
            
        Returns:
            Node ID or None on failure
        """
        prop_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        query = f"CREATE (n:{label} {{{prop_str}}}) RETURN n.{list(properties.keys())[0]} as id"
        
        try:
            results = self.execute_query(query, properties)
            node_id = results[0]["id"] if results else None
            logger.debug(f"Created {label} node: {node_id}")
            return node_id
        except Exception as e:
            logger.error(f"Failed to create {label}: {e}")
            return None
    
    def update_node(self, label: str, id_field: str, id_value: str, 
                   updates: Dict) -> bool:
        """
        Update node properties
        
        Args:
            label: Node label
            id_field: ID field name
            id_value: ID value
            updates: Properties to update
            
        Returns:
            True if successful
        """
        set_str = ", ".join([f"n.{k} = ${k}" for k in updates.keys()])
        query = f"MATCH (n:{label} {{{id_field}: ${id_field}}}) SET {set_str}"
        
        params = {id_field: id_value, **updates}
        try:
            self.execute_write(query, params)
            logger.debug(f"Updated {label}: {id_value}")
            return True
        except Exception as e:
            logger.error(f"Failed to update {label}: {e}")
            return False
    
    def create_relationship(self, node1_label: str, node1_id_field: str, 
                          node1_id: str, relationship: str, 
                          node2_label: str, node2_id_field: str, 
                          node2_id: str) -> bool:
        """
        Create a relationship between two nodes
        
        Args:
            node1_label: First node label
            node1_id_field: First node ID field
            node1_id: First node ID value
            relationship: Relationship type
            node2_label: Second node label
            node2_id_field: Second node ID field
            node2_id: Second node ID value
            
        Returns:
            True if successful
        """
        query = f"""
        MATCH (n1:{node1_label} {{{node1_id_field}: $n1_id}})
        MATCH (n2:{node2_label} {{{node2_id_field}: $n2_id}})
        CREATE (n1)-[:{relationship}]->(n2)
        """
        
        params = {
            "n1_id": node1_id,
            "n2_id": node2_id
        }
        
        try:
            self.execute_write(query, params)
            logger.debug(f"Created relationship: {node1_label}-[{relationship}]-{node2_label}")
            return True
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False
    
    def delete_node(self, label: str, id_field: str, id_value: str) -> bool:
        """Delete a node and its relationships"""
        query = f"""
        MATCH (n:{label} {{{id_field}: $id}})
        DETACH DELETE n
        """
        
        try:
            self.execute_write(query, {"id": id_value})
            logger.debug(f"Deleted {label}: {id_value}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {label}: {e}")
            return False
    
    def get_applicable_sops(self, scenario_code: str) -> List[Dict]:
        """Get applicable SOP rules for a scenario"""
        query = """
        MATCH (s:SOP)
        WHERE s.scenario_code = $scenario_code AND s.active = true
        RETURN s
        ORDER BY s.priority DESC
        """
        
        try:
            results = self.execute_query(query, {"scenario_code": scenario_code})
            return [dict(record["s"]) for record in results]
        except Exception as e:
            logger.error(f"Failed to get SOPs for {scenario_code}: {e}")
            return []


# Singleton instance
_connector: Optional[Neo4jConnector] = None


def get_neo4j_connector() -> Neo4jConnector:
    """Get or create Neo4j connector instance"""
    global _connector
    if _connector is None:
        _connector = Neo4jConnector()
    return _connector

