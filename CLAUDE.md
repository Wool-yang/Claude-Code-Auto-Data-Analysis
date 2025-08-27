# Claude Code 配置

## 项目概述

### 项目目标

构建一个通用数据分析Multi-Agent系统，能够适应各种场合的数据分析任务，通过多个专门Agent的协作，实现从数据源分析到结果验证的完整流程自动化。

### 项目架构

本项目采用Multi-Agent架构，包含以下核心Agent（注意：本项目采用"按 task 隔离"的存档策略，所有产物写入 archives/{current_task_name}/ 目录，详见"任务存档与每任务数据源"）：

#### Agent 文件位置与使用方式
所有Agent的详细实现文档位于 `Agents/` 目录下：
- `Agents/DataSourceFileAnalysisAgent.md` - 数据源文件分析Agent
- `Agents/AnalysisIdeaPlanningAgent.md` - 分析思路规划Agent  
- `Agents/IdeaValidationAgent.md` - 思路验证Agent
- `Agents/AnalysisExecutionAgent.md` - 分析执行Agent
- `Agents/ResultValidationAgent.md` - 结果验证Agent

子Agent位于 `.claude/agents/` 目录下：
- `.claude/agents/NonstructuredSummaryAgent.md` - 非结构化数据处理与摘要生成Agent
- `.claude/agents/NotebookExecutorAgent.md` - Notebook执行专家，处理所有nb_runner.py相关操作

**重要说明**：
- **执行方式**：主流程协调器（当前Claude助手）直接读取Agent文档并按照其定义执行相应功能
- **角色扮演**：执行时，主协调器将扮演对应Agent的角色，遵循其文档中定义的规范和流程

#### 主流程协调器
主流程协调器是整个Multi-Agent系统的核心组件，负责项目的总体调度、状态维护与用户门控，确保各子Agent按阶段有序交付可复用产物。**在Claude Code环境中，主流程协调器由用户直接调用的Claude助手担任**。

1. 项目初始化
* 主协调器必须在每次运行时通过对话获取 current_task_name（由用户输入），随后由用户指定 project_name；若 project_id 为空则生成 UUID。主协调器将写入 project_context.current_task_name，并以此在 archives/{current_task_name}/ 下创建运行目录。
* 初始化或更新 `project_config/project_context.json`（project_id、project_name、notebook_dir、status、current_phase 等），并以原子方式写入。
* 在 Jupyter 根目录（`D:\Program\jupyter`）下创建基于 project_name 的工程目录（若不存在）。

2. 流程控制与任务分发
* 按照定义的串行阶段顺序启动并协调子Agent；在阶段内部允许并行任务以提高效率。
* **集中收集Agent统计报告**：接收各Agent的任务完成报告，汇总统计信息后统一更新 `project_context.json` 的 `current_phase`、`status` 与计数字段。
* 按需将阶段产物（数据源描述、分析规划、Notebook 等）传递给下游Agent。
* 提供清晰的阶段边界、超时与重试策略以保证可观测性与可恢复性。

3. 上下文与元数据维护
* **独占式上下文文件管理**：仅主协调器可写入 `project_context.json`，确保写入为原子操作以避免Agent间竞态条件。
* 实时更新上下文文件（last_updated 使用 ISO8601），基于Agent报告的统计数据维护计数字段。
* 维护数据源与规划计数（data_sources.count/processed、analysis_plans.count/completed）和 notebook_dir 路径信息。

4. 用户交互与审批门控
* **验证阶段交互**：接收IdeaValidationAgent生成的验证报告，向用户呈现摘要和完整内容，收集审批决定
* **结果验证交互**：接收ResultValidationAgent的结果验证报告，根据用户指令决定是否需要重新执行
* **反馈传递**：将用户的具体修改意见传递给IdeaValidationAgent，由其生成反馈文件
* **决策传递**：将用户的审批决定反馈给相关Agent，触发后续流程或迭代修正

5. Agent调度与状态管理
* 按照定义的串行阶段顺序启动并协调子Agent；在阶段内部允许并行任务以提高效率。
* 监控并记录 `project_context.json` 的 `current_phase`、`status` 与计数字段，按需将阶段产物传递给下游Agent。
* 提供清晰的阶段边界、超时与重试策略以保证可观测性与可恢复性。

6. 错误处理与重试策略
* 监控子Agent执行状态；对单个任务失败进行有限次重试（默认 2 次），超出则记录失败并通知用户或进入回退流程。
* 支持按需回退到受影响的阶段或重跑指定的规划/Notebook，避免全量重跑。

我的工作流程将遵循以下阶段：

1. Phase 1 — 启动与数据分析
* Input：archives/{current_task_name}/data_source/raw/（主协调器应准备并放置本次运行原始数据）
* Output：生成 archives/{current_task_name}/data_source/descriptions/目录下的数据分析结果文件：
  - 结构化数据：*.json 格式 数据源描述文件
  - 非结构化数据：*_summary.md 格式 摘要文件（最终产物，20KB以内）
* Context update：current_phase=data_analysis，更新 data_sources 计数

2. Phase 2 — 规划与验证
* Action：启动 AnalysisIdeaPlanningAgent
* Input：结构化数据源描述、非结构化数据源摘要文件 与 archives/{current_task_name}/docs/task_background.md
* Output：生成 archives/{current_task_name}/docs/analysis_plans/*.json
* 随后启动 IdeaValidationAgent 验证并产出验证报告；用户批准则进入下一阶段，否则记录反馈并迭代

3. Phase 3 — 分析执行
* Action：启动 AnalysisExecutionAgent，通过NotebookExecutorAgent基于规划文件在 D:\\Program\\jupyter\\{project_name}\\{current_task_name} 中逐步生成并执行 Notebook（主协调器须设置 project_context.current_task_name），所有 Notebook 与执行日志按 task 隔离存放。

4. Phase 4 — 结果验证
* Action：启动 ResultValidationAgent，对已完成的 Notebook 进行验证并生成报告
* 若验证失败，根据报告建议回退并重跑受影响部分

5. Phase 5 — 项目完成
* Action：向用户汇报完成状态并提供最终产物路径
* Context update：status=completed

#### 主流程协调器补充规范

##### 状态机与流转
**Phase 1 (data_analysis)**：
- 进入前：设置 status=running, current_phase=data_analysis
- 完成条件：archives/{current_task_name}/data_source/descriptions/ 目录下成功生成所有 raw 文件对应的描述文件：
  - 结构化数据文件 → .json 格式描述文件
  - 非结构化数据文件 → *_summary.md 格式摘要文件
- 完成后：保持 status=running, current_phase=planning
- 失败处理：单个文件失败重试至多2次；超过50%文件失败则 status=failed 并停止

**Phase 2 (planning→validation)**：
- 规划阶段：current_phase=planning，完成条件为生成至少1个规划文件
- 验证阶段：current_phase=validation，为每个规划生成验证报告后等待用户审批
- 用户批准：更新 analysis_plans.completed 计数，设置 current_phase=execution
- 用户不批准：记录反馈到 feedback_{plan_slug}_{timestamp}.md，回到 planning 阶段

**Phase 3 (execution)**：
- 进入条件：current_phase=execution，用户批准通过验证的规划（analysis_plans.completed > 0）
- 执行阶段：AnalysisExecutionAgent 通过NotebookExecutorAgent基于规划文件生成并执行 Notebook
- 完成条件：所有 Notebook 成功执行，无严重错误

**Phase 4 (result_validation)**：
- 进入条件：current_phase=result_validation，所有Notebook成功执行完成
- 启动：ResultValidationAgent 并行验证所有Notebook
- 验证过程：为每个plan生成独立的结果验证报告，并更新统计信息：
  - result_validation.validation_reports_count: 累积生成的报告数量
  - result_validation.validated_notebooks_count: 累积已验证的notebook数量
  - result_validation.overall_quality_score: 根据所有验证结果计算的总体质量评分(0-100分)
  - result_validation.total_issues_count: 发现的问题总数
  - result_validation.agent_recommendations: ResultValidationAgent的建议数组
- 通过条件：所有Notebook验证报告显示结果合规，overall_quality_score达到预设阈值
- 通过后进入 Phase 5；不通过按报告建议回退到 execution 或更早阶段

**Phase 5 (completed)**：
- 设置 status=completed，current_phase=completed
- 输出最终产物路径清单

##### 上下文写入规范
- 时间：last_updated 使用 ISO8601（UTC 或含时区）
- 原子写：写入 project_context.json 时先写临时文件再替换，避免部分写入
- 幂等与续跑：同一阶段可安全重复执行；支持 --resume 从 current_phase 继续
- 计数规则：
  - data_sources.count 为 raw 文件总数，processed 为成功生成描述文件数
  - analysis_plans.count 为规划文件总数，completed 为用户批准数量
  - result_validation.validation_reports_count 为生成的验证报告数量，validated_notebooks_count 为已验证的notebook数量
- 路径：notebook_dir= "D:\\Program\\jupyter\\{project_name}"，Notebook 将按 task 存放于子目录 `{notebook_dir}/{current_task_name}`；若项目目录不存在则创建。

##### 用户审批门控
**验证报告生成**：
- 位置：archives/{current_task_name}/docs/analysis_plans/validation/report_{plan_slug}_{timestamp}.md（按 plan 隔离）
- 内容：每个 plan 的详细验证结果和建议

**用户交互机制**：
- 主协调器将所有验证报告摘要呈现给用户
- 用户可以：
  1. 批准全部规划 → 进入下一阶段
  2. 批准部分规划 → 仅通过的规划进入下一阶段，其余重新规划
  3. 不批准 → 记录具体修改意见并重新规划

**反馈处理**：
- 修改意见保存：archives/{current_task_name}/docs/analysis_plans/validation/feedback_{plan_slug}_{timestamp}.md
- 反馈内容：包含用户的具体修改要求和不满意的方面
- 历史追溯：重新规划时必须参考所有历史反馈，避免重复错误

**状态更新**：
- 批准后：更新 analysis_plans.completed 计数，设置 current_phase=execution
- 不批准：保持 current_phase=validation，触发 AnalysisIdeaPlanningAgent 重新规划

##### 运行与安全保障
- 并发与超时：阶段内 Agent 可并行；为长任务设定合理超时与重试
- 回退策略：执行或验证失败时仅重跑受影响的规划/Notebook，避免全量重跑
- 日志：按阶段写入 archives/{current_task_name}/logs/{phase}/YYYYMMDD_HHMMSS.log，记录进度、告警与错误摘要（项目根 logs/ 仅保留运行/系统级别日志，不用于 Agent 产物）。
- 安全：日志中脱敏，不写入敏感原文；不记录大体量样本，仅最小必要信息
- Windows 兼容：统一使用双反斜杠或转义路径，避免编码问题

##### 项目初始化细化
- 从 archives/{current_task_name}/docs/task_background.md 读取 project_name
- 若 project_context.json 不存在或 project_id 为空，则生成新的 UUID 作为 project_id
- 初始化/更新 project_context.json 字段并写入 last_updated
- 确保 notebook_dir = "D:\\Program\\jupyter\\{project_name}" 目录存在，不存在则创建
- 在 notebook_dir 下创建 {current_task_name} 子目录用于存放本次任务的 Notebook

##### 任务存档与每任务数据源
- 每次运行必须提供 current_task_name，所有 Agent 生成的产物写入 archives/{current_task_name}/ 下的对应子目录（见下文路径约定）。
- 每个 task 必须有独立的原始数据目录：archives/{current_task_name}/data_source/raw/，主协调器或运行入口应负责在任务开始前准备该目录并放置本次运行所需的原始数据文件。
- 路径示例：archives/{current_task_name}/data_source/descriptions/，archives/{current_task_name}/docs/analysis_plans/，archives/{current_task_name}/logs/{phase}/。
- Notebook 存放路径示例：D:\\Program\\jupyter\\{project_name}\\{current_task_name}\\*.ipynb。
- 读取规则：所有 Agent 首选当前 task 的 archives/{current_task_name} 下相应目录；若 task 目录缺失明确提示并退出（避免混用不同任务的数据）。
- 任务复制：用户可复制 archives/{old_task} 为 archives/{new_task} 作为基线后再运行；系统写入仅限新 task 目录，旧任务数据保持不变。
- 命名规范：current_task_name 建议仅包含字母数字、- 和 _，长度不超过 64 字符；非法字符将被替换为下划线。

任务背景文件（archives/{current_task_name}/docs/task_background.md）:
- 位置：archives/{current_task_name}/docs/task_background.md
- 目的：保存本次 task 的背景信息与元数据，包含但不限于：current_task_name、project_name、分析目标、关键指标、数据描述与变量说明
- 读取约定：主协调器与所有 Agent 首选从该文件读取 current_task_name 与 project_name；若缺失，主协调器应通过对话向用户确认必要字段

##### 与子Agent的契约
- **阶段边界严格串行**：产物路径与计数更新由主协调器负责聚合
- **上下文文件集中维护**：只有主协调器可以写入 `project_context.json`，Agent只能读取上下文信息
- **统计信息收集模式**：Agent完成任务后向主协调器报告统计数据，主协调器汇总后统一更新上下文文件
- **Agent与主协调器通信格式**：Agent返回标准化的任务完成报告（包含：成功状态、处理文件数、生成文件数、错误信息等）

#### DataSourceFileAnalysisAgent（数据源文件分析Agent）
读取数据源，构建标准化的数据源描述文件，为后续分析提供精准的数据结构信息
- **结构化数据**：处理csv、xlsx、xls等表格文件，生成JSON格式描述文件，包含表头、数据类型、采样值等结构信息
- **非结构化数据**：调用NonstructuredSummaryAgent子代理处理，生成摘要文件（*_summary.md）作为最终产物，控制在20KB以内，便于后续Agent快速理解内容

#### NonstructuredSummaryAgent（非结构化数据处理与摘要生成Agent）
专门处理非结构化数据文件，由DataSourceFileAnalysisAgent调用
- 负责所有非结构化文件的描述文件生成工作
- 检查中间产物大小，必要时进行文件分割
- 为每个文件生成摘要，便于后续Agent快速理解内容
- 上下文隔离设计，避免主Agent读取大文件

#### AnalysisIdeaPlanningAgent（分析思路规划Agent）
根据数据源描述文件以及任务背景文件，细化出分析规划文件
- 分析规划文件为基于背景文件中的多个分析目标、分析关键指标、分析目标结论，以及数据源中数据的数量、种类综合得出的一系列文件
- 此类文件不需要涉及到分析代码的构建思路，而是更多着眼于通过何种数据分析思想可以得出预期的分析成果，着重于分析思路的构建
- 每个文件会对应创建一个 ipynb 文件，代表了一段连贯完整的分析(对应了某个或者某些分析目标、指标、结论），同时也会基于每个分析的上下文范围来规定使用到的数据源文件有哪些

#### IdeaValidationAgent（思路验证Agent）
此 Agent 负责结合任务背景和数据源描述，对 `AnalysisIdeaPlanningAgent` 生成的规划文件进行评估验证。其产出为一份详细的验证报告文件，以及一份对该报告的概括总结。

我（主流程协调器）会将报告原文和概括一并呈现给你。
-   **若你批准**：流程将进入下一阶段。
-   **若你不批准**：我会向你征求具体的修改意见，然后将这些意见传递给 `AnalysisIdeaPlanningAgent`，由其对规划进行修改，并重新开始此验证流程，直到规划获得你的批准。


#### AnalysisExecutionAgent（分析执行Agent）
直接基于分析规划文件，开始进行 ipynb 文件的编写和执行
- 此 Agent 的工作流程为，每次生成单个 Cell 的代码后立马执行，验证当前步骤状态正常后，再次生成新的 Cell 进行运行验证，循环往复，直至单个分析 ipynb 流程运行结束，结果无异常

#### ResultValidationAgent（结果验证Agent）
此 Agent 负责读取所有 `AnalysisExecutionAgent` 的运行结果，进行数据验证。其产出为一份包含异常点分析的验证报告文件，以及一份对报告的概括总结。我（主流程协调器）会根据这份报告和你的指令，来决定是否需要重新执行部分或全部的分析流程。

## 项目配置

### 项目目录

- **项目根目录**: `D:\Desktop\data\数据复盘\Claude Code Auto Analysis`
  - 存放项目配置、数据源、分析规划及辅助脚本。
  - Agent分析产出的`.ipynb`文件将创建于Jupyter Notebook根目录下，此目录主要用于存放项目管理和源代码文件。

- **Jupyter Notebook根目录**: `D:\Program\jupyter`
  - 此目录下有多个项目文件夹
  - 根据 task_background.md 中或者是用户提供的 project_name，在此目录下创建同名工程目录
  - 只在当前项目对应的文件夹中进行创建和编辑 ipynb 文件

### 运行环境配置

#### 依赖管理

**Python 依赖**:
- **配置文件**: `requirements.txt`
- **核心数据处理依赖**: 
  - pyyaml>=6.0（YAML frontmatter 处理）
  - google-genai>=0.1.0（图片分析和描述生成）
  - chardet>=5.0.0（文件编码检测）
  - charset-normalizer>=3.0.0（编码规范化）
  - ftfy>=6.0.0（文本修复）
  - pandas>=1.5.0（数据处理）
  - pymupdf>=1.26.0（PDF文档处理）
  - openpyxl>=3.0.0（Excel .xlsx文件读取）
  - xlrd>=2.0.0（Excel .xls文件读取）
- **Jupyter Notebook 依赖**:
  - nbformat>=5.0.0（notebook 格式处理）
  - jupyter-client>=7.0.0（kernel 管理）
- **安装方式**: `pip install -r requirements.txt`

**MCP 服务器配置**:
- **配置文件**: `.mcp.json`

#### Conda 环境设置

- **环境名称**: base
- **说明**: 该项目运行环境为 conda 的 base 环境

#### 编码设置

- **编码格式**: UTF-8
- **说明**: 该项目生成代码或者是文本内容时，编码统一为 UTF-8

### 项目目录结构

```
D:\Desktop\data\数据复盘\Claude Code Auto Analysis\  # 项目根目录
├── .claude/                                        # Claude Code特定目录
│   ├── agents/                                     # 真正的Sub-Agent目录（通过Task工具调用）
│   │   ├── NonstructuredSummaryAgent.md            # 非结构化数据处理与摘要生成Agent
│   │   └── NotebookExecutorAgent.md                # Notebook执行专家Agent
│   └── settings.local.json                         # Claude Code本地配置
├── Agents/                                         # 主流程协调器扮演的Agent角色文档
│   ├── AnalysisExecutionAgent.md                   # 分析执行Agent
│   ├── AnalysisIdeaPlanningAgent.md                # 分析思路规划Agent
│   ├── DataSourceFileAnalysisAgent.md              # 数据源文件分析Agent
│   ├── IdeaValidationAgent.md                      # 思路验证Agent
│   └── ResultValidationAgent.md                    # 结果验证Agent
├── .mcp.json                                       # MCP服务器配置文件
├── CLAUDE.md                                       # 本项目配置文件
├── PROJECT_STRUCTURE.md                            # 项目结构说明文档
├── README.md                                       # 项目说明文档
├── requirements.txt                                # Python依赖配置
├── config/                                         # 配置文件目录
│   ├── README.md                                   # 配置说明文档
│   ├── config.example.json                         # 配置模板文件
│   └── config.json                                 # 实际配置文件
├── tests/                                          # 测试文件目录
├── project_config/                                 # 项目配置目录
│   └── project_context.json                        # 项目全局上下文文件
├── archives/                                       # 任务存档目录（每个 task 单独子目录）
│   └── {current_task_name}/                       # 当前任务目录
│       ├── data_source/                            # 数据目录
│       │   ├── raw/                                # 原始数据文件（由主协调器在任务启动前准备）
│       │   └── descriptions/                       # 数据源描述 JSON（DataSourceFileAnalysisAgent 输出）
│       │       └── intermediate_artifacts/         # 中间产物目录
│       │           └── {filename}_images/          # 图片提取目录（如果有）
│       ├── docs/
│       │   ├── task_background.md                  # 任务背景与元数据（含 current_task_name, project_name, 分析目标等）
│       │   ├── analysis_plans/                     # AnalysisIdeaPlanningAgent 输出（按 task 隔离）
│       │   │   └── validation/                     # 验证相关文件
│       │   │       ├── report_{plan_slug}_{timestamp}.md       # IdeaValidationAgent按plan隔离的验证报告
│       │   │       ├── result_report_{plan_slug}_{timestamp}.md # ResultValidationAgent按plan隔离的结果验证报告
│       │   │       └── feedback_{plan_slug}_{timestamp}.md     # 用户反馈文件
│       └── logs/                                   # 任务级日志，按 phase 子目录存放
├── tools/                                          # 工具脚本目录
│   ├── data_readers/                               # 数据读取工具
│   │   ├── README.md                               # 数据读取工具说明
│   │   ├── file_classifier.py                     # 文件分类脚本
│   │   ├── read_structured_data.py               # 结构化数据读取脚本
│   │   ├── document_parser.py                      # 文档解析脚本
│   │   ├── file_splitter.py                       # 文件分割工具
│   │   ├── README_file_splitter.md                # 文件分割工具说明
│   │   ├── frontmatter_tool.py                    # Frontmatter处理工具
│   │   └── README_frontmatter_tool.md             # Frontmatter工具说明
│   ├── notebook_runners/                           # Notebook运行器相关工具
│   │   ├── nb_runner.py                            # Notebook运行器脚本
│   │   ├── README.md                               # 运行器使用说明
│   │   ├── core/                                   # 核心功能模块
│   │   │   ├── __init__.py                         # 模块初始化文件
│   │   │   ├── image_manager.py                    # 图像管理模块
│   │   │   ├── notebook_analyzer.py               # Notebook分析模块
│   │   │   ├── notebook_editor.py                 # Notebook编辑模块
│   │   │   └── notebook_executor.py               # Notebook执行模块
│   │   └── utils/                                  # 辅助工具模块
│   │       ├── __init__.py                         # 模块初始化文件
│   │       ├── helpers.py                          # 辅助函数模块
│   │       └── notebook_io.py                      # Notebook输入输出模块
│   ├── notebook_config/                         # Notebook环境初始化工具
│   │   ├── notebook_env_config.md               # Notebook环境配置代码模板
│   │   └── README.md                            # 环境配置使用说明
│   └── README.md                                   # 工具脚本说明文档
└── logs/                                           # 系统或运行级日志目录（Agent 产物请写入 archives/{current_task_name}/logs/）
```

### 工具脚本说明文档规则

1. **文档位置**：每个工具脚本目录下都应包含一个 `README.md` 文件，用于说明该目录下工具的使用方法和功能。
2. **文档内容**：
   - 工具的主要功能
   - 使用方法和参数说明
   - 依赖项说明
   - 示例用法
3. **文档维护**：当工具脚本更新时，相应的说明文档也应及时更新。

### Agent 工具使用强制要求

**重要：所有 Agent 必须严格使用项目提供的工具脚本，禁止手动实现相同功能！**

#### DataSourceFileAnalysisAgent 必须使用的工具
- `tools/data_readers/file_classifier.py` - 文件类型分类
- `tools/data_readers/read_structured_data.py` - 结构化数据处理  
- `tools/data_readers/document_parser.py` - 非结构化数据处理
- 调用NonstructuredSummaryAgent处理非结构化文件

#### NonstructuredSummaryAgent 必须使用的工具
- `tools/data_readers/file_splitter.py` - 大文件分割
- `tools/data_readers/frontmatter_tool.py` - Frontmatter处理
- 文件系统命令（ls、cp等）用于文件操作

#### NotebookExecutorAgent 必须使用的工具
- `tools/notebook_runners/nb_runner.py` - 用于执行和管理Notebook文件

#### 禁止的手动实现行为
- ❌ 通过文件扩展名手动判断文件类型
- ❌ 使用 pandas.read_csv() 等直接读取而不调用 read_structured_data.py
- ❌ 手动解析 Word/Excel 文档而不使用 document_parser.py
- ❌ 手动分割大文件或处理 frontmatter
- ❌ 在DataSourceFileAnalysisAgent中直接读取非结构化中间产物文件
- ❌ 使用 nbconvert 等工具执行 Notebook 而不使用 nb_runner.py

#### 标准调用格式
详细的调用方法和参数请参考 `tools/README.md` 和各子目录的说明文档。

## Agent间通信Schema设计

为了确保Agent之间的顺畅协作，定义一套柔性的通信Schema。

### 1. 项目上下文文件 (`project_config/project_context.json`)

由主流程协调器维护，用于记录项目全局状态和进度，所有Agent均可读取此文件以获取上下文。

```json
{
  "project_id": "uuid",
  "project_name": "string",
  "notebook_dir": "string",
  "status": "enum[pending, running, completed, failed]",
  "current_phase": "enum[data_analysis, planning, validation, execution, result_validation]",
  "current_task_name": "string|null",
  "tasks": {
    "{current_task_name}": {
      "notebook_dir": "string",
      "data_sources": {"count": "integer", "processed": "integer"},
      "analysis_plans": {"count": "integer", "completed": "integer"},
      "execution": {"notebook_count": "integer", "completed_count": "integer", "failures": "integer"},
      "result_validation": {
        "validation_reports_count": "integer",
        "validated_notebooks_count": "integer",
        "overall_quality_score": "number",
        "total_issues_count": "integer",
        "agent_recommendations": "array[string]"
      }
    }
  },
  "last_updated": "datetime"
}
```

**字段说明**:
- `project_id`: 项目的唯一标识符。
- `project_name`: 项目名称（用于在 Jupyter 根目录创建工程目录）。
- `notebook_dir`: Jupyter Notebook 工程目录完整路径。
- `status`: 项目的整体状态（enum）。
- `current_phase`: 项目当前所处的阶段（enum）。
- `current_task_name`: 当前运行的 current_task_name（string|null），由主协调器在任务启动时设置。
- `tasks`: 按 current_task_name 索引的对象，保存该 task 的统计与路径信息。建议每个 task 包含：
  - `notebook_dir`: Notebook 存放目录。
  - `data_sources`: {`count`, `processed`}。
  - `analysis_plans`: {`count`, `completed`}。
  - `execution`: {`notebook_count`, `completed_count`, `failures`}。
  - `result_validation`: 结果验证统计信息。
    - `validation_reports_count`: 生成的验证报告数量。
    - `validated_notebooks_count`: 已被验证的notebook数量。
    - `overall_quality_score`: 总体分析质量评分（0-100分）。
    - `total_issues_count`: 发现的问题总数。
    - `agent_recommendations`: 验证Agent的建议数组。
- `last_updated`: 上下文文件的最后更新时间（ISO8601）。

Agent 读写约定：

- **上下文文件读取**：Agent 只能**读取** `project_config/project_context.json` 获取 `current_task_name`、项目状态等信息；若缺失或对应的 `archives/{current_task_name}` 目录不存在，应报错并退出以避免混用数据。

- **产物读写**：Agent 在 `archives/{current_task_name}/` 下读写产物（data_source 描述、analysis_plans、logs 等）。

- **统计信息报告**：Agent 完成任务后，应向主协调器**报告统计信息**（如处理文件数量、生成文件数量、错误计数等），由主协调器负责更新 `project_context.json`。

- **上下文文件维护**：**仅主协调器**负责 `project_context.json` 的写入和更新，确保原子操作（先写临时文件再重命名替换）和时间字段使用 ISO8601，避免Agent间竞态条件。

- **日志与隐私**：日志输出必须脱敏，不得写入敏感原文；产物中应尽量避免包含原始敏感数据。

- **兼容与迁移**：主协调器在首次写入时负责创建并初始化 `tasks` 和 `current_task_name` 等字段。


### 2. 分析规划文件 (`archives/{current_task_name}/docs/analysis_plans/*.json`)（每个 task 使用独立目录）

由`AnalysisIdeaPlanningAgent`生成，每一个文件都详细描述一个具体的分析任务，是后续分析执行的蓝图。分析规划文件基于任务背景文件中的分析目标、关键指标和预期结论，结合数据源的实际情况进行设计。

#### 文件命名与标识符规范

- **文件名格式**: `{plan_slug}.json`
- **plan_slug生成规则**: 基于`title`字段，转换为小写，空格和特殊字符替换为下划线，限制长度32字符以内
- **示例**: title="销售趋势分析" → plan_slug="销售_趋势_分析" → 文件名="销售_趋势_分析.json"

```json
{
  "plan_id": "uuid",
  "plan_slug": "string",
  "title": "string",
  "description": "string",
  
  "execution_steps": [
    {
      "step_id": "integer",
      "name": "string",
      "operations": [
        {
          "action": "string",
          "sources": ["string"],
          "fields": ["string"],
          "field_usage": "string",
          "output": "string"
        }
      ],
      "expected_output": "string"
    }
  ],
  
  "targets": {
    "objectives": ["string"],
    "kpis": ["string"],
    "outcomes": ["string"]
  },
  
  "data_sources": {
    "source_id": {
      "file": "string",
      "type": "enum[structured, unstructured]",
      "purpose": "string",
      "fields": {
        "core": ["string"],
        "support": ["string"]
      },
      "content_areas": ["string"]
    }
  },
  
  "field_stats": {
    "total_fields": "integer",
    "used_fields": "integer",
    "utilization_rate": "string"
  },
  
  "methodology": "string",
  
  "deliverables": {
    "notebook": "string",
    "outputs": ["string"]
  },
  
  "field_details": {
    "field_name": {
      "role": "string",
      "category": "enum[dimension, measure, identifier, metadata]",
      "derivation": ["string"]
    }
  }
}
```

**字段说明**:

**核心执行信息**：
- `plan_id`: 分析规划的唯一标识符（UUID）
- `plan_slug`: 规划的短标识符，用于文件命名和Agent间通信，基于title生成
- `title`: 分析任务的标题
- `description`: 对此分析任务的简要描述
- `execution_steps`: **执行步骤**：
  - `step_id`: 步骤编号
  - `name`: 步骤名称
  - `operations`: **操作序列**：
    - `action`: 操作描述（如"合并渠道数据"、"品线聚合分析"）
    - `sources`: 涉及的数据源ID列表
    - `fields`: 操作涉及的字段列表
    - `field_usage`: 字段利用方式（如"以品线为主键分组，计算花费总和、转化数总和"）
    - `output`: 输出结果名称
  - `expected_output`: 该步骤预期产生的输出

**目标追踪**：
- `targets`: **目标追踪**：
  - `objectives`: 分析目标列表
  - `kpis`: 关键指标列表
  - `outcomes`: 预期成果列表

**数据映射**：
- `data_sources`: **数据源映射**：
  - `source_id`: 数据源ID作为键
    - `file`: 文件名
    - `type`: 数据源类型（structured 或 unstructured）
    - `purpose`: 用途描述
    - `fields`: **字段分组（仅结构化数据）**：
      - `core`: 核心字段列表
      - `support`: 支撑字段列表
    - `content_areas`: **内容区域（仅非结构化数据）** - 摘要文件中的主要内容区域列表，用于指引AnalysisExecutionAgent定位特定内容，如["文档概述", "关键数据与指标", "重要发现与结论", "业务洞察"]
    - `extracted_info`: **提取的关键信息（仅非结构化数据）** - 字典格式，包含从摘要文件提取的核心信息，如{"核心指标": [...], "关键发现": [...], "重要数据": [...], "业务规则": [...], "业务洞察": [...]}
    - `summary_file_path`: **摘要文件路径** - 摘要文件的相对路径，如"archives/{current_task_name}/data_source/descriptions/{filename}_summary.md"

**统计信息**：
- `field_stats`: **字段利用统计**：
  - `total_fields`: 总字段数
  - `used_fields`: 使用字段数
  - `utilization_rate`: 利用率百分比

**分析方法**：
- `methodology`: 核心方法论描述

**交付物**：
- `deliverables`: **交付物信息**：
  - `notebook`: Notebook文件名
  - `outputs`: 预期输出列表

**扩展信息（可选）**：
- `field_details`: **字段详细信息（按需展开）**：
  - `field_name`: 字段名作为键
    - `type`: 数据类型（如categorical、numeric、datetime、text等）
    - `role`: 分析角色描述
    - `category`: 角色类别（dimension/measure/identifier/metadata）
    - `derivation`: 派生计算列表

#### Agent间通信传递规范

**plan_slug传递机制**:
1. `AnalysisIdeaPlanningAgent` 生成规划时创建 `plan_slug` 并写入JSON文件
2. `IdeaValidationAgent` 读取 `plan_slug` 生成验证报告 `report_{plan_slug}_{timestamp}.md`
3. `AnalysisExecutionAgent` 读取 `plan_slug`，通过NotebookExecutorAgent创建对应的Notebook `{plan_slug}.ipynb`
4. `ResultValidationAgent` 通过Notebook文件名获取 `plan_slug`，生成结果验证报告 `result_report_{plan_slug}_{timestamp}.md`

**AnalysisExecutionAgent与NotebookExecutorAgent交互规范**:
- **交互方式**：通过Task工具调用，使用自然语言描述执行需求
- **指令类型**：创建notebook、插入/编辑cell、执行cell、查看状态等
- **返回格式**：JSON结构化结果，包含执行状态、输出内容、错误信息、操作建议
- **错误处理**：AnalysisExecutionAgent根据返回的错误信息调整代码重试
- **典型交互示例**：
  ```
  AnalysisExecutionAgent: "创建notebook文件并插入环境初始化代码"
  NotebookExecutorAgent: {"execution_status": "success", "summary": "...", "recommendations": "..."}
  ```

**数据流向图**:
```
规划JSON({plan_slug}.json) → 验证报告(report_{plan_slug}_{timestamp}.md)
                          ↓
Notebook({plan_slug}.ipynb) → 结果报告(result_report_{plan_slug}_{timestamp}.md)
                          ↓
用户反馈(feedback_{plan_slug}_{timestamp}.md)
```



## Agent执行流程和并发设计

项目的整体工作流由一系列Agent串行协作完成，但在某些阶段内部可以进行并行处理以提高效率。

### 串行执行的主流程

Agent的执行顺序遵循严格的阶段性依赖，前一阶段的输出是后一阶段的输入。

**依赖关系链**：
```
主协调器 → DataSourceFileAnalysisAgent → AnalysisIdeaPlanningAgent → IdeaValidationAgent
                                                                            ↓
ResultValidationAgent ← AnalysisExecutionAgent ←
```

**触发条件详述**：

1.  **启动与数据分析**: 主协调器 → `DataSourceFileAnalysisAgent`
    - 触发条件：archives/{current_task_name}/data_source/raw/目录下存在至少1个数据文件
    - 完成标准：archives/{current_task_name}/data_source/descriptions/目录下成功生成所有raw文件对应的描述文件（结构化数据为.json，非结构化数据为.md）
    - 状态更新：data_sources.processed 计数更新，current_phase=planning

2.  **规划与验证**: `AnalysisIdeaPlanningAgent` → `IdeaValidationAgent` → 用户审批
    - 触发条件：DataSourceFileAnalysisAgent完成 + task_background.md存在
    - 完成标准：至少生成1个规划文件，所有规划通过用户验证
    - 状态更新：analysis_plans.completed计数更新，current_phase=execution

3.  **分析执行**: 直接启动 `AnalysisExecutionAgent`
    - 触发条件：analysis_plans.completed > 0（至少有通过验证的规划）
    - 完成标准：成功生成并执行对应的Notebook
    - 状态更新：execution.completed_count更新，current_phase=result_validation

4.  **结果验证**: `AnalysisExecutionAgent` → `ResultValidationAgent`
    - 触发条件：所有Notebook成功执行完成，current_phase=result_validation
    - 验证过程：并行验证每个Notebook，生成独立的结果验证报告，更新统计信息
    - 完成标准：所有Notebook验证报告显示结果合规，overall_quality_score达到预设阈值
    - 状态更新：更新result_validation统计字段，根据验证结果决定进入completed或回退到earlier phase

### 可并行的内部任务

在上述的串行主流程中，部分Agent在执行其任务时可以进行并行操作：

**并发执行规范**：
-   **`DataSourceFileAnalysisAgent`**: 可以**并行分析**多个数据源文件，但必须等待所有文件分析完成后才能进入下一阶段
-   **`AnalysisIdeaPlanningAgent`**: 如果分析目标之间相互独立，可以**并行创建**多个分析规划文件
-   **`IdeaValidationAgent`**: 可以**并行验证**多个分析规划文件，为每个plan生成独立的验证报告
-   **`AnalysisExecutionAgent`**: 如果分析任务（Notebook）之间没有依赖关系，可以**并行执行**多个Notebook
-   **`ResultValidationAgent`**: 可以**并行验证**多个Notebook的分析结果，为每个Notebook生成独立的验证报告

**同步机制**：
- 阶段内并发：同一Agent内部可并行处理多个文件/任务
- 阶段间串行：必须等待当前阶段的所有并发任务完成后，才能触发下一阶段
- 状态同步：主协调器负责汇总并发任务的完成状态，更新project_context.json中的计数字段
- 错误处理：单个并发任务失败不影响其他任务，但需要记录失败状态供主协调器决策

## 数据源处理策略

### 数据源类型
- **结构化数据**：xlsx、csv、xls等表格文件，通常包含表头和大量数据（一般在百万行以下）
- **非结构化数据**：markdown、doc等文件，以及带有各种格式、合并单元格、图片信息的复杂表格文件
- **数据源描述文件**：用于介绍数据源文件的细节信息

### 处理策略
1. **结构化数据处理**（如csv、xlsx、xls）：
   - 读取表头信息
   - 均匀抽样读取几十行数据来了解文件结构
   - 分析数据类型、数据范围等基本信息
   - **描述策略**：生成JSON格式描述文件，包含结构化信息，后续Agent读取此描述文件足够进行规划和设计，执行时仍需访问原始文件

2. **非结构化数据处理**（如markdown、doc、带有各种格式、合并单元格、图片信息的复杂表格文件）：
   - 对于长度在十几万字以下的文件，读取全文进行分析
   - 提取关键信息和结构化内容
   - 识别文件中的表格、列表等结构化元素
   - 对于包含图片的文件，记录图片位置并提取图片文件
   - **文件大小处理**：如果中间产物文件超过20KB，自动分割成多个子文件（保留在intermediate_artifacts目录）
   - **摘要文件生成**：所有非结构化文件都生成摘要文件（作为最重要的最终产物），采用增量式处理，控制在20KB以内
   - **描述策略**：生成摘要文件作为最终产物，后续Agent优先读取摘要文件进行分析和规划

### 数据源描述文件

#### 文件位置和命名
- **位置**：`archives/{current_task_name}/data_source/descriptions/` 目录下（每个 task 使用独立的 data_source/raw/ 以避免跨任务数据混用）。
- **结构化数据文件名**：与对应数据源文件同名，扩展名为 `.json`
- **非结构化数据文件名**：摘要文件为 `{filename}_summary.md`（最重要的最终产物）
- **示例**：
  - 结构化：`sales_data.xlsx` → `sales_data.json`
  - 非结构化：`project_doc.docx` → `project_doc_summary.md`

#### 唯一标识符（source_id）规范
采用简化的唯一标识符生成方式：
- 格式：自增数字
- 示例：`1`、`2`、`3`...
- 说明：从1开始自增的数字作为唯一标识符

#### 文件格式说明
DataSourceFileAnalysisAgent 通过调用预定义脚本生成中间产物，然后基于中间产物生成最终的数据源描述文件。

##### 数据处理工作流
```
原始文件 → file_classifier.py → 判定数据类型 → 选择对应脚本 → 生成中间产物 → Agent处理 → 最终描述文件
```

**结构化数据流程**：
```
原始文件 → read_structured_data.py --intermediate → JSON输出到stdout → DataSourceFileAnalysisAgent处理：
  ├─ 解析JSON输出
  ├─ 添加source_id、description、tags等字段
  └─ 生成最终JSON描述文件 → {filename}.json（最终产物）
```
**注意**：read_structured_data.py不生成中间产物文件，只输出到stdout

**非结构化数据流程**：
```  
原始文件 → document_parser.py → MD中间产物 → Agent检查大小并分割(>20KB) → 使用frontmatter工具更新元数据 → 增强MD描述文件
```

##### 中间产物类型

**结构化数据中间产物（JSON stdout输出）**：
- 输出方式：直接输出到stdout，不生成文件
- 生成脚本：`read_structured_data.py --intermediate`
- 格式示例：
```json
{
  "analysis_type": "structured_data",
  "file_info": {
    "file_name": "sales_data.csv",
    "file_type": "csv", 
    "file_size": 1024000
  },
  "data_structure": {
    "row_count": 10000,
    "column_count": 5,
    "columns_analysis": [
      {
        "name": "用户ID",
        "type": "integer", 
        "sample_values": [1, 2, 3, 4, 5]
      },
      {
        "name": "姓名",
        "type": "text",
        "sample_values": ["张三", "李四", "王五"]
      }
    ],
    "raw_columns": ["用户ID", "姓名", "年龄", "注册时间", "状态"],
    "clean_columns": ["用户ID", "姓名", "年龄", "注册时间", "状态"]
  },
  "parsing_metadata": {
    "encoding": "utf-8",
    "delimiter": ",",
    "has_header": true,
    "decoded_header_sample": "用户ID,姓名,年龄,注册时间,状态"
  },
  "sample_data": {
    "sample_rows": [...],
    "sample_count": 20,
    "sampling_method": "uniform"
  },
  "extraction_method": "read_structured_data",
  "processing_notes": {
    "ftfy_fixed_columns": [],
    "recovered_columns": []
  }
}
```

**非结构化数据中间产物（Markdown格式）**：
- 位置：`archives/{current_task_name}/data_source/descriptions/intermediate_artifacts/{filename}_intermediate.md`
- 生成脚本：`document_parser.py`
- 格式示例：
```markdown
---
file_name: "project_background.docx"
file_type: "docx"
size: 3121353
modified_time: "2025-07-24T20:36:51.177986"
is_structured: false
extraction_method: "document_parser"
intermediate_artifacts:
  intermediate_file_path: "intermediate_artifacts/project_background_intermediate.md"
  images_count: 13
  images_directory: "intermediate_artifacts/project_background_images"
---

## 项目概述

本项目旨在构建一个智能数据分析平台，致力于提升企业数据处理能力和决策效率。

### 核心目标
1. 提升数据分析效率，缩短从数据获取到洞察输出的时间
2. 优化用户体验，降低数据分析的技术门槛
3. 建立自动化流程，实现数据处理的标准化和规模化

## 业务背景

### 市场现状
当前市场上缺乏一体化的数据分析解决方案，企业面临数据孤岛、分析工具分散、技术门槛高等挑战。

### 用户需求
- 快速数据接入和处理能力
- 直观的可视化展示
- 灵活的分析模型构建
- 可扩展的架构设计

## 技术架构

### 系统设计
采用微服务架构，包含数据接入层、处理引擎、分析服务和展示层四个核心模块。

![架构图](project_background_images/architecture.png)

### 关键技术栈
- 前端：React + TypeScript
- 后端：Python + FastAPI
- 数据库：PostgreSQL + Redis
- 消息队列：RabbitMQ
- 容器化：Docker + Kubernetes

## 文档中的图片

![示例图表](project_background_images/chart_example.png)

![流程图](project_background_images/workflow.png)
```

**非结构化数据分片文件（>20KB时生成）**：
- 位置：`archives/{current_task_name}/data_source/descriptions/intermediate_artifacts/{filename}_1.md`, `{filename}_2.md`...
- 生成工具：`file_splitter.py`
- 格式示例（第1片）：
```markdown
---
source_id: 2
file_name: "project_background.docx"
file_type: "docx"
is_structured: false
size: 45231
description: "项目背景文档，包含需求分析和业务流程描述"
extraction_method: "document_parser"
intermediate_artifacts:
  intermediate_file_path: "intermediate_artifacts/project_background_intermediate.md"
  images_count: 13
  images_directory: "intermediate_artifacts/project_background_images/"
tags: ["项目背景", "需求分析", "业务流程"]
is_split: true
part_number: 1
total_parts: 3
parent_file: "project_background.docx"
---

# 项目概述（第1部分内容）

本项目旨在构建一个智能数据分析平台...

### 核心目标
1. 提升数据分析效率
2. 优化用户体验
3. 建立自动化流程

## 业务背景

### 市场现状
当前市场上缺乏...

![image1.png](project_background_images/image1.png)
```
- 图片目录：`archives/{current_task_name}/data_source/descriptions/intermediate_artifacts/{filename}_images/`

##### 最终描述文件格式

**结构化数据描述文件（JSON格式）**：
DataSourceFileAnalysisAgent 接收stdout的JSON输出并生成符合标准schema的JSON描述文件：

```json
{
  "source_id": 1,
  "file_name": "string",
  "file_type": "enum[csv, xlsx, xls]",
  "is_structured": true,
  "size": "integer", 
  "description": "string",
  "structure": {
    "row_count": "integer",
    "column_count": "integer",
    "columns": [
      {
        "name": "string",
        "type": "enum[integer, numeric, boolean, datetime, categorical, text, unknown]",
        "sample_values": ["any"]
      }
    ]
  },
  "metadata": {
    "encoding": "string",
    "delimiter": "string", 
    "has_header": "boolean"
  },
  "intermediate_artifacts": {
    "intermediate_file_path": "string",
    "images_count": 0,
    "images_directory": null
  },
  "extraction_method": "read_structured_data",
  "tags": ["string"]
}
```

**非结构化数据最终产物（摘要文件格式）**：
DataSourceFileAnalysisAgent 调用NonstructuredSummaryAgent处理，生成摘要文件作为最终产物：

**处理流程**：
1. **上下文隔离**：不直接读取中间产物文件内容，避免占用大量上下文
2. **大小检查**：检查中间产物文件大小（使用文件系统命令，不读取内容）
3. **分片处理**（如需要）：对>20KB的中间产物进行分割，分片文件用于增量生成摘要
4. **摘要生成**：生成控制在20KB以内的摘要文件，包含完整的YAML frontmatter和标准化正文

**最终产物位置和格式**：
- **摘要文件**：`archives/{current_task_name}/data_source/descriptions/{filename}_summary.md`（所有非结构化文件的最终产物）

**处理过程文件**（非最终产物）：
- 分片文件（数据源文件 > 20KB）：`archives/{current_task_name}/data_source/descriptions/intermediate_artifacts/{filename}_1.md`, `{filename}_2.md`...（用于增量生成摘要的处理过程文件）

**摘要文件格式示例**：
````markdown
---
source_id: 2
file_name: "project_background.docx"
file_type: "docx"
is_structured: false
size: 45231
description: "项目背景文档，包含需求分析和业务流程描述"
tags: ["项目背景", "需求分析", "业务流程"]
is_summary: true
total_parts: 3
intermediate_files:
  - "intermediate_artifacts/project_background_1.md"
  - "intermediate_artifacts/project_background_2.md"
  - "intermediate_artifacts/project_background_3.md"
content_areas:
  - "文档概述"
  - "关键数据与指标"
  - "重要发现与结论"
  - "业务洞察"
extracted_info:
  核心指标:
    - "项目周期: 6个月"
    - "预算范围: 100-150万"
  关键发现:
    - "用户需求集中在移动端体验"
    - "现有系统存在性能瓶颈"
  重要数据:
    - {"名称": "日活用户", "值": "50万+"}
    - {"名称": "峰值并发", "值": "1000+"}
  业务规则:
    - "用户数据必须符合GDPR规范"
    - "系统响应时间不超过2秒"
  业务洞察:
    - "移动端优先策略将显著提升用户体验"
    - "性能优化是项目成功的关键因素"
---

# project_background.docx 核心内容摘要

## 文档概述
项目背景文档详细描述了移动端体验优化项目的需求分析、技术架构和实施计划，项目周期为6个月，预算范围100-150万元。

## 关键数据与指标
- 目标用户群体：日活50万+的移动用户
- 性能指标：系统响应时间<2秒，峰值并发1000+
- 项目时间线：6个月开发周期，分3个里程碑

## 重要发现与结论
- 用户调研显示85%的核心操作发生在移动端
- 现有系统在高并发场景下存在明显性能瓶颈
- 移动端UI/UX设计需要重点关注触屏操作体验

## 业务洞察
项目成功的关键在于平衡用户体验提升与技术实现复杂度，建议采用渐进式优化策略。
````

#### 字段说明

**通用字段（两种格式均包含）**：
- `source_id`: 自增数字唯一标识符（1, 2, 3...）
- `file_name`: 文件名（不含路径），便于识别
- `file_type`: 文件格式类型
  - 结构化数据：csv, xlsx, xls
  - 非结构化数据：markdown, doc, docx, pdf, txt, other
- `is_structured`: 是否为结构化数据（true/false），基于文件内容判定而非文件格式
- `size`: 文件大小（字节）
- `description`: 基于文件内容和背景信息生成的中文描述
- `tags`: 关键词标签数组，基于文件名、内容、背景信息生成

**结构化数据专有字段**：
- `structure`: 数据结构信息
  - `row_count`: 总行数
  - `column_count`: 总列数
  - `columns`: 每列的信息数组
    - `name`: 列名
    - `type`: 数据类型（integer, numeric, boolean, datetime, categorical, text, unknown）
    - `sample_values`: 抽样值示例数组
- `metadata`: 文件元数据
  - `encoding`: 文件编码（如utf-8, gbk）
  - `delimiter`: 分隔符（适用于CSV等格式，如","、"\t"）
  - `has_header`: 是否包含表头（boolean）

**非结构化数据特殊说明**：
- 元数据通过YAML frontmatter形式记录在MD文件头部
- 文件正文包含完整的原始内容，保留所有上下文信息
- 后续Agent只读取此MD描述文件，无需访问原始文件

**中间产物信息**：
- `intermediate_artifacts`: 中间产物信息（新增字段）
  - `intermediate_file_path`: 中间产物文件的相对路径
  - `images_count`: 提取的图片数量（0表示无图片）
  - `images_directory`: 图片目录的相对路径（仅当images_count > 0）
- `extraction_method`: 数据提取方法（string）
  - 结构化数据："read_structured_data" 
  - 非结构化数据："document_parser"

**分片特有字段（仅当文件被分割时）**：
- `is_split`: 是否为分割文件（boolean）
- `part_number`: 当前分片序号（integer）
- `total_parts`: 总分片数（integer）
- `parent_file`: 原始文件名（string）

#### 数据源描述文件读取规则

**后续Agent读取规则**：
1. **结构化数据（.json描述文件）**：
   - AnalysisIdeaPlanningAgent：读取JSON描述文件进行规划设计
   - IdeaValidationAgent：读取JSON描述文件验证数据可用性
   - AnalysisExecutionAgent：只读取规划文件，执行时从 archives/{current_task_name}/data_source/raw/ 加载原始数据
   - ResultValidationAgent：读取JSON描述文件进行结果验证

2. **非结构化数据（摘要文件）**：
   - AnalysisIdeaPlanningAgent：读取摘要文件（{filename}_summary.md）进行规划设计
   - IdeaValidationAgent：读取摘要文件验证内容完整性
   - AnalysisExecutionAgent：只读取规划文件中的extracted_info
   - ResultValidationAgent：读取摘要文件进行结果验证

3. **摘要文件（{filename}_summary.md）**：
   - **生成条件**：所有非结构化数据文件都生成（作为最重要的最终产物）
   - **生成逻辑**：
     * ≤20KB文件：基于完整内容生成摘要
     * >20KB文件：采用增量式生成
     * 读取第一个分片 → 生成初始摘要
     * 读取下一个分片 → 提取新信息 → 合并到现有摘要 → 更新摘要文件
     * 重复直到所有分片处理完成
   - **增量更新策略**：每处理一个分片就更新一次摘要，避免同时加载所有分片
   - **长度控制**：每次更新后检查大小，如果接近20KB则进行智能压缩
   - **内容格式**：
     ```markdown
     # {原文件名} 核心内容摘要
     
     ## 文档概述
     [简要描述文档类型、用途、时间范围等]
     
     ## 关键数据与指标
     - [核心数据点1]
     - [核心数据点2]
     
     ## 重要发现与结论
     [主要发现和结论的自然语言描述]
     
     ## 关键表格与图表说明
     [重要表格的简化版本或说明]
     
     ## 业务洞察
     [对分析有价值的业务信息]
     ```
   - **用途**：避免Agent读取大文件，提供精炼的信息概览，作为规划文件中extracted_info的数据来源