# 项目目录结构

本文档专门说明项目的文件组织结构和路径约定。详细功能说明请参考 [README.md](README.md) 和 [CLAUDE.md](CLAUDE.md)。

## 📂 完整目录结构

```
D:\Desktop\data\数据复盘\Claude Code Auto Analysis\  # 项目根目录
├── .claude/                                        # Claude Code配置目录
│   ├── agents/                                     # Sub-Agent实现文档（Task工具调用）
│   │   ├── NonstructuredSummaryAgent.md            # 非结构化数据摘要Agent
│   │   └── NotebookExecutorAgent.md                # Notebook执行专家Agent
│   └── settings.local.json                         # Claude Code本地设置（不提交）
├── Agents/                                         # 主Agent实现文档（主协调器扮演）
│   ├── DataSourceFileAnalysisAgent.md              # 数据源分析Agent
│   ├── AnalysisIdeaPlanningAgent.md                # 分析规划Agent
│   ├── IdeaValidationAgent.md                      # 思路验证Agent
│   ├── AnalysisExecutionAgent.md                   # 分析执行Agent
│   └── ResultValidationAgent.md                    # 结果验证Agent
├── config/                                         # 配置文件目录
│   ├── README.md                                   # 配置说明文档
│   ├── config.example.json                         # 配置模板
│   └── config.json                                 # 实际配置（不提交）
├── tools/                                          # 工具脚本目录
│   ├── data_readers/                               # 数据读取工具
│   │   ├── README.md                               # 工具说明
│   │   ├── file_classifier.py                     # 文件分类器
│   │   ├── read_structured_data.py               # 结构化数据读取
│   │   ├── document_parser.py                      # 文档解析器
│   │   ├── file_splitter.py                       # 文件分割器
│   │   ├── README_file_splitter.md                # 分割器说明
│   │   ├── frontmatter_tool.py                    # Frontmatter工具
│   │   └── README_frontmatter_tool.md             # Frontmatter工具说明
│   ├── notebook_runners/                           # Notebook运行器
│   │   ├── nb_runner.py                            # 主运行器脚本
│   │   ├── README.md                               # 运行器说明
│   │   ├── core/                                   # 核心功能模块
│   │   │   ├── __init__.py
│   │   │   ├── notebook_executor.py               # 执行引擎
│   │   │   ├── notebook_editor.py                 # 编辑器
│   │   │   ├── notebook_analyzer.py               # 分析器
│   │   │   └── image_manager.py                   # 图像管理
│   │   └── utils/                                  # 辅助工具
│   │       ├── __init__.py
│   │       ├── notebook_io.py                     # 文件IO
│   │       └── helpers.py                         # 辅助函数
│   ├── notebook_config/                         # Notebook环境配置
│   │   ├── notebook_env_config.md               # 环境配置模板
│   │   └── README.md                            # 配置说明
│   └── README.md                                   # 工具总说明
├── project_config/                                 # 项目配置
│   └── project_context.json                        # 全局上下文（运行时生成，不提交）
├── archives/                                       # 任务存档目录（不提交内容）
│   └── {current_task_name}/                       # 单个任务目录
│       ├── data_source/                            # 数据源目录
│       │   ├── raw/                                # 原始数据文件
│       │   └── descriptions/                       # 数据描述文件
│       │       └── intermediate_artifacts/         # 中间产物
│       │           ├── {filename}_intermediate.md  # 非结构化中间产物
│       │           ├── {filename}_1.md            # 分片文件（>20KB）
│       │           └── {filename}_images/          # 图片目录
│       ├── docs/                                   # 文档目录
│       │   ├── task_background.md                  # 任务背景文件
│       │   └── analysis_plans/                     # 分析规划目录
│       │       ├── {plan_slug}.json               # 规划文件
│       │       └── validation/                     # 验证目录
│       │           ├── report_{plan_slug}_{timestamp}.md        # 验证报告
│       │           ├── result_report_{plan_slug}_{timestamp}.md # 结果验证报告
│       │           └── feedback_{plan_slug}_{timestamp}.md      # 用户反馈
│       └── logs/                                   # 任务日志（按phase分目录）
├── tests/                                          # 测试文件目录
├── logs/                                           # 系统级日志目录（不提交内容）
├── .gitignore                                      # Git忽略规则
├── .mcp.json                                       # MCP服务器配置
├── CLAUDE.md                                       # Claude Code配置（执行手册）
├── PROJECT_STRUCTURE.md                            # 本文档（目录结构说明）
├── README.md                                       # 项目说明文档
└── requirements.txt                                # Python依赖
```

## 📋 路径约定

### Jupyter Notebook 存放路径
```
D:\Program\jupyter\{project_name}\{current_task_name}\*.ipynb
```

### 任务存档路径模式
```
archives/{current_task_name}/data_source/raw/          # 原始数据
archives/{current_task_name}/data_source/descriptions/ # 数据描述
archives/{current_task_name}/docs/analysis_plans/      # 分析规划
archives/{current_task_name}/logs/{phase}/             # 阶段日志
```

### 文件命名规范

#### 数据描述文件
- **结构化数据**：`{原文件名}.json`
- **非结构化数据摘要**：`{原文件名}_summary.md`
- **中间产物**：`{原文件名}_intermediate.md`
- **分片文件**：`{原文件名}_1.md`, `{原文件名}_2.md`...

#### 分析相关文件
- **规划文件**：`{plan_slug}.json`
- **验证报告**：`report_{plan_slug}_{timestamp}.md`
- **结果验证**：`result_report_{plan_slug}_{timestamp}.md`
- **用户反馈**：`feedback_{plan_slug}_{timestamp}.md`
- **Notebook文件**：`{plan_slug}.ipynb`

## 🔒 Git 管理规则

### 提交到仓库的文件
- 源代码和工具脚本
- Agent实现文档
- 配置模板文件
- 项目说明文档

### 不提交的文件/目录（.gitignore）
```gitignore
# 运行时数据
archives/
project_config/project_context.json
logs/

# 本地配置
config/config.json
.claude/settings.local.json

# 临时文件
*.tmp
*.log
.DS_Store
```

## 💡 目录用途快速参考

| 目录/文件 | 用途 | 提交到Git |
|-----------|------|----------|
| `.claude/agents/` | Sub-Agent实现文档 | ✓ |
| `Agents/` | 主Agent实现文档 | ✓ |
| `config/` | API配置文件 | 仅模板 |
| `tools/` | 工具脚本 | ✓ |
| `project_config/` | 运行时上下文 | ✗ |
| `archives/` | 任务存档数据 | ✗ |
| `tests/` | 测试文件 | ✓ |
| `logs/` | 系统日志 | ✗ |

---

*专注于目录结构 • 路径约定 • 文件组织*