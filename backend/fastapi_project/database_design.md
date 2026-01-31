# 数据库设计与文件存储方案

## 1. 数据库设计说明

### 1.1 数据库架构概述

本系统采用关系型数据库设计，主要包含以下实体：

- 用户（User）：存储系统用户的基本信息
- 群组（Group）：支持群组管理功能
- 群组成员（GroupMember）：用户与群组的多对多关系
- 文件信息（FileInfo）：上传文件的元数据
- 问答记录（QaRecord）：用户提问和AI回答的记录
- 收藏记录（Favorite）：用户收藏的问答记录

### 1.2 数据库表结构详解

#### 1.2.1 users 表
| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | Integer (Primary Key) | 用户唯一标识 |
| username | String | 用户名（唯一索引） |
| email | String | 邮箱（唯一索引） |
| hashed_password | String | 加密后的密码 |
| created_at | DateTime | 创建时间，默认为当前时间 |

#### 1.2.2 groups 表
| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | Integer (Primary Key) | 群组唯一标识 |
| name | String | 群组名称（索引） |
| description | Text | 群组描述 |
| owner_id | Integer (Foreign Key) | 群组所有者ID，关联 users.id |
| created_at | DateTime | 创建时间，默认为当前时间 |

#### 1.2.3 group_members 表
| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | Integer (Primary Key) | 记录唯一标识 |
| group_id | Integer (Foreign Key) | 群组ID，关联 groups.id |
| user_id | Integer (Foreign Key) | 用户ID，关联 users.id |
| joined_at | DateTime | 加入时间，默认为当前时间 |

#### 1.2.4 file_info 表
| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | Integer (Primary Key) | 文件记录唯一标识 |
| filename | String | 存储时的文件名（UUID生成，索引） |
| original_filename | String | 原始文件名 |
| file_size | Integer | 文件大小（字节） |
| content_type | String | MIME类型 |
| upload_time | DateTime | 上传时间，默认为当前时间 |
| uploader_id | Integer (Foreign Key) | 上传者ID，关联 users.id |
| group_id | Integer (Foreign Key) | 所属群组ID，关联 groups.id（可为空） |
| file_category | String | 文件分类，默认为"general" |

#### 1.2.5 qa_records 表
| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | Integer (Primary Key) | 问答记录唯一标识 |
| question | Text | 用户提出的问题 |
| answer | Text | AI模型的回答 |
| media_type | String | 媒体类型，默认为"text" |
| user_id | Integer (Foreign Key) | 提问用户ID，关联 users.id |
| group_id | Integer (Foreign Key) | 所属群组ID，关联 groups.id（可为空） |
| created_at | DateTime | 创建时间，默认为当前时间 |

#### 1.2.6 favorites 表
| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | Integer (Primary Key) | 收藏记录唯一标识 |
| user_id | Integer (Foreign Key) | 收藏者ID，关联 users.id |
| qa_record_id | Integer (Foreign Key) | 被收藏的问答ID，关联 qa_records.id |
| created_at | DateTime | 创建时间，默认为当前时间 |

## 2. 文件存储方案

### 2.1 文件存储架构

系统采用混合存储策略：

1. **元数据存储**：使用关系型数据库存储文件的元数据（名称、大小、类型等）
2. **物理文件存储**：使用本地文件系统存储实际文件内容

### 2.2 文件上传流程

1. 用户通过 `/file/upload` 接口上传文件
2. 系统生成唯一的文件名（UUID + 原始文件名）
3. 将文件保存到 [uploads/](file:///c%3A/Users/lenovo/Desktop/fastapi_project/uploads/) 目录
4. 在 [file_info](file:///c%3A/Users/lenovo/Desktop/fastapi_project/main.py#L78-L88) 表中创建对应的元数据记录

### 2.3 文件存储路径结构

```
uploads/
├── <uuid>_original_filename.ext
├── <uuid>_another_file.pdf
└── ...
```

其中 `<uuid>` 是使用 Python 的 [uuid.uuid4()](file:///c%3A/Users/lenovo/AppData/Local/Programs/Python/Python39/Lib/uuid.py#L684-L708) 生成的唯一标识符。

### 2.4 文件管理策略

1. **文件命名**：使用 UUID 确保全局唯一性，防止文件名冲突
2. **文件大小限制**：单个文件最大 50MB
3. **文件分类**：支持按类别组织文件（如文档、图片、视频等）
4. **安全性**：只存储文件的元数据，实际文件无法直接通过 URL 访问
5. **清理机制**：当删除文件记录时，同步删除物理文件

### 2.5 文件上传 API 设计

#### POST /file/upload
- 参数：
  - `file`: 上传的文件
  - `group_id` (可选): 指定群组ID
  - `category` (默认: "general"): 文件分类
- 返回：FileInfoResponse 对象

#### GET /knowledge/list
- 查询参数：
  - `group_id` (可选): 群组ID过滤
  - `category` (可选): 文件分类过滤
  - `keyword` (可选): 文件名关键词搜索
  - `skip` (默认: 0): 分页偏移量
  - `limit` (默认: 100): 最大返回数量
- 返回：FileInfoResponse 列表

## 3. 数据库配置

### 3.1 支持的数据库类型

系统支持多种数据库：

1. **SQLite**：开发环境使用，配置为 `sqlite:///./knowledge_system.db`
2. **PostgreSQL**：生产环境推荐，配置为 `postgresql://user:password@localhost/dbname`
3. **MySQL**：生产环境备选，配置为 `mysql+pymysql://user:password@localhost/dbname`

### 3.2 连接配置

- 通过环境变量 [DATABASE_URL](file:///c%3A/Users/lenovo/Desktop/fastapi_project/main.py#L32-L36) 配置数据库连接
- SQLite 使用 `connect_args={"check_same_thread": False}` 设置
- PostgreSQL 和 MySQL 使用 `pool_pre_ping=True` 确保连接有效性

## 4. 安全性设计

### 4.1 用户认证
- 使用 JWT (JSON Web Token) 实现无状态会话管理
- 密码使用 bcrypt 算法哈希存储
- 访问令牌有过期时间限制

### 4.2 权限控制
- 用户只能访问自己上传的文件或所属群组的文件
- 问答记录和收藏记录也受相同权限限制
- 文件上传有大小限制和类型验证

## 5. 扩展性考虑

### 5.1 文件存储扩展
未来可以考虑以下扩展方案：
1. 使用对象存储服务（如 AWS S3、阿里云OSS）替代本地存储
2. 实现分布式文件系统支持
3. 添加文件压缩和格式转换功能

### 5.2 数据库扩展
1. 分库分表策略支持大数据量
2. 读写分离提高并发能力
3. 缓存层集成（如 Redis）优化热点数据访问