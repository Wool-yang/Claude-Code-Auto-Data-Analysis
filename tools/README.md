# 工具脚本说明

## 目录结构

```
tools/
├── data_readers/               # 数据读取和分析工具
│   ├── file_classifier.py      # 文件类型分类器
│   ├── read_structured_data.py  # 结构化数据处理脚本
│   ├── document_parser.py       # 非结构化数据处理脚本
│   └── README.md               # 数据读取工具详细说明
├── notebook_runners/           # Notebook运行器相关工具
│   ├── nb_runner.py           # Notebook运行器脚本
│   └── README_nb_runner.md    # 运行器使用说明
└── README.md                  # 本文件
```

## 工具说明

### data_readers

此目录包含用于 DataSourceFileAnalysisAgent 的数据源分析工具，实现了完整的数据处理流程：

#### 核心脚本

- **file_classifier.py**: 智能文件类型分类器
  - 自动判定文件为结构化或非结构化数据
  - 支持图片检测，有图片的文件自动归类为非结构化
  - 输出分类结果和推荐处理脚本

- **read_structured_data.py**: 结构化数据处理脚本
  - 处理 CSV、Excel 等结构化数据文件
  - 强大的编码检测和数据类型推断
  - 生成 JSON 格式中间产物供 Agent 使用

- **document_parser.py**: 非结构化数据处理脚本
  - 处理 Markdown、Word、复杂 Excel 等文档类型
  - 支持图片提取和图文混排处理
  - 生成 Markdown 格式中间产物

#### 数据处理流程

```
原始文件 → file_classifier.py → 判定数据类型 → 选择对应脚本 → 生成中间产物 → DataSourceFileAnalysisAgent融合分析 → 最终描述文件（JSON或MD）
```

#### 中间产物类型

- **结构化数据**: 生成 `{filename}_intermediate.json`，包含数据结构分析、类型推断、采样数据等
- **非结构化数据**: 生成 `{filename}_intermediate.md`，包含全文内容、提取的图片、表格转换等

详细使用方法请参考 `data_readers/README.md`

### notebook_runners

此目录包含用于运行和管理 Jupyter Notebook 的工具脚本：

- `nb_runner.py`: 主要的 Notebook 运行脚本，支持运行整个 Notebook、特定单元格或单元格范围
- `README_nb_runner.md`: 详细的使用说明文档

## 使用方法

请查看各个子目录中的 README 文件获取具体的使用方法和参数说明。

## 与 Multi-Agent 系统的集成

这些工具脚本是 Claude Code 自动化数据分析系统的重要组成部分：

- **DataSourceFileAnalysisAgent** 使用 `data_readers` 工具进行数据源分析
- **AnalysisExecutionAgent** 使用 `notebook_runners` 工具执行分析代码
- 所有脚本都支持 UTF-8 编码，确保在 Windows 环境下的中文兼容性

## 开发规范

1. **编码统一**: 所有脚本都使用 UTF-8 编码输出
2. **错误处理**: 采用统一的错误处理和容错机制
3. **路径兼容**: 使用 `os.path.normpath()` 确保 Windows 路径兼容性
4. **中间产物**: 统一保存在 `intermediate_artifacts` 目录下
5. **文档维护**: 每个工具目录都包含详细的 README 说明文档