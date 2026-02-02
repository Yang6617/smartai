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
            # Use consistent settings to avoid conflicts with other instances
            settings = Settings(
                persist_directory=self.config.path or "./chroma_data",
                anonymized_telemetry=False  # Disable telemetry to reduce conflicts
            )
                
            # Create client based on configuration
            # Prioritize persistent client over HTTP client to avoid connection issues
            if self.config.host and self.config.port and self.config.host != "localhost" and self.config.port != 8000:
                # For HTTP API client (only if not using default FastAPI port)
                try:
                    self.client = chromadb.HttpClient(
                        host=self.config.host,
                        port=self.config.port,
                        ssl=self.config.ssl,
                        headers={} if not self.config.api_key else {"Authorization": f"Bearer {self.config.api_key}"}
                    )
                    # Test the connection
                    _ = self.client.heartbeat()
                    return True
                except Exception as http_error:
                    print(f"HTTP connection failed: {http_error}. Falling back to persistent client.")
                    # If HTTP connection fails, fall back to persistent client
                    pass
            
            # For persistent client (default fallback)
            self.client = chromadb.PersistentClient(
                path=self.config.path or "./chroma_data",
                settings=settings
            )
                
            # Test the connection with a simple operation
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
                # 强制持久化数据到磁盘
                try:
                    if hasattr(self.client, 'persist'):
                        print("[ChromaDB Adapter] Calling persist() before disconnect")
                        self.client.persist()
                        import time
                        time.sleep(0.3)  # 等待持久化完成
                except Exception as e:
                    print(f"[ChromaDB Adapter] Persist failed: {e}")
                
            self.client = None
            self.collections.clear()  # Clear cached collections
            return True
        except Exception as e:
            print(f"Error disconnecting from ChromaDB: {str(e)}")
            return False

    def create_collection(self, collection_name: str, metadata: Optional[Dict] = None) -> bool:
        """
        Create a new collection in ChromaDB.
        If the collection already exists, this method will return True without error.
        
        Args:
            collection_name: Name of the collection to create
            metadata: Optional metadata for the collection
            
        Returns:
            True if collection creation is successful or if collection already exists, False otherwise
        """
        try:
            if self.client:
                # Check if collection already exists
                try:
                    existing_collection = self.client.get_collection(name=collection_name)
                    # If we get here, collection exists
                    print(f"Collection '{collection_name}' already exists")
                    return True
                except:
                    # Collection doesn't exist, so create it
                    self.client.create_collection(
                        name=collection_name,
                        metadata=metadata
                    )
                    print(f"Created collection '{collection_name}'")
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
        Get a reference to an existing collection, creating it if it doesn't exist.
        
        Args:
            collection_name: Name of the collection to retrieve or create
            
        Returns:
            Collection object
        """
        try:
            if self.client:
                # Try to get the collection, create it if it doesn't exist
                try:
                    collection = self.client.get_collection(name=collection_name)
                except:
                    # Collection doesn't exist, create it
                    print(f"Collection '{collection_name}' does not exist, creating it...")
                    collection = self.client.create_collection(name=collection_name)
                
                # Update cache with fresh collection reference
                self.collections[collection_name] = collection
                return collection
            else:
                raise Exception("Not connected to ChromaDB")
        except Exception as e:
            print(f"Error getting/creating collection '{collection_name}' from ChromaDB: {str(e)}")
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
                # First, try to get the collection
                collection = self.get_collection(collection_name)
                
                if not collection:
                    # Create collection if it doesn't exist
                    if not self.create_collection(collection_name):
                        return False
                    collection = self.get_collection(collection_name)
                
                # Check if the vector dimensions match the existing collection
                # If vectors list is not empty, check the first vector's dimension
                if vectors is not None and len(vectors) > 0:
                    # Convert numpy arrays to lists if needed
                    if hasattr(vectors[0], 'tolist'):
                        new_dimension = len(vectors[0].tolist())
                    else:
                        new_dimension = len(vectors[0])
                    
                    # Try to get the existing collection's dimension by retrieving one record
                    try:
                        # Attempt to get collection count to see if it's empty
                        existing_count = collection.count()
                        
                        if existing_count > 0:
                            # If collection has records, try to get one to check dimension
                            try:
                                sample_result = collection.peek(limit=1)
                                if sample_result and isinstance(sample_result, dict) and sample_result.get('embeddings') and len(sample_result['embeddings']) > 0:
                                    # Convert numpy arrays to lists if needed
                                    first_embedding = sample_result['embeddings'][0]
                                    if hasattr(first_embedding, 'tolist'):
                                        existing_dimension = len(first_embedding.tolist())
                                    else:
                                        existing_dimension = len(first_embedding)
                                    
                                    if existing_dimension != new_dimension:
                                        print(f"[ChromaDB Adapter] Dimension mismatch detected: "
                                              f"existing={existing_dimension}, new={new_dimension}")
                                        print(f"[ChromaDB Adapter] Recreating collection '{collection_name}' "
                                              f"with new dimension {new_dimension}")
                                        
                                        # Delete and recreate the collection with correct dimension
                                        self.delete_collection(collection_name)
                                        
                                        # Create new collection with the new dimension by adding first vector
                                        collection = self.client.create_collection(name=collection_name)
                                        
                                        # Add the first vector to establish the correct dimension
                                        collection.add(
                                            embeddings=[vectors[0]],
                                            ids=[ids[0]],
                                            metadatas=[metadatas[0]] if metadatas else None,
                                            documents=[documents[0]] if documents else None
                                        )
                                        
                                        # Add remaining vectors if any
                                        if len(vectors) > 1:
                                            collection.add(
                                                embeddings=vectors[1:],
                                                ids=ids[1:],
                                                metadatas=metadatas[1:] if metadatas else None,
                                                documents=documents[1:] if documents else None
                                            )
                                        return True
                            except Exception as peek_error:
                                print(f"[ChromaDB Adapter] Warning: Could not peek existing dimension: {peek_error}")
                                # Continue with normal operation
                    except Exception as count_error:
                        print(f"[ChromaDB Adapter] Warning: Could not get collection count: {count_error}")
                
                # Add embeddings to the collection
                # Ensure vectors are in the right format for ChromaDB
                if vectors is not None and len(vectors) > 0:
                    # Convert numpy arrays to lists if needed
                    processed_vectors = []
                    for v in vectors:
                        if hasattr(v, 'tolist'):
                            processed_vectors.append(v.tolist())
                        else:
                            processed_vectors.append(v)
                    
                    collection.add(
                        embeddings=processed_vectors,
                        ids=ids,
                        metadatas=metadatas,
                        documents=documents
                    )
                else:
                    print(f"[ChromaDB Adapter] Warning: No vectors to add to collection '{collection_name}'")
                    return False
                return True
            else:
                raise Exception("Not connected to ChromaDB")
        except Exception as e:
            # Handle dimension mismatch error specifically
            error_msg = str(e).lower()
            if "dimension" in error_msg and ("expecting" in error_msg or "got" in error_msg):
                print(f"[ChromaDB Adapter] Dimension mismatch error detected: {str(e)}")
                print(f"[ChromaDB Adapter] Recreating collection '{collection_name}' to fix dimension")
                
                # Delete and recreate the collection
                self.delete_collection(collection_name)
                
                # Retry creating and adding vectors to the new collection
                collection = self.get_collection(collection_name)
                if collection:
                    try:
                        collection.add(
                            embeddings=vectors,
                            ids=ids,
                            metadatas=metadatas,
                            documents=documents
                        )
                        return True
                    except Exception as retry_e:
                        print(f"[ChromaDB Adapter] Retry failed after recreating collection: {retry_e}")
                        return False
                else:
                    return False
            else:
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