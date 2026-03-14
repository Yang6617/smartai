"""
数据库迁移脚本：为 group_members 表添加 role 列
"""
from sqlalchemy import Column, String, text
from models.database_models import GroupMember, Base
from database.db_config import engine, Base as DBBase

# 创建 role 列
print("正在为 group_members 表添加 role 列...")

# 使用 ALTER TABLE 语句添加列
with engine.begin() as conn:
    # 检查列是否已存在
    result = conn.execute(text(
        "SELECT name FROM pragma_table_info('group_members') WHERE name='role'"
    ))
    if result.fetchone():
        print("role 列已存在，跳过添加")
    else:
        conn.execute(text("ALTER TABLE group_members ADD COLUMN role STRING DEFAULT 'member'"))
        print("role 列添加成功")

# 更新现有数据，将所有现有成员设置为管理员
print("正在更新现有数据...")
with engine.begin() as conn:
    conn.execute(text("UPDATE group_members SET role = 'admin' WHERE role IS NULL"))
    print("现有数据更新成功")

print("数据库迁移完成！")
