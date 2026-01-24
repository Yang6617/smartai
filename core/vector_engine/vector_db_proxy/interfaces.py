"""
Abstract interface for vector database operations.
Defines the common interface that all vector database implementations must follow.
"""

import sys
import os
# 添加项目根目录到系统路径，以便导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np


class VectorDatabaseInterface(ABC):
    """
    Abstract base class defining the interface for vector database operations.
    All vector database implementations must inherit from this class.
    """

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish a connection to the vector database.
        Returns True if connection is successful, False otherwise.
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close the connection to the vector database.
        Returns True if disconnection is successful, False otherwise.
        """
        pass

    @abstractmethod
    def create_collection(self, collection_name: str, metadata: Optional[Dict] = None) -> bool:
        """
        Create a new collection in the vector database.
        
        Args:
            collection_name: Name of the collection to create
            metadata: Optional metadata for the collection
            
        Returns:
            True if collection creation is successful, False otherwise
        """
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection from the vector database.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if collection deletion is successful, False otherwise
        """
        pass

    @abstractmethod
    def get_collection(self, collection_name: str):
        """
        Get a reference to an existing collection.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            Collection object if found, None otherwise
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_vector_count(self, collection_name: str) -> int:
        """
        Get the count of vectors in a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Number of vectors in the collection
        """
        pass

    @abstractmethod
    def reset_database(self) -> bool:
        """
        Reset the entire database (delete all collections).
        
        Returns:
            True if reset is successful, False otherwise
        """
        pass