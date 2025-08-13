# 项目目录结构

本项目采用任务隔离的存档策略，每个分析任务的所有产物都存放在独立的任务目录下。

## 目录结构说明

```
Claude-Code-Auto-Data-Analysis/
├── .claude/                    # Claude Code配置
│   └── settings.local.json    # 本地配置（不提交）
├── Agents/                     # Agent实现文件
│   ├── AnalysisExecutionAgent.md           # 分析执行Agent
│   ├── AnalysisIdeaPlanningAgent.md        # 分析思路规划Agent
│   ├── DataSourceFileAnalysisAgent.md      # 数据源文件分析Agent
│   ├── IdeaValidationAgent.md              # 思路验证Agent
│   └── ResultValidationAgent.md            # 结果验证Agent
├── .mcp.json                   # MCP服务器配置
├── CLAUDE.md                   # 项目配置文档
├── PROJECT_STRUCTURE.md        # 本文档
├── package.json                # Node.js依赖
├── requirements.txt            # Python依赖
├── project_config/             # 项目配置目录
│   └── project_context.json   # 运行时上下文（不提交）
├── logs/                       # 系统级日志（不提交内容）
├── archives/                   # 任务存档目录（不提交内容）
│   └── {task_name}/           # 每个任务的独立目录
│       ├── data_source/       # 数据源目录
│       │   ├── raw/           # 原始数据文件
│       │   └── descriptions/  # 数据源描述文件
│       │       └── intermediate_artifacts/  # 中间产物
│       ├── docs/              # 文档目录
│       │   ├── task_background.md          # 任务背景
│       │   ├── analysis_plans/             # 分析规划
│       │   │   └── validation/             # 验证相关文件
│       │   └── code_designs/               # 代码设计（已废弃）
│       └── logs/              # 任务级日志
└── tools/                     # 工具脚本
    ├── data_readers/          # 数据读取工具
    ├── notebook_runners/      # Notebook运行工具
    └── notebook_config/       # Notebook环境初始化
```

## 使用说明

1. **新建任务**：在 `archives/` 目录下创建以任务名命名的文件夹
2. **数据准备**：将原始数据放入 `archives/{task_name}/data_source/raw/`
3. **任务配置**：创建 `archives/{task_name}/docs/task_background.md`
4. **运行分析**：系统会自动在相应目录生成分析产物

## 注意事项

- `archives/` 目录下的内容不会提交到Git仓库
- `project_config/project_context.json` 包含运行时数据，不提交
- `.claude/settings.local.json` 包含本地配置，不提交
- Jupyter Notebook文件存放在 `D:\Program\jupyter\{project_name}\{task_name}\`