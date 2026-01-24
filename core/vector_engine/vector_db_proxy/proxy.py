"""
Main vector database proxy class that orchestrates all components.
Provides a unified interface for vector database operations with connection pooling
and stability features.
"""

import time
import sys
import os
# 添加项目根目录到系统路径，以便导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .config import VectorDBConfig
from .pool_manager import VectorDBPool
from .stability import StabilityManager, ConnectionMonitor
from .adapters import VectorDBAdapterFactory
from typing import List, Dict, Any, Optional


class VectorDBProxy:
    """
    Main proxy class for vector database operations.
    Orchestrates connection pooling, stability features, and database operations.
    """
    
    def __init__(self, config: VectorDBConfig):
        """
        Initialize the vector database proxy with configuration.
        
        Args:
            config: Configuration object for the vector database
        """
        self.config = config
        self.pool = VectorDBPool(config)
        try:
            from .adapters import VectorDBAdapterFactory
            self.adapter_factory = VectorDBAdapterFactory
        except ImportError:
            from core.vector_engine.adapters import VectorDBAdapterFactory
            self.adapter_factory = VectorDBAdapterFactory
        self.current_adapter = None
        
        # Initialize with a single adapter for the configured database type
        self.current_adapter = self.adapter_factory.create_adapter(config)
        
        # Initialize stability manager and monitor
        self.stability_manager = StabilityManager(self.current_adapter)
        self.monitor = ConnectionMonitor(self.current_adapter)
        
        # Initialize the connection pool
        self.pool.initialize_pool()
    
    def connect(self) -> bool:
        """
        Establish connection to the vector database.
        
        Returns:
            True if connection is successful, False otherwise
        """
        return self.current_adapter.connect()
    
    def disconnect(self) -> bool:
        """
        Close connection to the vector database.
        
        Returns:
            True if disconnection is successful, False otherwise
        """
        # Close all pooled connections
        self.pool.close_all_connections()
        # Disconnect the main adapter
        return self.current_adapter.disconnect()
    
    def create_collection(self, collection_name: str, metadata: Optional[Dict] = None) -> bool:
        """
        Create a new collection in the vector database.
        
        Args:
            collection_name: Name of the collection to create
            metadata: Optional metadata for the collection
            
        Returns:
            True if collection creation is successful, False otherwise
        """
        def op():
            start_time = time.time()
            try:
                result = self.current_adapter.create_collection(collection_name, metadata)
                self.monitor.record_request(True, time.time() - start_time)
                return result
            except Exception as e:
                self.monitor.record_request(False, time.time() - start_time)
                raise e
        
        return self.stability_manager.execute_with_retry(op)
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection from the vector database.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if collection deletion is successful, False otherwise
        """
        def op():
            start_time = time.time()
            try:
                result = self.current_adapter.delete_collection(collection_name)
                self.monitor.record_request(True, time.time() - start_time)
                return result
            except Exception as e:
                self.monitor.record_request(False, time.time() - start_time)
                raise e
        
        return self.stability_manager.execute_with_retry(op)
    
    def get_collection(self, collection_name: str):
        """
        Get a reference to an existing collection.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            Collection object if found, None otherwise
        """
        def op():
            start_time = time.time()
            try:
                result = self.current_adapter.get_collection(collection_name)
                self.monitor.record_request(True, time.time() - start_time)
                return result
            except Exception as e:
                self.monitor.record_request(False, time.time() - start_time)
                raise e
        
        return self.stability_manager.execute_with_retry(op)
    
    def add_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        ids: List[str],
        metadatas: Optional[List[Dict]] = None,
        documents: Optional[List[str]] = None
    ) -> bool:
        """
        Add vectors to a collection.
        
        Args:
            collection_name: Name of the collection to add vectors to
            vectors: List of vectors to add
            ids: List of unique IDs for the vectors
            metadatas: Optional list of metadata dictionaries
            documents: Optional list of document texts
            
        Returns:
            True if vectors were added successfully, False otherwise
        """
        # Validate parameters
        params = {
            'vectors': vectors,
            'ids': ids,
            'metadatas': metadatas,
            'documents': documents
        }
        
        if not self.stability_manager.validate_operation_params('add_vectors', params):
            raise ValueError("Invalid parameters for add_vectors operation")
        
        def op():
            start_time = time.time()
            try:
                result = self.current_adapter.add_vectors(
                    collection_name, vectors, ids, metadatas, documents
                )
                self.monitor.record_request(True, time.time() - start_time)
                return result
            except Exception as e:
                self.monitor.record_request(False, time.time() - start_time)
                raise e
        
        return self.stability_manager.execute_with_retry(op)
    
    def query_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        n_results: int = 10,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for similar vectors in a collection.
        
        Args:
            collection_name: Name of the collection to query
            query_vector: Vector to find similarities for
            n_results: Number of results to return
            where: Optional filter conditions
            where_document: Optional document filter conditions
            
        Returns:
            List of results containing similar vectors and their metadata
        """
        # Validate parameters
        params = {
            'query_vector': query_vector,
            'n_results': n_results
        }
        
        if not self.stability_manager.validate_operation_params('query_vectors', params):
            raise ValueError("Invalid parameters for query_vectors operation")
        
        def op():
            start_time = time.time()
            try:
                result = self.current_adapter.query_vectors(
                    collection_name, query_vector, n_results, where, where_document
                )
                self.monitor.record_request(True, time.time() - start_time)
                return result
            except Exception as e:
                self.monitor.record_request(False, time.time() - start_time)
                raise e
        
        return self.stability_manager.execute_with_retry(op)
    
    def delete_vectors(
        self,
        collection_name: str,
        ids: List[str],
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> bool:
        """
        Delete vectors from a collection.
        
        Args:
            collection_name: Name of the collection to delete from
            ids: List of vector IDs to delete
            where: Optional filter conditions
            where_document: Optional document filter conditions
            
        Returns:
            True if deletion is successful, False otherwise
        """
        # Validate parameters
        params = {
            'ids': ids,
            'where': where,
            'where_document': where_document
        }
        
        if not self.stability_manager.validate_operation_params('delete_vectors', params):
            raise ValueError("Invalid parameters for delete_vectors operation")
        
        def op():
            start_time = time.time()
            try:
                result = self.current_adapter.delete_vectors(
                    collection_name, ids, where, where_document
                )
                self.monitor.record_request(True, time.time() - start_time)
                return result
            except Exception as e:
                self.monitor.record_request(False, time.time() - start_time)
                raise e
        
        return self.stability_manager.execute_with_retry(op)
    
    def get_vector_count(self, collection_name: str) -> int:
        """
        Get the count of vectors in a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Number of vectors in the collection
        """
        def op():
            start_time = time.time()
            try:
                result = self.current_adapter.get_vector_count(collection_name)
                self.monitor.record_request(True, time.time() - start_time)
                return result
            except Exception as e:
                self.monitor.record_request(False, time.time() - start_time)
                raise e
        
        return self.stability_manager.execute_with_retry(op)
    
    def reset_database(self) -> bool:
        """
        Reset the entire database (delete all collections).
        
        Returns:
            True if reset is successful, False otherwise
        """
        def op():
            start_time = time.time()
            try:
                result = self.current_adapter.reset_database()
                self.monitor.record_request(True, time.time() - start_time)
                return result
            except Exception as e:
                self.monitor.record_request(False, time.time() - start_time)
                raise e
        
        return self.stability_manager.execute_with_retry(op)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database proxy.
        
        Returns:
            Dictionary with proxy statistics
        """
        return {
            'pool_stats': self.pool.get_stats(),
            'performance_metrics': self.monitor.get_performance_metrics(),
            'is_healthy': self.stability_manager.is_connection_healthy()
        }


# Convenience function to create a proxy with default configuration
def create_vector_db_proxy(
    db_type: str = "chromadb",
    host: str = "localhost",
    port: int = 8000,
    path: Optional[str] = "./chroma_data",
    api_key: Optional[str] = None,
    pool_size: int = 10,
    max_overflow: int = 20
) -> VectorDBProxy:
    """
    Create a vector database proxy with default configuration.
    
    Args:
        db_type: Type of vector database ('chromadb', 'pinecone', etc.)
        host: Host address for the database
        port: Port number for the database
        path: Path for local storage (for ChromaDB)
        api_key: API key if required by the database
        pool_size: Size of the connection pool
        max_overflow: Maximum overflow connections
        
    Returns:
        Configured VectorDBProxy instance
    """
    config = VectorDBConfig(
        db_type=db_type,
        host=host,
        port=port,
        path=path,
        api_key=api_key,
        pool_size=pool_size,
        max_overflow=max_overflow
    )
    
    return VectorDBProxy(config)