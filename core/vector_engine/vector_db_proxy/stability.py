"""
Stability and reliability features for vector database connections.
Includes retry logic, health checks, failover mechanisms, etc.
"""

import sys
import os
# 添加项目根目录到系统路径，以便导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import random
from functools import wraps
from typing import Callable, Any, Optional
from .chromadb_adapter import ChromaDBAdapter


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry a function on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (in seconds)
        backoff: Multiplier for delay after each retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        raise e
                    
                    # Wait before retry with exponential backoff and jitter
                    jitter = random.uniform(0, 0.1 * current_delay)
                    time.sleep(current_delay + jitter)
                    current_delay *= backoff
            
            return None
        return wrapper
    return decorator


class StabilityManager:
    """
    Manages stability and reliability features for vector database connections.
    Includes health checks, retry mechanisms, and connection validation.
    """
    
    def __init__(self, adapter: ChromaDBAdapter):
        """
        Initialize the stability manager.
        
        Args:
            adapter: The vector database adapter to manage
        """
        self.adapter = adapter
        self.health_check_interval = 30  # seconds
        self.last_health_check = 0
        self.is_healthy = True
        self.failed_attempts = 0
        self.max_failed_attempts = 5
    
    def is_connection_healthy(self) -> bool:
        """
        Check if the current connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        current_time = time.time()
        
        # Only perform health check periodically
        if (current_time - self.last_health_check) < self.health_check_interval:
            return self.is_healthy
        
        self.last_health_check = current_time
        
        try:
            # Perform a lightweight operation to test connection
            # Using heartbeat or a simple operation to verify connection
            if hasattr(self.adapter, 'client') and self.adapter.client:
                # Try to get the heartbeat from the client
                heartbeat = self.adapter.client.heartbeat()
                self.is_healthy = True
                self.failed_attempts = 0
                return True
            else:
                # Try to reconnect
                self.is_healthy = self.adapter.connect()
                if not self.is_healthy:
                    self.failed_attempts += 1
                return self.is_healthy
        except Exception as e:
            print(f"Health check failed: {str(e)}")
            self.is_healthy = False
            self.failed_attempts += 1
            return False
    
    def ensure_connection(self) -> bool:
        """
        Ensure that the connection is active and healthy.
        
        Returns:
            True if connection is established and healthy, False otherwise
        """
        if self.is_connection_healthy():
            return True
        
        # Attempt to reconnect
        if self.failed_attempts < self.max_failed_attempts:
            try:
                # Disconnect first to clean up any stale connections
                self.adapter.disconnect()
                # Reconnect
                success = self.adapter.connect()
                if success:
                    self.is_healthy = True
                    self.failed_attempts = 0
                    return True
                else:
                    self.is_healthy = False
                    self.failed_attempts += 1
                    return False
            except Exception as e:
                print(f"Reconnection attempt failed: {str(e)}")
                self.is_healthy = False
                self.failed_attempts += 1
                return False
        else:
            print("Maximum failed attempts reached, connection considered permanently failed")
            return False
    
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    def execute_with_retry(self, operation: Callable, *args, **kwargs):
        """
        Execute an operation with automatic retry on failure.
        
        Args:
            operation: The operation to execute
            *args: Arguments to pass to the operation
            **kwargs: Keyword arguments to pass to the operation
            
        Returns:
            Result of the operation
        """
        # Ensure connection is healthy before executing
        if not self.ensure_connection():
            raise Exception("Cannot execute operation: connection is not healthy")
        
        return operation(*args, **kwargs)
    
    def validate_operation_params(self, operation_name: str, params: dict) -> bool:
        """
        Validate parameters for a specific operation.
        
        Args:
            operation_name: Name of the operation
            params: Parameters for the operation
            
        Returns:
            True if parameters are valid, False otherwise
        """
        # Basic validation for common operations
        if operation_name == "add_vectors":
            required_fields = ['vectors', 'ids']
            for field in required_fields:
                if field not in params or (params[field] is not None and len(params[field]) == 0):
                    return False
            # Validate that vectors and ids have the same length
            if len(params['vectors']) != len(params['ids']):
                return False
        elif operation_name == "query_vectors":
            required_fields = ['query_vector']
            for field in required_fields:
                if field not in params or (params[field] is not None and len(params[field]) == 0):
                    return False
        elif operation_name == "delete_vectors":
            required_fields = ['ids']
            for field in required_fields:
                if field not in params or (params[field] is not None and len(params[field]) == 0):
                    return False
        
        return True
    
    def handle_transient_error(self, error: Exception) -> bool:
        """
        Determine if an error is transient and warrants a retry.
        
        Args:
            error: The error that occurred
            
        Returns:
            True if the error is transient, False otherwise
        """
        error_msg = str(error).lower()
        
        # Common transient error indicators
        transient_indicators = [
            'timeout',
            'connection refused',
            'network',
            'temporary',
            'busy',
            'congestion',
            'throttle'
        ]
        
        for indicator in transient_indicators:
            if indicator in error_msg:
                return True
        
        return False


class ConnectionMonitor:
    """
    Monitors connection health and performance metrics.
    """
    
    def __init__(self, adapter: ChromaDBAdapter):
        """
        Initialize the connection monitor.
        
        Args:
            adapter: The vector database adapter to monitor
        """
        self.adapter = adapter
        self.stats = {
            'requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'total_response_time': 0
        }
        self.response_times = []
        
    def record_request(self, success: bool, response_time: float):
        """
        Record a request and its outcome.
        
        Args:
            success: Whether the request was successful
            response_time: Time taken for the request in seconds
        """
        self.stats['requests'] += 1
        self.response_times.append(response_time)
        
        if success:
            self.stats['successful_requests'] += 1
        else:
            self.stats['failed_requests'] += 1
        
        # Update average response time
        self.stats['total_response_time'] += response_time
        self.stats['avg_response_time'] = (
            self.stats['total_response_time'] / self.stats['requests']
        )
    
    def get_performance_metrics(self) -> dict:
        """
        Get performance metrics for the connection.
        
        Returns:
            Dictionary with performance metrics
        """
        total_requests = self.stats['requests']
        success_rate = (
            (self.stats['successful_requests'] / total_requests * 100) 
            if total_requests > 0 else 0
        )
        
        return {
            'success_rate': success_rate,
            'total_requests': total_requests,
            'successful_requests': self.stats['successful_requests'],
            'failed_requests': self.stats['failed_requests'],
            'average_response_time': self.stats['avg_response_time'],
            'last_response_times': self.response_times[-10:]  # Last 10 response times
        }