# Claude Code 配置

## 项目概述

### 项目目标

构建一个通用数据分析Multi-Agent系统，能够适应各种场合的数据分析任务，通过多个专门Agent的协作，实现从数据源分析到结果验证的完整流程自动化。

### 项目架构

本项目采用Multi-Agent架构，包含以下核心Agent：

#### 主流程协调器
作为项目的主协调器，我将负责整个分析流程的推进。我的核心职责如下：

**1. 项目初始化:**
*   读取 `docs/project_background.md`，获取项目名称和核心目标。
*   初始化 `project_config/project_context.json`，设置项目ID、名称、初始状态等全局信息。
*   根据项目名称，在Jupyter根目录 (`D:\Program\jupyter`) 创建对应的工程目录。

**2. 流程控制与任务分发:**
*   严格按照本文档定义的 **串行主流程** 顺序，依次启动和协调其他专门的Subagent。
*   监控 `project_context.json` 中的 `current_phase` 和 `status`，确保各阶段任务按时完成。
*   将当前阶段的产物（如数据源描述文件、分析规划文件等）作为输入，传递给下一个Subagent。

**3. 上下文维护:**
*   实时更新 `project_context.json` 文件，反映项目的最新状态和进度。
*   确保所有Subagent都能通过上下文文件获取到一致的、最新的项目信息。

**4. 用户交互:**
*   作为与你的主要交互接口。
*   在关键节点（如 `IdeaValidationAgent` 验证后）向你汇报进展和Subagent的产出。
*   收集你的反馈，并根据反馈调整后续工作或重新启动特定流程。
*   在流程最终完成后，向你交付最终成果。

**5. 错误处理与重试:**
*   监控Subagent的执行状态，如果某个Agent执行失败，我会根据预设逻辑进行重试或向你报告错误。
*   管理 `AnalysisIdeaPlanningAgent` 和 `IdeaValidationAgent` 之间的迭代循环，直到所有分析规划都得到你的确认。

**我的工作流程将遵循以下阶段：**

1.  **Phase 1: 启动与数据分析**
    *   **Action**: 启动 `DataSourceFileAnalysisAgent`。
    *   **Input**: `data_source/raw/` 目录下的原始数据文件。
    *   **Output**: 等待 `DataSourceFileAnalysisAgent` 生成所有数据源的描述文件。
    *   **Context Update**: 更新 `current_phase` 为 `data_analysis`，更新 `data_sources` 计数。

2.  **Phase 2: 规划与验证**
    *   **Action**: 启动 `AnalysisIdeaPlanningAgent`。
    *   **Input**: 数据源描述文件和 `project_background.md`。
    *   **Output**: 等待 `AnalysisIdeaPlanningAgent` 生成所有分析规划文件。
    *   ---
    *   **Action**: 启动 `IdeaValidationAgent` 对所有规划文件进行验证，并向你报告结果，等待你的确认。
    *   **If** 你确认通过: 进入下一阶段。
    *   **Else**: 根据你的反馈，再次启动 `AnalysisIdeaPlanningAgent` 令其修改规划，然后重复验证步骤。

3.  **Phase 3: 设计与执行**
    *   **Action**: 启动 `CodeStructureDesignAgent`。
    *   **Input**: 所有已通过验证的分析规划文件。
    *   **Output**: 等待 `CodeStructureDesignAgent` 生成所有代码设计文件。
    *   ---
    *   **Action**: 启动 `AnalysisExecutionAgent`。
    *   **Input**: 所有代码设计文件。
    *   **Output**: 等待 `AnalysisExecutionAgent` 在Jupyter工程目录下执行并生成所有分析Notebook。

4.  **Phase 4: 结果验证**
    *   **Action**: 启动 `ResultValidationAgent`。
    *   **Input**: 所有已执行完毕的Notebook。
    *   **Output**: 等待 `ResultValidationAgent` 完成结果验证并向你报告。
    *   **If** 你指示结果异常: 根据你的反馈，重新触发相关流程。

5.  **Phase 5: 项目完成**
    *   **Action**: 向你报告项目完成，并提供最终产出物的路径。
    *   **Context Update**: 更新 `status` 为 `completed`。

### 主流程协调器补充规范

#### 状态机与流转
- Phase 1 data_analysis：进入前设置 status=running；完成后保持 running；失败单项重试至多2次，仍失败则 status=failed 并停止
- Phase 2 planning→validation：规划完成后进入验证；若用户未批准，携带修改意见回到 planning；批准数计入 analysis_plans.completed
- Phase 3 code_design→execution：全部通过验证的规划才进入设计；所有设计完成后再进入执行
- Phase 4 result_validation：通过则进入 Phase 5；不通过则按报告建议回退到 execution 或更早阶段
- Phase 5 completed：设置 status=completed，并输出最终产物路径

#### 上下文写入规范
- 时间：last_updated 使用 ISO8601（UTC 或含时区）
- 原子写：写入 project_context.json 时先写临时文件再替换，避免部分写入
- 幂等与续跑：同一阶段可安全重复执行；支持 --resume 从 current_phase 继续
- 计数规则：
  - data_sources.count 为 raw 文件总数，processed 为成功生成描述文件数
  - analysis_plans.count 为规划文件总数，completed 为用户批准数量
- 路径：notebook_dir= "D:\\Program\\jupyter\\{project_name}"，不存在则创建

#### 用户审批门控
- 验证输出：docs/analysis_plans/validation/report_{timestamp}.md 与 summary_{timestamp}.md
- 等待用户审批：批准→进入下一阶段；不批准→记录修改意见并回到 planning
- 修改意见保存：docs/analysis_plans/validation/feedback_{timestamp}.md（可选）

#### 运行与安全保障
- 并发与超时：阶段内 Agent 可并行；为长任务设定合理超时与重试
- 回退策略：执行或验证失败时仅重跑受影响的规划/Notebook，避免全量重跑
- 日志：按阶段写入 logs/{phase}/YYYYMMDD_HHMMSS.log，记录进度、告警与错误摘要
- 安全：日志中脱敏，不写入敏感原文；不记录大体量样本，仅最小必要信息
- Windows 兼容：统一使用双反斜杠或转义路径，避免编码问题

#### 项目初始化细化
- 从 docs/project_background.md 读取 project_name；若 project_id 为空则生成 UUID
- 初始化/更新 project_context.json 字段并写入 last_updated；确保 notebook_dir 就绪

#### 与子Agent的契约
- 阶段边界严格串行；产物路径与计数更新由主协调器负责聚合

#### DataSourceFileAnalysisAgent（数据源文件分析Agent）
读取数据源，来构建描述文件实现对数据源的内容实现精准描述（此处会预先写一些脚本来实现不同格式、不同条件文件在这里的读取逻辑）
- 规范化数据：如csv xlsx xls等等，表头+大量数据（一般在百万行以下），读取表头，均匀抽样读取几十行数据来了解文件结构
- 非规范化数据：如markdown、doc、和带有各种格式+合并单元格+图片信息的表格文件等等，此类文件一般为背景信息文件，如果长度不是特别长（十几万字以下），可以读取全文进行分析

#### AnalysisIdeaPlanningAgent（分析思路规划Agent）
根据数据源描述文件以及项目背景文件，细化出分析规划文件
- 分析规划文件为基于背景文件中的多个分析目标、分析关键指标、分析目标结论，以及数据源中数据的数量、种类综合得出的一系列文件
- 此类文件不需要涉及到分析代码的构建思路，而是更多着眼于通过何种数据分析思想可以得出预期的分析成果，着重于分析思路的构建
- 每个文件会对应创建一个 ipynb 文件，代表了一段连贯完整的分析(对应了某个或者某些分析目标、指标、结论），同时也会基于每个分析的上下文范围来规定使用到的数据源文件有哪些

#### IdeaValidationAgent（思路验证Agent）
此 Agent 负责结合项目背景和数据源描述，对 `AnalysisIdeaPlanningAgent` 生成的规划文件进行评估验证。其产出为一份详细的验证报告文件，以及一份对该报告的概括总结。

我（主流程协调器）会将报告原文和概括一并呈现给你。
-   **若你批准**：流程将进入下一阶段。
-   **若你不批准**：我会向你征求具体的修改意见，然后将这些意见传递给 `AnalysisIdeaPlanningAgent`，由其对规划进行修改，并重新开始此验证流程，直到规划获得你的批准。

#### CodeStructureDesignAgent（代码结构设计Agent）
根据AnalysisIdeaPlanningAgent生成的若干分析规划文件，来生成代码设计文件
- 代码设计文件为更贴近于 ipynb 中 python 数据分析代码的文件，进一步阐述分析规划文件中的分析思路转化到对应的一系列分析代码的构建思路
- 此处仍然不需要构建出完整的代码，是简单的代码步骤对应伪代码、文字信息皆可，目标是描述清晰之后AnalysisExecutionAgent的任务步骤

#### AnalysisExecutionAgent（分析执行Agent）
基于所有代码设计文件，开始进行 ipynb 文件的编写
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
  - 根据项目背景文件中的项目名称，在此目录下创建同名工程目录
  - 只在当前项目对应的文件夹中进行创建和编辑 ipynb 文件

### 运行环境配置

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
│   └── agents/                                     # Agent实现文件
├── CLAUDE.md                                       # 本项目配置文件
├── project_config/                                 # 项目配置目录
│   └── project_context.json                        # 项目全局上下文文件
├── data_source/                                    # 数据源目录
│   ├── raw/                                        # 原始数据文件
│   └── descriptions/                               # 数据源描述文件
├── docs/                                           # 项目文档目录
│   ├── project_background.md                       # 项目背景文件
│   ├── analysis_plans/                             # 分析规划文件
│   └── code_designs/                               # 代码设计文件
├── tools/                                          # 工具脚本目录
│   ├── notebook_runners/                           # Notebook运行器相关工具
│   │   ├── nb_runner.py                            # Notebook运行器脚本
│   │   └── README_nb_runner.md                     # 运行器使用说明
│   └── README.md                                   # 工具脚本说明文档
└── logs/                                           # 日志目录
```

### 工具脚本说明文档规则

1. **文档位置**：每个工具脚本目录下都应包含一个 `README.md` 文件，用于说明该目录下工具的使用方法和功能。
2. **文档内容**：
   - 工具的主要功能
   - 使用方法和参数说明
   - 依赖项说明
   - 示例用法
3. **文档维护**：当工具脚本更新时，相应的说明文档也应及时更新。

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
  "current_phase": "enum[data_analysis, planning, validation, code_design, execution, result_validation]",
  "data_sources": {
    "count": "integer",
    "processed": "integer"
  },
  "analysis_plans": {
    "count": "integer",
    "completed": "integer"
  },
  "last_updated": "datetime"
}
```

**字段说明**:
- `project_id`: 项目的唯一标识符。
- `project_name`: 项目名称，从项目背景文件中读取。用于在Jupyter Notebook根目录下创建同名工程目录。
- `notebook_dir`: Jupyter Notebook工程目录的完整路径。
- `status`: 项目的整体状态。
- `current_phase`: 项目当前所处的阶段。
- `data_sources`: 数据源处理状态。
  - `count`: 数据源文件总数。
  - `processed`: 已处理的数据源文件数。
- `analysis_plans`: 分析规划处理状态。
  - `count`: 分析规划文件总数。
  - `completed`: 已完成的分析规划数。
- `last_updated`: 上下文文件的最后更新时间。


### 2. 分析规划文件 (`docs/analysis_plans/*.json`)

由`AnalysisIdeaPlanningAgent`生成，每一个文件都详细描述一个具体的分析任务，是后续代码设计和执行的蓝图。分析规划文件基于项目背景文件中的分析目标、关键指标和预期结论，结合数据源的实际情况进行设计。

```json
{
  "plan_id": "uuid",
  "title": "string",
  "description": "string",
  "related_objectives": ["string"],
  "related_key_indicators": ["string"],
  "expected_conclusions": ["string"],
  "data_sources_used": ["source_id"],
  "methodology": "string",
  "analysis_approach": "string",
  "steps": [
    {
      "step_id": "integer",
      "description": "string",
      "expected_output": "string"
    }
  ],
  "deliverables": {
    "notebook_file": "string",
    "expected_outputs": ["string"]
  }
}
```

**字段说明**:
- `plan_id`: 分析规划的唯一标识符。
- `title`: 分析任务的标题。
- `description`: 对此分析任务的简要描述。
- `related_objectives`: 关联的项目背景中的分析目标。
- `related_key_indicators`: 关联的项目背景中的关键指标。
- `expected_conclusions`: 预期得出的结论。
- `data_sources_used`: 本次分析需要用到的数据源ID列表。
- `methodology`: 本次分析所采用的核心方法论或模型概述。
- `analysis_approach`: 分析思路和方法，描述如何通过数据分析得出预期结论。
- `steps`: 具体的分析步骤。
  - `step_id`: 步骤编号。
  - `description`: 该步骤的详细描述。
  - `expected_output`: 该步骤预期产生的输出或结论。
- `deliverables`: 交付物信息。
  - `notebook_file`: 对应的Jupyter Notebook文件名。
  - `expected_outputs`: 预期的分析输出结果（图表、数据表等）。


### 3. 代码设计文件 (`docs/code_designs/*.md`)

由`CodeStructureDesignAgent`生成，将分析规划中的思路转化为更贴近代码实现的伪代码或文字描述，指导`AnalysisExecutionAgent`的工作。

````markdown
# Code Design for: {plan_title}

## Cell 1: 导入库和环境设置
- **描述**: 导入所有需要的Python库，例如pandas, matplotlib等。
- **伪代码**:
  - `import pandas as pd`
  - `import matplotlib.pyplot as plt`

## Cell 2: 加载数据
- **描述**: 根据分析规划中指定的`data_sources_used`，从`{data_source_path}`加载数据。
- **伪代码**:
  - `sales_df = pd.read_excel('path/to/sales_data.xlsx')`
  - `customer_df = pd.read_csv('path/to/customer_data.csv')`

## Cell 3: 数据预处理
- **描述**: 对加载的数据进行清洗，如处理缺失值、转换数据类型等。
- **伪代码**:
  - `sales_df.dropna(inplace=True)`
  - `sales_df['OrderDate'] = pd.to_datetime(sales_df['OrderDate'])`

## Cell 4: 分析步骤 - {step_1_description}
- **描述**: {step_1_description}
- **实现思路**:
  - 1. 按月分组销售数据。
  - 2. 计算每月的总销售额。
  - 3. 绘制月度销售趋势图。
````

## Agent执行流程和并发设计

项目的整体工作流由一系列Agent串行协作完成，但在某些阶段内部可以进行并行处理以提高效率。

### 串行执行的主流程

Agent的执行顺序遵循严格的阶段性依赖，前一阶段的输出是后一阶段的输入。

1.  **启动与数据分析**: 主流程协调器 -> `DataSourceFileAnalysisAgent`
    - 主流程协调器初始化项目后，启动`DataSourceFileAnalysisAgent`。
    - `DataSourceFileAnalysisAgent`必须完成对所有数据源的分析并生成统一的数据源描述文件后，流程才能进入下一阶段。

2.  **规划与验证**: `DataSourceFileAnalysisAgent` -> `AnalysisIdeaPlanningAgent` -> `IdeaValidationAgent`
    - `AnalysisIdeaPlanningAgent`接收数据源描述，生成所有分析规划文件。
    - `IdeaValidationAgent`对所有分析规划文件进行验证并生成报告。我（主流程协调器）会将报告呈现给你，等待你的确认后，才能进入下一阶段。如果需要修改，此流程将迭代进行。

3.  **设计与执行**: `IdeaValidationAgent` -> `CodeStructureDesignAgent` -> `AnalysisExecutionAgent`
    - `CodeStructureDesignAgent`接收所有通过验证的分析规划，并为它们创建代码设计文件。
    - `AnalysisExecutionAgent`必须等待所有代码设计文件完成后，才开始生成和执行Notebook。

4.  **结果验证**: `AnalysisExecutionAgent` -> `ResultValidationAgent`
    - `ResultValidationAgent`对所有Notebook的执行结果进行验证并生成报告。我（主流程协调器）将根据报告和你的指令决定后续步骤。

### 可并行的内部任务

在上述的串行主流程中，部分Agent在执行其任务时可以进行并行操作：

-   **`DataSourceFileAnalysisAgent`**: 可以**并行分析**多个数据源文件。
-   **`AnalysisIdeaPlanningAgent`**: 如果分析目标之间相互独立，可以**并行创建**多个分析规划文件。
-   **`IdeaValidationAgent`**: 可以**并行验证**多个分析规划文件。
-   **`CodeStructureDesignAgent`**: 可以**并行生成**多个代码设计文件。
-   **`AnalysisExecutionAgent`**: 如果分析任务（Notebook）之间没有依赖关系，可以**并行执行**多个Notebook。
-   **`ResultValidationAgent`**: 可以**并行验证**多个Notebook的分析结果。

## 数据源处理策略

### 数据源类型
- **结构化数据**：xlsx、csv、xls等表格文件，通常包含表头和大量数据（一般在百万行以下）
- **非结构化数据**：markdown、doc等文件，以及带有各种格式、合并单元格、图片信息的复杂表格文件
- **数据源描述文件**：用于介绍数据源文件的细节信息

### 处理策略
1. **规范化数据处理**（如csv、xlsx、xls）：
   - 读取表头信息
   - 均匀抽样读取几十行数据来了解文件结构
   - 分析数据类型、数据范围等基本信息

2. **非规范化数据处理**（如markdown、doc、带有各种格式、合并单元格、图片信息的复杂表格文件）：
   - 对于长度在十几万字以下的文件，可以读取全文进行分析
   - 提取关键信息和结构化内容
   - 识别文件中的表格、列表等结构化元素
   - 对于包含图片的文件，记录图片位置和相关信息

### 数据源描述文件

#### 文件位置和命名
- **位置**：`data_source/descriptions/` 目录下
- **文件名**：与对应数据源文件同名，但扩展名为 `.json`
- **示例**：对于 `data_source/sales_data.xlsx`，描述文件为 `data_source/descriptions/sales_data.json`

#### 唯一标识符（source_id）规范
采用简化的唯一标识符生成方式：
- 格式：自增数字
- 示例：`1`、`2`、`3`...
- 说明：从1开始自增的数字作为唯一标识符

#### 文件格式说明
DataSourceFileAnalysisAgent将使用预定义的脚本处理所有数据源文件，并将信息写入描述文件中。描述文件采用JSON格式，结构如下：

```json
{
  "source_id": "1",
  "file_name": "string",
  "file_type": "enum[csv, xlsx, xls, markdown, doc, other]",
  "is_structured": "boolean",
  "size": "integer",
  "description": "string",
  "structure": {
    "row_count": "integer",
    "column_count": "integer",
    "columns": [
      {
        "name": "string",
        "type": "string",
        "sample_values": ["any"]
      }
    ]
  },
  "metadata": {
    "encoding": "string",
    "delimiter": "string",
    "has_header": "boolean"
  },
  "tags": ["string"]
}
```

#### 字段说明
- `source_id`: 自增数字唯一标识符
- `file_name`: 文件名（不含路径），便于识别
- `file_type`: 文件格式类型（csv, xlsx, xls, markdown, doc等）
- `is_structured`: 是否为结构化数据（true/false），与文件格式无关，表示数据是否具有清晰的行列结构
- `size`: 文件大小（字节）
- `description`: 人工编写的描述信息，便于理解文件内容
- `structure`: 数据结构信息
  - `row_count`: 总行数
  - `column_count`: 总列数
  - `columns`: 每列的信息
    - `name`: 列名
    - `type`: 数据类型
    - `sample_values`: 抽样值示例
- `metadata`: 文件元数据
  - `encoding`: 文件编码
  - `delimiter`: 分隔符（适用于CSV等格式）
  - `has_header`: 是否包含表头
- `tags`: 自定义标签，便于分类和搜索