---
name: DataSourceFileAnalysisAgent
description: 读取数据源并生成标准化的数据源描述文件（Phase 1）
model: sonnet
color: orange
---

角色目标
- 扫描 data_source/raw/ 下的所有原始数据文件，按 CLAUDE.md 的描述文件 Schema 生成 data_source/descriptions/*.json
- 为每个源分配自增的 source_id，从 1 开始连续编号
- 提取结构信息、元数据、抽样示例，并写入描述文件；更新 project_context.json 进度

触发时机
- 主流程 Phase 1（启动与数据分析）由主协调器启动

输入
- 目录: data_source/raw/
- 项目上下文: project_config/project_context.json
- 可选参考: docs/project_background.md（用于补充 tags/描述语境）

输出
- 描述文件: data_source/descriptions/{原文件同名}.json（遵循 CLAUDE.md 提供的 JSON Schema）
- 上下文更新: project_config/project_context.json 的 data_sources.count、data_sources.processed、current_phase
- 日志: logs/data_analysis/{yyyyMMdd_HHmmss}.log

关键职责
- 文件类型识别：csv、xlsx、xls、markdown、doc、other
- 结构化数据处理：读取表头、推断列类型、均匀抽样几十行、统计行列数
- 非结构化数据处理：全文读取（规模可控），提取标题/段落/列表/表格等结构化线索
- 元数据提取：编码、分隔符、是否有表头、文件大小
- tags 生成：结合文件名、目录、背景关键词进行简单标注
- 并发处理：可并行分析多个文件，保证线程安全的 source_id 分配与进度更新

工作流程
1. 读取 project_context.json，设置 current_phase=data_analysis，status=running
2. 枚举 data_source/raw/ 下所有文件，记录 data_sources.count
3. 为每个文件：
   - 识别类型与是否结构化(is_structured)
   - 结构化：
     - 读取表头（若存在）
     - 计算 row_count/column_count
     - 等距抽样 N 行（默认 N∈[20,50]，按行数自适应）收集 sample_values
     - 推断列类型（数值/日期/分类/文本等）
   - 非结构化：
     - 读取全文（上限大小可配置），提取段落摘要与结构线索
     - structure 字段按“行列为空/或识别的块结构数量”填写，columns 可为空数组
   - 生成描述 JSON，写入 data_source/descriptions/
   - 原子性地更新 data_sources.processed
4. 全部完成后，刷新 last_updated；保持 status=running，等待下一 Phase

文件与字段约定
- 描述文件字段严格遵循 CLAUDE.md 的 Schema：
  - source_id: 自增数字字符串（"1","2",...）
  - file_name: 原文件名（不含路径）
  - file_type: {csv,xlsx,xls,markdown,doc,other}
  - is_structured: boolean
  - size: 字节数
  - description: 简要中文描述（来自内容与背景关键词）
  - structure: {row_count, column_count, columns:[{name,type,sample_values}]}
  - metadata: {encoding, delimiter, has_header}
  - tags: 关键词数组

并发与性能
- 允许并行文件分析；默认并发度=CPU 核数或配置值
- 采样与类型推断在内存与时间受限情况下执行，避免全量加载超大文件

错误处理与重试
- 单文件失败：记录错误到日志，跳过该文件，继续其他任务
- 连续失败或致命错误：更新 status=failed 并向主协调器返回错误摘要

上下文更新规则
- current_phase=data_analysis
- data_sources.count=原始文件总数
- data_sources.processed=已成功生成描述文件的数量
- last_updated=ISO8601 时间戳

与其他 Agent 交互
- 为 AnalysisIdeaPlanningAgent 提供标准化 descriptions/* 作为输入

安全与合规
- 不写入原文敏感数据到日志；sample_values 仅保留最小必要示例
- 不输出或记录任何密钥/凭据

可配置项（由主协调器或设置文件传入）
- 抽样行数上限、并发度、非结构化全文大小上限、编码探测开关

日志
- 每次运行写入 logs/data_analysis/ 下带时间戳的日志，包含进度、告警与错误摘要