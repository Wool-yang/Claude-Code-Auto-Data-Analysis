# Jupyter Notebook Runner

专为 AnalysisExecutionAgent 优化的 Notebook 执行工具，支持无状态执行、依赖检测和完整操作能力。

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
```

### 环境要求
- **Python 3.7+**
- **Python依赖**: `pip install nbformat nbconvert jupyter jupyter-client`
- **Claude Code权限**: `"Bash(python tools/notebook_runners/nb_runner.py:*)"`

---

## 📋 核心功能分类

### 🚀 执行操作 (Execution)

| 命令 | 功能 | 示例 |
|------|------|------|
| `--all` | 执行整个notebook | `--all --show-output` |
| `--cells "范围"` | 执行指定cells（支持批量） | `--cells "0,1,2" --show-output` |

**Cell标识符支持**：
- **数字索引**: `0, 1, 2, 3...` (从0开始)
- **Cell ID**: `1c29d688, 4896f9ab...` (Jupyter内部标识)
- **混合使用**: `"0,abc123,3-5"` (索引、ID、范围混用)

### 🔍 查询分析 (Query & Analysis)

| 命令 | 功能 | 示例 |
|------|------|------|
| `--get [标识符]` | 获取cell信息 | `--get 0` / `--get all` |
| `--status [选项]` | 查看状态信息 | 见下表 |
| `--search "模式"` | 搜索文本(支持正则) | `--search "pandas"` |

#### --status 子命令详解

| 子命令 | 功能 | 输出内容 |
|--------|------|----------|
| `exec` | 执行状态 | 已执行cell数、执行率、输出统计 |
| `structure` | 结构信息 | cell总数、类型分布、代码行数 |
| `deps` | 依赖关系 | 变量依赖链、cell间关系 |
| `errors` | 错误检查 | 错误cell位置、错误类型、行号 |
| `all` | 全部信息 | 以上所有信息 |
| (无参数) | 详细状态 | cell逐个状态、问题诊断 |

**查询示例**：
```bash
# 获取特定cell信息
python nb_runner.py notebook.ipynb --get 0
python nb_runner.py notebook.ipynb --get "1c29d688"

# 查看执行状态和结构
python nb_runner.py notebook.ipynb --status exec
python nb_runner.py notebook.ipynb --status structure

# 分析依赖关系
python nb_runner.py notebook.ipynb --status deps

# 查找错误cell
python nb_runner.py notebook.ipynb --status errors

# 搜索功能（自动识别正则表达式）
python nb_runner.py notebook.ipynb --search "import pandas"
python nb_runner.py notebook.ipynb --search "pd\\.\\w+" --case-sensitive
```

### ✏️ 编辑操作 (Edit)

| 分类 | 命令 | 功能 |
|------|------|------|
| **基础** | `--create` | 创建空白notebook |
| **内容编辑** | `--edit-cell 标识符` | 编辑cell内容（支持数字索引或Cell ID） |
| | `--insert-cell 位置 [类型]` | 插入新cell（位置必须是数字） |
| | `--delete-cell 标识符` | 删除cell（支持数字索引或Cell ID） |
| | `--clear-output 标识符` | 清空cell输出（支持数字索引或Cell ID） |
| **位置调整** | `--move-cell 源 目标` | 移动cell位置（支持数字索引或Cell ID） |
| | `--copy-cell 源 目标` | 复制cell（支持数字索引或Cell ID） |
| **类型转换** | `--convert-cell 标识符 类型` | 转换cell类型（支持数字索引或Cell ID） |

**支持的cell类型**: `code`, `markdown`, `raw`

### 📦 批量操作 (Batch Operations)

| 命令 | 功能 | 范围格式 |
|------|------|----------|
| `--batch-delete` | 批量删除cell | `"1,2,3"` / `"1-5"` / `"0,abc123,3-5"` |
| `--batch-clear-outputs` | 批量清空输出 | 同上 |
| `--batch-convert 范围 类型` | 批量转换类型 | 同上 |

**批量操作示例**：
```bash
# 批量删除（支持预览）
python nb_runner.py notebook.ipynb --batch-delete "10,11,12" --dry-run
python nb_runner.py notebook.ipynb --batch-delete "10,11,12"

# 批量转换为markdown
python nb_runner.py notebook.ipynb --batch-convert "1-5" markdown

# 使用Cell ID批量操作
python nb_runner.py notebook.ipynb --cells "1a2b3c4d,5e6f7a8b" --show-output

# 混合使用索引和Cell ID
python nb_runner.py notebook.ipynb --batch-clear-outputs "0,abc123,3-5"
```

### 💾 备份管理 (Backup)

| 命令 | 功能 | 示例 |
|------|------|------|
| `--backup [描述]` | 创建备份 | `--backup "重要修改前"` |
| `--list-backups` | 列出所有备份 | |
| `--restore-backup ID` | 恢复指定备份 | `--restore-backup 20250820_120109` |
| `--delete-backup ID` | 删除指定备份 | `--delete-backup 20250820_120109` |
| `--cleanup-backups [N]` | 清理旧备份 | `--cleanup-backups 10` |
| `--backup-info` | 显示备份信息 | |

**备份特性**：
- **自动ID**: 基于时间戳(`20250820_120109`)
- **版本管理**: 自动限制备份数量
- **安全恢复**: 恢复前自动备份当前状态

### 🖼️ 图片管理 (Image Management)

| 命令 | 功能 |
|------|------|
| `--sync-images` | 同步图片状态(故障恢复) |
| `--list-images` | 查看保存的图片详情 |
| `--storage-info` | 显示存储统计信息 |

---

## 📖 使用指南

### Here Document 标准格式 (系统标准)

**本系统使用 Here Document + EOF 格式作为插入/编辑多行代码的唯一标准方式**

#### 标准语法
```bash
cat <<'EOF' | python nb_runner.py notebook.ipynb --edit-cell 0 --code-stdin
代码内容...
EOF
```

#### 格式要点
1. **EOF必须单独一行**: 结束标记EOF必须独占一行，前后不能有任何字符
2. **大小写敏感**: 开始和结束标记必须完全一致
3. **完美引号支持**: 支持所有引号类型，无需转义

#### 实际使用示例
```bash
# 插入环境初始化代码
cat <<'EOF' | python nb_runner.py notebook.ipynb --insert-cell 0 code --code-stdin
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 配置中文显示
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

print('环境初始化完成')
EOF

# 编辑数据处理代码
cat <<'EOF' | python nb_runner.py notebook.ipynb --edit-cell 2 --code-stdin
# 数据加载和预处理
data = pd.read_csv('analysis_data.csv', encoding='utf-8')
print(f'数据形状: {data.shape}')

# 数据清洗
data_cleaned = data.dropna()
print(f'清洗后: {data_cleaned.shape}')
EOF

# 复杂代码示例（包含各种引号和符号）
cat <<'EOF' | python nb_runner.py notebook.ipynb --insert-cell 3 code --code-stdin
# 可视化代码
import plotly.express as px

# 配置参数
config = {
    'title': '销售趋势分析', 
    'font': 'Microsoft YaHei',
    'colors': ['#FF6B6B', '#4ECDC4', '#45B7D1']
}

fig = px.line(data, x='日期', y='销售额', title=config['title'])
fig.show()

print("图表生成完成!")
EOF
```

### 预览模式 (--dry-run)

编辑操作、批量操作和部分备份操作都支持预览模式，先查看操作效果再决定是否执行：

```bash
# 预览编辑操作
cat <<'EOF' | python nb_runner.py notebook.ipynb --edit-cell 2 --code-stdin --dry-run
新的代码内容
EOF

# 预览批量删除
python nb_runner.py notebook.ipynb --batch-delete "10,15,20" --dry-run
```

---

## 🎯 常见使用场景

### 场景1: Agent逐Cell验证流程

**工作流程**: 每次添加新Cell后验证执行，保持状态连续性

```bash
# 1. 创建新notebook
python tools/notebook_runners/nb_runner.py analysis.ipynb --create

# 2. 插入环境初始化Cell
cat <<'EOF' | python tools/notebook_runners/nb_runner.py analysis.ipynb --insert-cell 0 code --code-stdin
import pandas as pd
import numpy as np
print('环境初始化完成')
EOF

# 3. 执行首个Cell
python tools/notebook_runners/nb_runner.py analysis.ipynb --cells "0" --show-output

# 4. 继续添加数据加载Cell并扩展执行范围
# ... (添加新Cell)
python tools/notebook_runners/nb_runner.py analysis.ipynb --cells "0,1" --show-output

# 5. 逐步扩展执行范围(智能依赖排序)
python tools/notebook_runners/nb_runner.py analysis.ipynb --cells "0,1,2,3,4" --show-output

# 6. 查看当前执行状态
python tools/notebook_runners/nb_runner.py analysis.ipynb --status
```

### 场景2: 结构分析和调试

```bash
# 查看整体结构
python tools/notebook_runners/nb_runner.py analysis.ipynb --status structure

# 分析依赖关系（发现Cell间的变量依赖）
python tools/notebook_runners/nb_runner.py analysis.ipynb --status deps

# 查找错误Cell
python tools/notebook_runners/nb_runner.py analysis.ipynb --status errors

# 搜索特定内容
python tools/notebook_runners/nb_runner.py analysis.ipynb --search "import pandas"
python tools/notebook_runners/nb_runner.py analysis.ipynb --search "Error|Exception"
```

### 场景3: 安全编辑和备份

```bash
# 1. 创建备份
python tools/notebook_runners/nb_runner.py analysis.ipynb --backup "重要修改前备份"

# 2. 预览编辑操作
cat <<'EOF' | python tools/notebook_runners/nb_runner.py analysis.ipynb --edit-cell 2 --code-stdin --dry-run
import pandas as pd
data = pd.read_csv('new_data.csv')
print(f'数据加载: {data.shape}')
EOF

# 3. 确认无误后执行实际编辑
cat <<'EOF' | python tools/notebook_runners/nb_runner.py analysis.ipynb --edit-cell 2 --code-stdin
import pandas as pd  
data = pd.read_csv('new_data.csv')
print(f'数据加载: {data.shape}')
EOF

# 4. 如需要，可恢复备份
python tools/notebook_runners/nb_runner.py analysis.ipynb --restore-backup 20250820_120109
```

### 场景4: 批量处理和清理

```bash
# 批量删除无用Cell（预览）
python tools/notebook_runners/nb_runner.py analysis.ipynb --batch-delete "10,15,20" --dry-run

# 批量转换Cell类型
python tools/notebook_runners/nb_runner.py analysis.ipynb --batch-convert "1,3,5" markdown

# 批量清空输出
python tools/notebook_runners/nb_runner.py analysis.ipynb --batch-clear-outputs "1-10"

# 批量执行特定范围
python tools/notebook_runners/nb_runner.py analysis.ipynb --cells "2,3,4" --show-output
```

### 场景5: 依赖感知执行

```bash
# 1. 首次完整运行
python tools/notebook_runners/nb_runner.py analysis.ipynb --all --show-output

# 2. 修改Cell后，分析依赖关系
python tools/notebook_runners/nb_runner.py analysis.ipynb --status deps
# 输出示例:
# 🔗 依赖关系:
#    Cell [5] → [3]  
#    Cell [7] → [3]
# (发现Cell 5和7依赖Cell 3的变量)

# 3. 基于依赖分析，智能执行受影响的Cell
python tools/notebook_runners/nb_runner.py analysis.ipynb --cells "3,5,7" --show-output
```

---

## 🔧 技术架构

### 模块化设计
```
nb_runner.py (主入口，100%向后兼容)
├── core/                           # 核心功能模块
│   ├── notebook_executor.py       # 执行引擎
│   ├── notebook_editor.py         # 编辑功能
│   ├── notebook_analyzer.py       # 分析查询功能
│   └── image_manager.py           # 图片管理
├── utils/                          # 工具函数模块
│   ├── notebook_io.py             # 备份管理
│   └── helpers.py                 # 辅助函数
└── old_modules_backup/             # 旧模块备份目录
```

### Cell状态类型
- `✅ success`: 执行成功
- `❌ failed`: 执行失败  
- `❓ pending`: 待执行
- `⚠️ dirty`: 内容变化需要重跑

### 执行策略
- **智能执行模式** (`--cells`): 按依赖关系排序，自动处理变量依赖
- **原样执行模式** (`--all`): 按原始顺序，保持Notebook设计逻辑
- **无状态执行**: 每次启动新kernel，确保环境一致性

---

## 🆘 故障排除

### 常见问题

**执行问题排查**:
```bash
# 查看详细执行状态
python nb_runner.py notebook.ipynb --status

# 查找错误Cell
python nb_runner.py notebook.ipynb --status errors

# 重新完整执行
python nb_runner.py notebook.ipynb --all --show-output
```

**编辑操作失败**:
```bash
# 使用预览模式检查
python nb_runner.py notebook.ipynb --edit-cell 2 "内容" --dry-run

# 检查Here Document格式
# ✅ 正确: EOF单独一行
# ❌ 错误: EOF后有空格或其他字符
```

**Here Document格式错误**:
```bash
# ❌ 常见错误
EOF)     # 错误：EOF后有括号
EOF      # 错误：EOF前有空格
 
# ✅ 正确格式  
EOF      # 正确：EOF单独一行，无任何额外字符
```

### 调试技巧
- 使用 `--status` 监控执行状态和依赖关系
- 编辑前用 `--dry-run` 预览操作
- 重要修改前用 `--backup` 创建备份
- 使用 `--search` 快速定位代码位置

---

## 📝 更新日志

**v2.0.0 (2025-08-26)**
- 📋 文档完全重构，按功能分类组织  
- 🔍 完善查询分析功能说明(--status子命令详解)
- 📦 新增完整批量操作说明
- 🎯 增加实用场景和工作流程
- ✅ 修正所有命令格式，确保与实际实现一致
- 🚀 优化帮助文本结构，突出核心功能

**v2.0.0 (2025-08-20)**
- 模块化重构，完整Notebook操作平台
- 新增结构分析、内容搜索、编辑操作
- 新增批量操作、备份管理、预览模式
- 优化Agent体验：移除调试警告，增强AST解析
- 100%向后兼容

**v1.x.x**
- 基础执行、依赖检测功能
- 双模式执行策略