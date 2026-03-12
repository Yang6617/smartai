"""
文件存储系统测试脚本
用于验证按群组划分目录的文件存储功能
"""
import os
import tempfile
from pathlib import Path
from utils.file_storage import LocalFileStorage


def test_file_storage():
    """测试文件存储系统的功能"""
    print("开始测试文件存储系统...")
    
    # 创建临时目录用于测试
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = LocalFileStorage(temp_dir)
        
        # 测试数据
        test_content = b"This is a test file content."
        test_filename = "test_file.txt"
        
        print("1. 测试个人文件存储...")
        personal_path = storage.save_file(test_content, test_filename, group_id=None)
        print(f"   个人文件存储路径: {personal_path}")
        
        # 验证文件是否保存在正确的目录下
        personal_file_path = storage.get_file_path(personal_path)
        assert "personal" in personal_file_path, f"Personal file should be stored in 'personal' directory, got: {personal_file_path}"
        print("   ✓ 个人文件存储在正确的目录中")
        
        # 加载文件验证内容
        loaded_content = storage.load_file(personal_path)
        assert loaded_content == test_content, "Loaded content does not match original content"
        print("   ✓ 个人文件内容正确")
        
        print("\n2. 测试群组文件存储...")
        group_id = 123
        group_path = storage.save_file(test_content, test_filename, group_id=group_id)
        print(f"   群组文件存储路径: {group_path}")
        
        # 验证文件是否保存在正确的群组目录下
        group_file_path = storage.get_file_path(group_path)
        assert f"group_{group_id}" in group_file_path, f"Group file should be stored in 'group_{group_id}' directory, got: {group_file_path}"
        print("   ✓ 群组文件存储在正确的目录中")
        
        # 加载文件验证内容
        loaded_content = storage.load_file(group_path)
        assert loaded_content == test_content, "Loaded content does not match original content"
        print("   ✓ 群组文件内容正确")
        
        print("\n3. 测试文件删除功能...")
        delete_result = storage.delete_file(personal_path)
        assert delete_result, "Failed to delete personal file"
        print("   ✓ 个人文件删除成功")
        
        delete_result = storage.delete_file(group_path)
        assert delete_result, "Failed to delete group file"
        print("   ✓ 群组文件删除成功")
        
        # 验证删除后的状态
        try:
            storage.load_file(personal_path)
            assert False, "Should have raised FileNotFoundError for deleted personal file"
        except FileNotFoundError:
            print("   ✓ 个人文件确实已被删除")
        
        try:
            storage.load_file(group_path)
            assert False, "Should have raised FileNotFoundError for deleted group file"
        except FileNotFoundError:
            print("   ✓ 群组文件确实已被删除")
        
        print("\n4. 测试同名文件处理...")
        # 保存第一个文件
        path1 = storage.save_file(test_content, "duplicate.txt", group_id=None)
        # 再次保存同名文件，应该生成不同的名称
        path2 = storage.save_file(test_content, "duplicate.txt", group_id=None)
        
        assert path1 != path2, "Duplicate filenames should be handled with unique naming"
        print(f"   第一个文件路径: {path1}")
        print(f"   第二个文件路径: {path2}")
        print("   ✓ 重复文件名被正确处理")
        
        print("\n✓ 所有测试通过！文件存储系统工作正常")
        

if __name__ == "__main__":
    test_file_storage()