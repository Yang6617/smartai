"""
Tests for the vector database proxy layer.
"""

import unittest
import sys
import os
# 添加项目根目录到系统路径，以便导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from unittest.mock import Mock, patch, MagicMock
from core.vector_engine.vector_db_proxy.config import VectorDBConfig
from core.vector_engine.vector_db_proxy.interfaces import VectorDatabaseInterface
from core.vector_engine.vector_db_proxy.chromadb_adapter import ChromaDBAdapter
from core.vector_engine.vector_db_proxy.proxy import VectorDBProxy, create_vector_db_proxy
from core.vector_engine.vector_db_proxy.pool_manager import VectorDBPool
from core.vector_engine.vector_db_proxy.stability import StabilityManager


class TestVectorDBConfig(unittest.TestCase):
    """Test the VectorDBConfig class."""
    
    def test_config_creation(self):
        """Test creating a VectorDBConfig instance."""
        config = VectorDBConfig(
            db_type="chromadb",
            host="localhost",
            port=8000,
            path="./test_data",
            pool_size=5,
            max_overflow=10
        )
        
        self.assertEqual(config.db_type, "chromadb")
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 8000)
        self.assertEqual(config.path, "./test_data")
        self.assertEqual(config.pool_size, 5)
        self.assertEqual(config.max_overflow, 10)


class TestVectorDatabaseInterface(unittest.TestCase):
    """Test the abstract VectorDatabaseInterface."""
    
    def test_interface_abstract_methods(self):
        """Verify that the interface has all required methods."""
        # Check that VectorDatabaseInterface is abstract
        self.assertTrue(hasattr(VectorDatabaseInterface, '__abstractmethods__'))
        
        # Check for required methods
        required_methods = {
            'connect', 'disconnect', 'create_collection', 'delete_collection',
            'get_collection', 'add_vectors', 'query_vectors', 'delete_vectors',
            'get_vector_count', 'reset_database'
        }
        
        abstract_methods = VectorDatabaseInterface.__abstractmethods__
        self.assertEqual(abstract_methods, required_methods)


class TestChromaDBAdapter(unittest.TestCase):
    """Test the ChromaDBAdapter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = VectorDBConfig(db_type="chromadb", path="./test_chroma_data", host="", port=0)
        self.adapter = ChromaDBAdapter(self.config)
    
    @patch('core.vector_engine.vector_db_proxy.chromadb_adapter.get_chromadb_client')
    def test_connect_method(self, mock_chromadb_module):
        """Test the connect method."""
        # Mock the PersistentClient and its heartbeat method
        mock_client = Mock()
        mock_client.heartbeat.return_value = 12345
        mock_chromadb_module.PersistentClient.return_value = mock_client
        # Also mock HttpClient in case it's needed
        mock_chromadb_module.HttpClient.return_value = mock_client
        
        result = self.adapter.connect()
        
        self.assertTrue(result)
        self.assertIsNotNone(self.adapter.client)
        mock_chromadb_module.PersistentClient.assert_called_once()
    
    def test_required_methods_exist(self):
        """Verify that ChromaDBAdapter implements all required interface methods."""
        methods = [
            'connect', 'disconnect', 'create_collection', 'delete_collection',
            'get_collection', 'add_vectors', 'query_vectors', 'delete_vectors',
            'get_vector_count', 'reset_database'
        ]
        
        for method in methods:
            self.assertTrue(hasattr(self.adapter, method))
            self.assertTrue(callable(getattr(self.adapter, method)))


class TestVectorDBPool(unittest.TestCase):
    """Test the VectorDBPool class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = VectorDBConfig(
            db_type="chromadb",
            path="./test_pool_data",
            pool_size=2,
            max_overflow=1
        )
        self.pool = VectorDBPool(self.config)
    
    def test_pool_initialization(self):
        """Test that the pool initializes with correct parameters."""
        self.assertEqual(self.pool.pool_size, 2)
        self.assertEqual(self.pool.max_overflow, 1)
        self.assertEqual(self.pool.timeout, 30)  # default value
        self.assertEqual(self.pool.recycle_time, 3600)  # default value
    
    @patch('core.vector_engine.vector_db_proxy.pool_manager.ChromaDBAdapter')
    def test_create_connection(self, mock_adapter_class):
        """Test creating a connection."""
        mock_adapter_instance = Mock()
        mock_adapter_instance.connect.return_value = True
        mock_adapter_class.return_value = mock_adapter_instance
        
        # Override the config to use chromadb
        self.config.db_type = "chromadb"
        
        conn = self.pool._create_connection()
        
        self.assertIsNotNone(conn)
        mock_adapter_class.assert_called_once()


class TestStabilityManager(unittest.TestCase):
    """Test the StabilityManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_adapter = Mock(spec=ChromaDBAdapter)
        self.stability_manager = StabilityManager(self.mock_adapter)
    
    def test_is_connection_healthy(self):
        """Test the health check method."""
        # Mock the client heartbeat
        mock_client = Mock()
        mock_client.heartbeat.return_value = 12345
        self.mock_adapter.client = mock_client
        
        result = self.stability_manager.is_connection_healthy()
        
        self.assertTrue(result)
        self.assertTrue(self.stability_manager.is_healthy)
    
    def test_validate_operation_params(self):
        """Test parameter validation."""
        # Test valid add_vectors params
        valid_add_params = {
            'vectors': [[1.0, 2.0], [3.0, 4.0]],
            'ids': ['id1', 'id2']
        }
        result = self.stability_manager.validate_operation_params('add_vectors', valid_add_params)
        self.assertTrue(result)
        
        # Test invalid add_vectors params (missing vectors)
        invalid_add_params = {'ids': ['id1']}
        result = self.stability_manager.validate_operation_params('add_vectors', invalid_add_params)
        self.assertFalse(result)
        
        # Test valid query_vectors params
        valid_query_params = {'query_vector': [1.0, 2.0]}
        result = self.stability_manager.validate_operation_params('query_vectors', valid_query_params)
        self.assertTrue(result)


class TestVectorDBProxy(unittest.TestCase):
    """Test the VectorDBProxy class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = VectorDBConfig(
            db_type="chromadb",
            path="./test_proxy_data",
            pool_size=2
        )
        self.proxy = VectorDBProxy(self.config)
    
    def test_proxy_initialization(self):
        """Test that the proxy initializes correctly."""
        self.assertIsInstance(self.proxy.config, VectorDBConfig)
        self.assertIsNotNone(self.proxy.pool)
        self.assertIsNotNone(self.proxy.current_adapter)
        self.assertIsNotNone(self.proxy.stability_manager)
        self.assertIsNotNone(self.proxy.monitor)
    
    @patch.object(ChromaDBAdapter, 'connect')
    def test_connect_method(self, mock_connect):
        """Test the connect method."""
        mock_connect.return_value = True
        
        result = self.proxy.connect()
        
        self.assertTrue(result)
        mock_connect.assert_called_once()
    
    @patch.object(ChromaDBAdapter, 'create_collection')
    def test_create_collection(self, mock_create_collection):
        """Test the create_collection method."""
        mock_create_collection.return_value = True
        
        result = self.proxy.create_collection("test_collection")
        
        self.assertTrue(result)
        mock_create_collection.assert_called_once_with("test_collection", None)


class TestCreateVectorDBProxy(unittest.TestCase):
    """Test the create_vector_db_proxy factory function."""
    
    def test_create_proxy(self):
        """Test creating a proxy with default parameters."""
        proxy = create_vector_db_proxy()
        
        self.assertIsInstance(proxy, VectorDBProxy)
        self.assertEqual(proxy.config.db_type, "chromadb")
        self.assertEqual(proxy.config.host, "localhost")
        self.assertEqual(proxy.config.pool_size, 10)


if __name__ == '__main__':
    unittest.main()