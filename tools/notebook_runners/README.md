# Jupyter Notebook Runner

专业的 Notebook 执行和管理工具，支持无状态执行、依赖检测和完整操作能力。

## 🎯 工具定位

**核心工具**：提供完整的Jupyter Notebook操作、执行、分析能力  
**标准接口**：通过 `notebook_wrapper.sh` 提供统一的调用接口  
**双重价值**：既支持Agent系统集成，又支持开发者直接使用

### 推荐调用方式

**Agent系统集成**：通过wrapper脚本统一调用
```bash
bash tools/notebook_runners/notebook_wrapper.sh <operation> <notebook_path> [params...]
```

**直接开发调试**：直接使用nb_runner.py命令
```bash
python tools/notebook_runners/nb_runner.py notebook.ipynb [options]
```

## 🚀 快速开始

### 最常用命令
```bash
# 1. 逐Cell执行验证（推荐）
python tools/notebook_runners/nb_runner.py notebook.ipynb --cells "0,1,2,3" --show-output

# 2. 查看执行状态
python tools/notebook_runners/nb_runner.py notebook.ipynb --status

# 3. 完整执行验证
python tools/notebook_runners/nb_runner.py notebook.ipynb --all --show-output

# 4. 查看结构和依赖
python tools/notebook_runners/nb_runner.py notebook.ipynb --status structure
python tools/notebook_runners/nb_runner.py notebook.ipynb --status deps

# 5. 预览模式使用
python tools/notebook_runners/nb_runner.py notebook.ipynb --enter-preview      # 进入预览模式
python tools/notebook_runners/nb_runner.py notebook.ipynb --insert-cell 0 --code-stdin  # [PREVIEW] 插入cell
python tools/notebook_runners/nb_runner.py notebook.ipynb --exit-preview       # 退出并丢弃更改
python tools/notebook_runners/nb_runner.py notebook.ipynb --exit-preview keep  # 退出并保留更改
```

### 环境要求
- **Python 3.7+**
- **Python依赖**: `pip install nbformat nbconvert jupyter jupyter-client`
- **Claude Code权限**: `"Bash(python tools/notebook_runners/nb_runner.py:*)"`

---

## 🔧 Wrapper脚本调用 (推荐方式)

### 统一调用接口

**标准调用格式**：
```bash
bash tools/notebook_runners/notebook_wrapper.sh <operation> <notebook_path> [params...]
```

**核心优势**：
- **编码处理**：自动处理Windows环境UTF-8编码问题
- **参数标准化**：统一的操作接口和参数格式
- **错误处理**：完善的错误恢复和重试机制
- **文件传递**：支持通过文件路径传递代码内容，避免引号冲突

### Wrapper操作映射表

#### 🚀 执行类操作
| Wrapper操作 | nb_runner等价命令 | 说明 |
|-------------|------------------|------|
| `execute_all` | `--all --show-output` | 执行整个notebook |
| `execute_cells <cells>` | `--cells "<cells>" --show-output` | 执行指定cells |

#### 🔍 查询类操作
| Wrapper操作 | nb_runner等价命令 | 说明 |
|-------------|------------------|------|
| `get_structure` | `--status structure` | 获取notebook结构信息 |
| `get_status` | `--status` | 获取详细执行状态 |
| `get_exec_status` | `--status exec` | 获取执行状态统计 |
| `get_dependencies` | `--status deps` | 分析cell依赖关系 |
| `get_errors` | `--status errors` | 查找错误cell |
| `get_all_status` | `--status all` | 获取完整状态信息 |
| `get_cell <index>` | `--get <index>` | 获取指定cell信息 |
| `get_cell_output <index>` | `--get <index> --output-only` | 获取指定cell输出信息 |
| `search <text>` | `--search "<text>"` | 搜索包含文本的cell |

#### ✏️ 编辑类操作
| Wrapper操作 | nb_runner等价命令 | 说明 | 文件支持 |
|-------------|------------------|------|----------|
| `create` | `--create` | 创建空白notebook | ❌ |
| `insert_cell_file <pos> <type> <file>` | `--insert-cell <pos> <type> --code-stdin` | 从文件插入cell | ✅ |
| `edit_cell_file <index> <file>` | `--edit-cell <index> --code-stdin` | 从文件编辑cell | ✅ |
| `delete_cell <index>` | `--delete-cell <index>` | 删除cell | ❌ |
| `move_cell <from> <to>` | `--move-cell <from> <to>` | 移动cell位置 | ❌ |
| `copy_cell <from> <to>` | `--copy-cell <from> <to>` | 复制cell | ❌ |
| `convert_cell <index> <type>` | `--convert-cell <index> <type>` | 转换cell类型 | ❌ |
| `clear_output <index>` | `--clear-output <index>` | 清空cell输出 | ❌ |

#### 📦 批量操作
| Wrapper操作 | nb_runner等价命令 | 说明 |
|-------------|------------------|------|
| `batch_delete <range>` | `--batch-delete "<range>"` | 批量删除cell |
| `batch_clear_outputs <range>` | `--batch-clear-outputs "<range>"` | 批量清空输出 |
| `batch_convert <range> <type>` | `--batch-convert "<range>" <type>` | 批量转换cell类型 |

#### 💾 备份管理
| Wrapper操作 | nb_runner等价命令 | 说明 |
|-------------|------------------|------|
| `backup [description]` | `--backup "[description]"` | 创建备份 |
| `list_backups` | `--list-backups` | 列出所有备份 |
| `restore <backup_id>` | `--restore-backup <backup_id>` | 恢复指定备份 |
| `delete_backup <backup_id>` | `--delete-backup <backup_id>` | 删除指定备份 |
| `cleanup <keep_count>` | `--cleanup-backups <keep_count>` | 清理旧备份 |

#### 🖼️ 图片管理
| Wrapper操作 | nb_runner等价命令 | 说明 |
|-------------|------------------|------|
| `sync_images` | `--sync-images` | 同步图片状态 |
| `list_images` | `--list-images` | 查看图片详情 |
| `storage_info` | `--storage-info` | 存储统计信息 |

#### 🎭 预览模式管理
| Wrapper操作 | nb_runner等价命令 | 说明 |
|-------------|------------------|------|
| `enter_preview` | `--enter-preview` | 进入预览模式（自动创建备份） |
| `exit_preview [keep]` | `--exit-preview [keep]` | 退出预览模式，默认丢弃更改，可选保留 |
| `preview_status` | `--preview-status` | 查看当前预览模式状态 |

### 文件传递机制

**核心机制**：通过文件路径传递代码内容，避免命令行参数的引号冲突问题

**工作流程**：
1. **代码写入文件**：将要插入/编辑的代码写入独立文件
2. **传递文件路径**：wrapper调用时传递文件路径参数
3. **自动读取内容**：wrapper脚本从文件读取代码并传递给nb_runner
4. **完美格式保持**：保持代码的原始格式、缩进、引号类型

**典型使用示例**：
```bash
# 1. Agent先将代码写入文件
echo 'import pandas as pd
print("数据处理开始")' > cell_code.py

# 2. 通过wrapper插入cell
bash tools/notebook_runners/notebook_wrapper.sh insert_cell_file notebook.ipynb 0 code cell_code.py

# 3. 执行验证
bash tools/notebook_runners/notebook_wrapper.sh execute_cells notebook.ipynb "0"
```

### 🎭 预览模式详细说明

**设计理念**：提供完整的"临时工作空间"，支持任意操作后选择保留或丢弃所有更改。

**核心特性**：
- **自动备份**：进入预览模式时自动创建还原点
- **操作隔离**：预览模式下的所有操作都有 [PREVIEW] 标识
- **完整功能**：预览模式支持所有编辑、执行、批量操作
- **安全退出**：默认丢弃更改，需显式指定才保留

**预览模式工作流**：

```bash
# 1. 进入预览模式（自动创建备份）
bash tools/notebook_runners/notebook_wrapper.sh enter_preview notebook.ipynb
# 输出: ✅ 成功进入预览模式
#       备份ID: preview_start_20250829_143022
#       [PREVIEW] 标识将出现在所有后续操作中

# 2. 在预览模式下进行编辑操作
bash tools/notebook_runners/notebook_wrapper.sh insert_cell_file notebook.ipynb 0 code cell_code.py
# 输出: [PREVIEW] ✅ 在位置 [0] 插入 code Cell 完成

# 3. 执行代码验证功能
bash tools/notebook_runners/notebook_wrapper.sh execute_cells notebook.ipynb "0"
# 输出: [PREVIEW] 执行完成

# 4. 检查执行结果和状态（关键验证步骤）
bash tools/notebook_runners/notebook_wrapper.sh get_status notebook.ipynb
# 输出: [PREVIEW] 📊 执行状态：已执行1个cell，成功1个，失败0个

bash tools/notebook_runners/notebook_wrapper.sh get_errors notebook.ipynb
# 输出: [PREVIEW] ✅ 未发现错误cell

bash tools/notebook_runners/notebook_wrapper.sh get_cell notebook.ipynb 0
# 输出: [PREVIEW] 📋 Cell [0] 信息：
#       类型: code, 状态: 已执行, 输出: "环境初始化完成"

# 5. 根据检查结果决定保留或丢弃
# 5a. 结果满意，保留所有更改
bash tools/notebook_runners/notebook_wrapper.sh exit_preview notebook.ipynb keep
# 输出: ✅ 预览模式已退出，保留了 2 个操作的更改

# 5b. 结果不满意，丢弃所有更改（默认安全行为）
bash tools/notebook_runners/notebook_wrapper.sh exit_preview notebook.ipynb
# 输出: ✅ 预览模式已退出，丢弃了 2 个操作的更改
```

**预览模式的实际应用场景**：
- **安全实验**：测试复杂的数据处理逻辑，确认效果后再决定是否保留
- **代码调试**：在预览环境中调试 notebook，避免污染原始版本
- **分支开发**：类似 git 分支的概念，在隔离环境中开发新功能
- **Agent 系统**：为 AnalysisExecutionAgent 提供安全的试错环境

### 预览模式使用

**预览模式**：
- **完整工作空间**：支持所有操作类型（执行、编辑、批量、备份等）
- **状态持久化**：预览会话在进程重启后仍然有效
- **操作追踪**：记录预览期间的所有操作历史
- **安全恢复**：基于自动备份的可靠恢复机制

**标准工作流**：
```bash
# 预览模式工作流
bash tools/notebook_runners/notebook_wrapper.sh enter_preview notebook.ipynb
bash tools/notebook_runners/notebook_wrapper.sh insert_cell_file notebook.ipynb 0 code cell.py  # [PREVIEW] 完整功能
bash tools/notebook_runners/notebook_wrapper.sh exit_preview notebook.ipynb [keep]
```

**使用场景**：预览模式提供真正的工作空间隔离，适用于需要完整测试和验证的场景。

---

## 📋 Agent集成示例

### 典型Agent调用流程

```bash
# 基础工作流（非预览模式）
bash tools/notebook_runners/notebook_wrapper.sh create analysis.ipynb
bash tools/notebook_runners/notebook_wrapper.sh insert_cell_file analysis.ipynb 0 code env_init.py
bash tools/notebook_runners/notebook_wrapper.sh execute_cells analysis.ipynb "0"
bash tools/notebook_runners/notebook_wrapper.sh get_status analysis.ipynb

# 预览模式安全工作流（推荐用于复杂分析）
bash tools/notebook_runners/notebook_wrapper.sh create analysis.ipynb

# 进入预览模式进行安全开发
bash tools/notebook_runners/notebook_wrapper.sh enter_preview analysis.ipynb

# [PREVIEW] 模式下开发和测试
bash tools/notebook_runners/notebook_wrapper.sh insert_cell_file analysis.ipynb 0 code env_init.py
bash tools/notebook_runners/notebook_wrapper.sh insert_cell_file analysis.ipynb 1 code data_load.py
bash tools/notebook_runners/notebook_wrapper.sh execute_cells analysis.ipynb "0,1"
bash tools/notebook_runners/notebook_wrapper.sh get_status analysis.ipynb

# 验证结果满意后保留更改，或丢弃重新开始
bash tools/notebook_runners/notebook_wrapper.sh exit_preview analysis.ipynb keep  # 保留更改
# bash tools/notebook_runners/notebook_wrapper.sh exit_preview analysis.ipynb     # 丢弃更改
```

### Agent协作的优势
- ✅ **统一接口**：所有Agent使用相同的wrapper调用方式
- ✅ **文件管理**：通过文件路径传递，完美支持复杂代码
- ✅ **状态追踪**：每步操作后都能获取详细的执行状态反馈
- ✅ **错误处理**：wrapper提供统一的错误处理和重试机制
- ✅ **编码兼容**：自动处理Windows环境的编码问题
- ✅ **预览模式**：提供完整的工作空间隔离，支持安全的开发和测试
- ✅ **操作可逆**：预览模式支持完整的撤销机制，降低试错成本

---

## 🔧 技术架构

### 整体架构层次

```
Agent系统调用层
         ↓
notebook_wrapper.sh (统一接口层)
         ↓  
nb_runner.py (核心工具层)
         ↓
Jupyter内核执行层
```

### 调用模式对比

| 特性 | Wrapper调用 | 直接调用 |
|------|------------|----------|
| **适用场景** | Agent系统集成 | 开发调试 |
| **接口复杂度** | 简化统一 | 完整灵活 |
| **文件传递** | 支持文件路径 | Here Document |
| **编码处理** | 自动处理 | 手动处理 |
| **错误恢复** | 内置重试 | 手动处理 |
| **跨平台** | 自动适配 | 需要适配 |

---

## 🆘 基础故障排除

### Wrapper调用问题

```bash
# 1. 检查wrapper脚本是否存在
ls tools/notebook_runners/notebook_wrapper.sh

# 2. 手动测试wrapper调用
bash tools/notebook_runners/notebook_wrapper.sh get_status notebook.ipynb

# 3. 查看wrapper错误输出
bash -x tools/notebook_runners/notebook_wrapper.sh execute_cells notebook.ipynb "0" 2>&1
```

### 文件传递问题

```bash
# 1. 检查代码文件是否存在和可读
ls -la cells/cell_code.py
cat cells/cell_code.py  # 查看文件内容

# 2. 预览执行一下（第5个参数true启用预览模式，不实际修改文件）
bash tools/notebook_runners/notebook_wrapper.sh insert_cell_file notebook.ipynb 0 code cells/test.py true

# 3. 实际执行文件插入
bash tools/notebook_runners/notebook_wrapper.sh insert_cell_file notebook.ipynb 0 code cells/test.py
```

---

## 📖 详细文档

**完整功能文档**: [README_nb_runner.md](README_nb_runner.md)
- 详细的nb_runner.py参数说明
- Here Document标准格式
- 高级使用场景
- 技术架构深入解析
- 完整故障排除指南

**主要章节**:
- 核心功能分类 (执行、查询、编辑、批量操作、备份管理)
- 使用指南 (Here Document格式、预览模式)
- 常见使用场景 (开发调试、结构分析、安全编辑等)
- 技术架构 (模块化设计、执行机制、Cell状态管理)
- 故障排除 (详细的问题排查和调试技巧)

---

## 📝 更新日志

**v3.0.0 (2025-08-29)**
- 🎭 **预览模式重构**：将无实用价值的 dry_run 重构为完整的预览工作空间
- 🔄 **完整工作流支持**：预览模式支持任意操作（执行、编辑、批量操作等）
- 🔒 **安全退出机制**：默认丢弃更改，需显式指定才保留，确保安全性
- 📊 **状态持久化**：预览会话状态在进程重启后仍然有效
- 🔍 **操作追踪**：记录预览期间所有操作历史，支持完整审计
- ⚡ **自动备份恢复**：基于现有备份系统的可靠恢复机制
- 🏷️ **视觉标识**：预览模式下所有操作显示 [PREVIEW] 标识
- 🗑️ **移除旧功能**：删除过时的 --dry-run 参数和相关逻辑

**v2.0.1 (2025-08-29)**
- 🔧 补充缺失的批量操作映射表章节
- ✅ 修正预览模式参数格式说明，与wrapper脚本实际实现保持一致
- 📝 更新帮助信息，准确反映预览功能使用方式
- 🎯 完成文档与代码100%一致性验证
- 📋 新增专门的预览模式使用章节，统一术语和说明

**v2.0.0 (2025-08-29)**
- 📋 文档结构重新设计，主README专注wrapper接口
- 🔧 详细实现文档独立为README_nb_runner.md
- 🎯 突出Agent系统集成和文件传递机制
- ✅ 精简主文档，提高可读性和易用性

**v2.0.0 (2025-08-26)**
- 📋 文档完全重构，按功能分类组织  
- 🔍 完善查询分析功能说明
- 📦 新增完整批量操作说明
- 🎯 增加实用场景和工作流程
- ✅ 修正所有命令格式，确保与实际实现一致