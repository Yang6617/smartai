"""
Connection pool manager for vector database connections.
Manages multiple connections to ensure efficient resource usage and stable connections.
"""

import sys
import os
# 添加项目根目录到系统路径，以便导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import threading
import time
from queue import Queue, Empty
from contextlib import contextmanager
from typing import Dict, Optional, Any
from .config import VectorDBConfig
from .chromadb_adapter import ChromaDBAdapter


class VectorDBPool:
    """
    Connection pool manager for vector database connections.
    Handles creation, management, and cleanup of vector database connections.
    """
    
    def __init__(self, config: VectorDBConfig):
        """
        Initialize the connection pool with configuration.
        
        Args:
            config: Configuration object for the vector database
        """
        self.config = config
        self.pool_size = config.pool_size
        self.max_overflow = config.max_overflow
        self.timeout = config.pool_timeout
        self.recycle_time = config.pool_recycle
        
        # Thread-safe queue for managing connections
        self._pool_lock = threading.Lock()
        self._pool = Queue(maxsize=self.pool_size + self.max_overflow)
        self._active_connections = 0
        self._created_connections = 0
        
        # Track connection creation time for recycling
        self._connection_timestamps = {}
        
        # Statistics
        self._stats = {
            'total_requests': 0,
            'misses': 0,
            'errors': 0
        }
        
    def _create_connection(self):
        """
        Create a new vector database connection.
        
        Returns:
            New vector database connection instance
        """
        try:
            # Create appropriate adapter based on config
            if self.config.db_type.lower() == "chromadb":
                conn = ChromaDBAdapter(self.config)
                if conn.connect():
                    conn_id = id(conn)
                    self._connection_timestamps[conn_id] = time.time()
                    return conn
                else:
                    raise Exception("Failed to connect to ChromaDB")
            else:
                raise ValueError(f"Unsupported database type: {self.config.db_type}")
        except Exception as e:
            print(f"Error creating connection: {str(e)}")
            raise
    
    def _get_connection(self):
        """
        Get a connection from the pool or create a new one if needed.
        
        Returns:
            Vector database connection
        """
        with self._pool_lock:
            self._stats['total_requests'] += 1
            
            # Try to get an existing connection from the pool
            try:
                conn = self._pool.get_nowait()
                
                # Check if connection needs to be recycled
                conn_id = id(conn)
                if (time.time() - self._connection_timestamps.get(conn_id, 0)) > self.recycle_time:
                    self._recycle_connection(conn)
                    conn = self._create_connection()
                
                return conn
            except Empty:
                # No available connections, check if we can create more
                if self._active_connections < (self.pool_size + self.max_overflow):
                    conn = self._create_connection()
                    self._active_connections += 1
                    self._created_connections += 1
                    return conn
                else:
                    # Pool is full, wait for a connection to become available
                    try:
                        return self._pool.get(timeout=self.timeout)
                    except Empty:
                        self._stats['errors'] += 1
                        raise Exception("Timeout waiting for vector database connection")
    
    def _return_connection(self, conn):
        """
        Return a connection to the pool.
        
        Args:
            conn: Vector database connection to return
        """
        with self._pool_lock:
            # Check if we're still under capacity
            if self._pool.qsize() < self.pool_size:
                # Check if connection is still valid
                if self._is_connection_valid(conn):
                    conn_id = id(conn)
                    self._connection_timestamps[conn_id] = time.time()
                    self._pool.put(conn)
                else:
                    # Connection is invalid, remove it
                    self._active_connections -= 1
            else:
                # Pool is full, close the connection
                self._close_connection(conn)
                self._active_connections -= 1
    
    def _recycle_connection(self, conn):
        """
        Recycle an old connection.
        
        Args:
            conn: Vector database connection to recycle
        """
        self._close_connection(conn)
        conn_id = id(conn)
        if conn_id in self._connection_timestamps:
            del self._connection_timestamps[conn_id]
        self._active_connections -= 1
    
    def _close_connection(self, conn):
        """
        Close a vector database connection.
        
        Args:
            conn: Vector database connection to close
        """
        try:
            conn.disconnect()
        except:
            # Ignore errors during disconnect
            pass
    
    def _is_connection_valid(self, conn):
        """
        Check if a connection is still valid.
        
        Args:
            conn: Vector database connection to check
            
        Returns:
            True if connection is valid, False otherwise
        """
        # For now, we'll assume the connection is valid
        # In a real implementation, we might ping the database
        return True
    
    @contextmanager
    def get_connection(self):
        """
        Context manager to safely acquire and return a connection.
        
        Yields:
            Vector database connection
        """
        conn = None
        try:
            conn = self._get_connection()
            yield conn
        except Exception as e:
            self._stats['errors'] += 1
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def initialize_pool(self):
        """
        Pre-populate the connection pool with initial connections.
        """
        with self._pool_lock:
            for _ in range(self.pool_size):
                try:
                    conn = self._create_connection()
                    self._pool.put(conn)
                    self._active_connections += 1
                    self._created_connections += 1
                except Exception as e:
                    print(f"Warning: Failed to create initial connection: {str(e)}")
    
    def close_all_connections(self):
        """
        Close all connections in the pool.
        """
        with self._pool_lock:
            # Drain the pool and close all connections
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    self._close_connection(conn)
                    self._active_connections -= 1
                except Empty:
                    break
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the connection pool.
        
        Returns:
            Dictionary with connection pool statistics
        """
        with self._pool_lock:
            return {
                'pool_size': self.pool_size,
                'max_overflow': self.max_overflow,
                'active_connections': self._active_connections,
                'available_connections': self._pool.qsize(),
                'created_connections': self._created_connections,
                'total_requests': self._stats['total_requests'],
                'misses': self._stats['misses'],
                'errors': self._stats['errors']
            }