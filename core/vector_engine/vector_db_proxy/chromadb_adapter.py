"""
ChromaDB implementation of the VectorDatabaseInterface.
"""

import sys
import os
# 添加项目根目录到系统路径，以便导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .interfaces import VectorDatabaseInterface
from typing import List, Dict, Any, Optional
import numpy as np


def get_chromadb_client():
    """
    Helper function to import and return chromadb client.
    This makes it easier to mock during testing.
    """
    try:
        import chromadb
        return chromadb
    except ImportError:
        # For testing purposes when chromadb is not available
        raise ImportError("chromadb package is not installed. Please install it using 'pip install chromadb'")


class ChromaDBAdapter(VectorDatabaseInterface):
    """
    ChromaDB implementation of the VectorDatabaseInterface.
    Provides concrete implementation of vector database operations using ChromaDB.
    """
    
    def __init__(self, config):
        """
        Initialize the ChromaDB adapter with configuration.
        
        Args:
            config: Configuration object containing connection parameters
        """
        self.config = config
        self.client = None
        self.collections = {}
        
    def connect(self) -> bool:
        """
        Establish a connection to the ChromaDB instance.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            chromadb = get_chromadb_client()
            from chromadb.config import Settings
            
            # Configure settings based on provided config
            settings = Settings()
            
            if self.config.path:
                settings = Settings(persist_directory=self.config.path)
                
            # Create client based on configuration
            if self.config.host and self.config.port:
                # For HTTP API client
                self.client = chromadb.HttpClient(
                    host=self.config.host,
                    port=self.config.port,
                    ssl=self.config.ssl,
                    headers={} if not self.config.api_key else {"Authorization": f"Bearer {self.config.api_key}"}
                )
            else:
                # For persistent client
                self.client = chromadb.PersistentClient(
                    path=self.config.path or "./chroma_data",
                    settings=settings
                )
                
            # Test the connection
            _ = self.client.heartbeat()
            return True
            
        except ImportError:
            raise Exception("chromadb package is not installed. Please install it using 'pip install chromadb'")
        except Exception as e:
            print(f"Error connecting to ChromaDB: {str(e)}")
            return False

    def disconnect(self) -> bool:
        """
        Close the connection to the ChromaDB instance.
        
        Returns:
            True if disconnection is successful, False otherwise
        """
        try:
            if self.client:
                # ChromaDB doesn't have explicit disconnect method
                # We'll just clean up references
                self.collections.clear()
                self.client = None
                return True
            return True  # Already disconnected
        except Exception as e:
            print(f"Error disconnecting from ChromaDB: {str(e)}")
            return False

    def create_collection(self, collection_name: str, metadata: Optional[Dict] = None) -> bool:
        """
        Create a new collection in ChromaDB.
        
        Args:
            collection_name: Name of the collection to create
            metadata: Optional metadata for the collection
            
        Returns:
            True if collection creation is successful, False otherwise
        """
        try:
            if self.client:
                # Create collection with optional metadata
                self.client.create_collection(
                    name=collection_name,
                    metadata=metadata
                )
                return True
            else:
                raise Exception("Not connected to ChromaDB")
        except Exception as e:
            print(f"Error creating collection '{collection_name}' in ChromaDB: {str(e)}")
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection from ChromaDB.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if collection deletion is successful, False otherwise
        """
        try:
            if self.client:
                self.client.delete_collection(name=collection_name)
                # Remove from local cache
                if collection_name in self.collections:
                    del self.collections[collection_name]
                return True
            else:
                raise Exception("Not connected to ChromaDB")
        except Exception as e:
            print(f"Error deleting collection '{collection_name}' from ChromaDB: {str(e)}")
            return False

    def get_collection(self, collection_name: str):
        """
        Get a reference to an existing collection.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            Collection object if found, None otherwise
        """
        try:
            if self.client:
                if collection_name in self.collections:
                    return self.collections[collection_name]
                
                collection = self.client.get_collection(name=collection_name)
                self.collections[collection_name] = collection
                return collection
            else:
                raise Exception("Not connected to ChromaDB")
        except Exception as e:
            print(f"Error getting collection '{collection_name}' from ChromaDB: {str(e)}")
            return None

    def add_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        ids: List[str],
        metadatas: Optional[List[Dict]] = None,
        documents: Optional[List[str]] = None
    ) -> bool:
        """
        Add vectors to a collection in ChromaDB.
        
        Args:
            collection_name: Name of the collection to add vectors to
            vectors: List of vectors to add
            ids: List of unique IDs for the vectors
            metadatas: Optional list of metadata dictionaries
            documents: Optional list of document texts
            
        Returns:
            True if vectors were added successfully, False otherwise
        """
        try:
            if self.client:
                collection = self.get_collection(collection_name)
                if not collection:
                    # Create collection if it doesn't exist
                    if not self.create_collection(collection_name):
                        return False
                    collection = self.get_collection(collection_name)
                
                # Add embeddings to the collection
                collection.add(
                    embeddings=vectors,
                    ids=ids,
                    metadatas=metadatas,
                    documents=documents
                )
                return True
            else:
                raise Exception("Not connected to ChromaDB")
        except Exception as e:
            print(f"Error adding vectors to collection '{collection_name}' in ChromaDB: {str(e)}")
            return False

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
        try:
            if self.client:
                collection = self.get_collection(collection_name)
                if not collection:
                    return []
                
                # Perform similarity search
                results = collection.query(
                    query_embeddings=[query_vector],
                    n_results=n_results,
                    where=where,
                    where_document=where_document
                )
                
                # Format results to match expected interface
                formatted_results = []
                
                # Check if results contain data
                if 'ids' in results and len(results['ids']) > 0 and len(results['ids'][0]) > 0:
                    for i in range(len(results['ids'][0])):
                        result = {
                            'id': results['ids'][0][i],
                            'distance': results['distances'][0][i] if 'distances' in results and results['distances'] and i < len(results['distances'][0]) else None,
                            'metadata': results['metadatas'][0][i] if 'metadatas' in results and results['metadatas'] and i < len(results['metadatas'][0]) else None,
                            'document': results['documents'][0][i] if 'documents' in results and results['documents'] and i < len(results['documents'][0]) else None,
                            'embedding': results['embeddings'][0][i] if 'embeddings' in results and results['embeddings'] and i < len(results['embeddings'][0]) else None
                        }
                        formatted_results.append(result)
                
                return formatted_results
            else:
                raise Exception("Not connected to ChromaDB")
        except Exception as e:
            print(f"Error querying vectors from collection '{collection_name}' in ChromaDB: {str(e)}")
            return []

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
        try:
            if self.client:
                collection = self.get_collection(collection_name)
                if not collection:
                    return False
                
                # Delete by IDs or filters
                collection.delete(
                    ids=ids,
                    where=where,
                    where_document=where_document
                )
                return True
            else:
                raise Exception("Not connected to ChromaDB")
        except Exception as e:
            print(f"Error deleting vectors from collection '{collection_name}' in ChromaDB: {str(e)}")
            return False

    def get_vector_count(self, collection_name: str) -> int:
        """
        Get the count of vectors in a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Number of vectors in the collection
        """
        try:
            if self.client:
                collection = self.get_collection(collection_name)
                if collection:
                    return collection.count()
                return 0
            else:
                raise Exception("Not connected to ChromaDB")
        except Exception as e:
            print(f"Error getting vector count for collection '{collection_name}' in ChromaDB: {str(e)}")
            return 0

    def reset_database(self) -> bool:
        """
        Reset the entire database (delete all collections).
        
        Returns:
            True if reset is successful, False otherwise
        """
        try:
            if self.client:
                # Get all collection names
                collections = self.client.list_collections()
                
                # Delete each collection
                for collection in collections:
                    self.client.delete_collection(name=collection.name)
                    
                # Clear local cache
                self.collections.clear()
                return True
            else:
                raise Exception("Not connected to ChromaDB")
        except Exception as e:
            print(f"Error resetting ChromaDB: {str(e)}")
            return False