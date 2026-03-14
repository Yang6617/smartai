# 数据库设计与文件存储方案

## 1. 数据库设计说明

### 1.1 数据库架构概述

本系统采用关系型数据库设计，主要包含以下实体：

- 用户（User）：存储系统用户的基本信息
- 群组（Group）：支持群组管理功能
- 群组成员（GroupMember）：用户与群组的多对多关系，包含角色信息
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
| role | String | 成员角色（"admin" 或 "member"），默认 "member" |
| joined_at | DateTime | 加入时间，默认为当前时间 |

**说明**：
- `role` 字段用于实现基于角色的访问控制（RBAC）
- `admin`：管理员，拥有文件上传、成员管理等权限
- `member`：普通用户，只能提问和查看信息

#### 1.2.4 file_info 表
| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | Integer (Primary Key) | 文件记录唯一标识 |
| filename | String | 存储时的文件名（相对路径，索引） |
| original_filename | String | 原始文件名 |
| file_size | Integer | 文件大小（字节） |
| content_type | String | MIME类型 |
| upload_time | DateTime | 上传时间，默认为当前时间 |
| group_id | Integer (Foreign Key) | 所属群组ID，关联 groups.id |
| file_category | String | 文件分类，默认为"general" |
| file_type | String | 文件类型（如"markdown"、"pdf"等） |

**说明**：
- `filename` 存储相对路径，格式为 `group_{id}/original_filename`
- 如果文件名冲突，会自动添加编号（如 `test_1.md`、`test_2.md`）
- `file_type` 用于区分不同类型的文件

#### 1.2.5 qa_records 表
| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | Integer (Primary Key) | 问答记录唯一标识 |
| question | Text | 用户提出的问题 |
| answer | Text | AI模型的回答 |
| sources | JSON | 引用的源文档信息（JSON格式） |
| user_id | Integer (Foreign Key) | 提问用户ID，关联 users.id |
| group_id | Integer (Foreign Key) | 所属群组ID，关联 groups.id |
| created_at | DateTime | 创建时间，默认为当前时间 |

**说明**：
- `sources` 字段存储问答过程中引用的源文档信息
- 包含文档ID、相似度分数等元数据

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
2. 系统验证文件大小（最大50MB）和类型
3. 将文件保存到 `uploads/group_{group_id}/` 目录
4. 在 `file_info` 表中创建对应的元数据记录
5. 自动触发文档预处理和向量化流程

### 2.3 文件存储路径结构

```
uploads/
└── group_{id}/
    ├── original_filename.ext
    ├── original_filename_1.ext
    ├── original_filename_2.ext
    └── ...
```

**说明**：
- 文件保存在 `uploads/group_{group_id}/` 目录下
- 使用原始文件名保存，避免UUID前缀
- 如果文件名冲突，自动添加编号（_1、_2等）

### 2.4 文件管理策略

1. **文件命名**：使用原始文件名，提高可读性；冲突时自动添加编号
2. **文件大小限制**：单个文件最大 50MB
3. **文件分类**：支持按类别组织文件（如文档、图片、视频等）
4. **安全性**：文件无法直接通过 URL 访问，必须通过下载接口
5. **权限控制**：只有群组成员可以下载该群组的文件
6. **清理机制**：当删除文件记录时，同步删除物理文件

### 2.5 文件上传 API 设计

#### POST /file/upload
- **认证**：Bearer JWT Token
- **权限**：仅群组管理员可以上传
- **表单参数**：
  - `file`: 上传的文件（必需）
  - `group_id`: 群组ID（必需，字符串类型）
  - `original_filename`: 原始文件名（可选）
  - `category`: 文件分类（可选，默认 "general"）
- **返回**：FileInfoResponse 对象

**示例**：
```bash
curl -X POST http://127.0.0.1:8003/file/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.md" \
  -F "group_id=1"
```

#### GET /file/list
- **认证**：Bearer JWT Token
- **权限**：仅群组成员可以查看
- **查询参数**：
  - `group_id`: 群组ID（必需）
- **返回**：FileInfoResponse 列表

**示例**：
```bash
curl -X GET "http://127.0.0.1:8003/file/list?group_id=1" \
  -H "Authorization: Bearer <token>"
```

#### GET /file/download/{file_id}
- **认证**：Bearer JWT Token
- **权限**：仅群组成员可以下载
- **路径参数**：
  - `file_id`: 文件ID（必需）
- **返回**：文件二进制内容（触发浏览器下载）

**示例**：
```bash
curl -X GET "http://127.0.0.1:8003/file/download/1" \
  -H "Authorization: Bearer <token>" \
  -o downloaded_file.md
```

## 3. 数据库配置

### 3.1 数据库文件位置

**SQLite 数据库文件**：
- 默认位置：`backend/fastapi_project/knowledge_system.db`
- 该文件位于项目根目录下的 `backend/fastapi_project` 目录中
- 文件会被 `.gitignore` 排除，不会提交到版本控制系统

**向量数据库位置**：
- 默认位置：`chroma_data/`（项目根目录下）
- 存储所有向量嵌入数据

### 3.2 支持的数据库类型

系统支持多种数据库：

1. **SQLite**：开发环境使用，默认路径为 `backend/fastapi_project/knowledge_system.db`
2. **PostgreSQL**：生产环境推荐，配置为 `postgresql://user:password@localhost/dbname`
3. **MySQL**：生产环境备选，配置为 `mysql+pymysql://user:password@localhost/dbname`

### 3.3 连接配置

- 通过环境变量 `DATABASE_URL` 配置数据库连接
- SQLite 使用 `connect_args={"check_same_thread": False}` 设置
- PostgreSQL 和 MySQL 使用 `pool_pre_ping=True` 确保连接有效性

### 3.4 数据库迁移

系统提供了数据库迁移脚本 `migrate_add_role.py`，用于为 `group_members` 表添加 `role` 列：

```bash
python migrate_add_role.py
```

**功能**：
- 检查 `role` 列是否已存在
- 添加 `role` 列（默认值 "member"）
- 更新现有数据，将所有现有成员设置为管理员

### 3.5 重置数据库

如需重置数据库：

```bash
python clear_database.py
```

此命令会删除 SQLite 数据库和 ChromaDB 向量数据库，下次启动时会自动重新创建。

## 4. 安全性设计

### 4.1 用户认证
- 使用 JWT (JSON Web Token) 实现无状态会话管理
- 密码使用 bcrypt 算法哈希存储
- 访问令牌有过期时间限制（默认30分钟）

### 4.2 权限控制

#### 基于角色的访问控制（RBAC）

系统实现了基于角色的访问控制（RBAC），每个群组中有两种角色：

**管理员（admin）**：
- 可以上传文件到知识库
- 可以添加新成员到群组
- 可以从群组中移除成员
- 可以提升普通用户为管理员
- 可以下载群组文件
- 可以提问和查看群组信息

**普通用户（member）**：
- 可以向知识库提问
- 可以下载群组文件
- 可以查看群组信息
- 不能上传文件
- 不能添加/移除成员
- 不能提升用户角色

#### 权限验证规则

1. **文件上传**：仅群组管理员可以上传文件
2. **文件下载**：仅群组成员可以下载该群组的文件
3. **提问**：仅群组成员可以提问（包括管理员和普通用户）
4. **成员管理**：仅管理员可以添加、移除成员和更新角色
5. **角色提升**：仅管理员可以提升用户角色

### 4.3 文件安全
- 文件大小限制（最大50MB）
- 文件上传类型验证
- 文件无法直接通过 URL 访问
- 文件下载需要权限验证

## 5. 扩展性考虑

### 5.1 文件存储扩展
未来可以考虑以下扩展方案：
1. 使用对象存储服务（如 AWS S3、阿里云OSS）替代本地存储
2. 实现分布式文件系统支持
3. 添加文件压缩和格式转换功能
4. 实现文件版本控制

### 5.2 数据库扩展
1. 分库分表策略支持大数据量
2. 读写分离提高并发能力
3. 缓存层集成（如 Redis）优化热点数据访问
4. 数据库连接池优化

### 5.3 群组管理扩展
未来可以考虑以下扩展：
1. 群组层级结构（子群组）
2. 群组模板（预设角色和权限）
3. 群组邀请链接
4. 群组操作日志

## 6. 数据库初始化

### 6.1 数据库文件位置

**SQLite 数据库文件**：
- 默认位置：`backend/fastapi_project/knowledge_system.db`
- 该文件位于项目根目录下的 `backend/fastapi_project` 目录中
- 文件会被 `.gitignore` 排除，不会提交到版本控制系统

**向量数据库位置**：
- 默认位置：`chroma_data/`（项目根目录下）
- 存储所有向量嵌入数据

### 6.2 首次运行
首次运行后端服务时，系统会自动创建所有数据库表结构。

### 6.3 重置数据库
如需重置数据库：

```bash
python clear_database.py
```

此命令会删除 SQLite 数据库和 ChromaDB 向量数据库，下次启动时会自动重新创建。

### 6.4 数据库迁移
当数据库结构发生变化时，需要运行迁移脚本：

```bash
python migrate_add_role.py
```

迁移脚本会检查当前数据库结构，只添加缺失的列，不会影响现有数据。
