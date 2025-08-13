# 工具脚本说明

## 目录结构

```
tools/
├── data_readers/               # 数据读取和分析工具
│   ├── file_classifier.py      # 文件类型分类器
│   ├── read_structured_data.py  # 结构化数据处理脚本
│   ├── document_parser.py       # 非结构化数据处理脚本
│   ├── file_splitter.py         # 文件分割工具
│   ├── frontmatter_tool.py      # Frontmatter处理工具
│   ├── README.md               # 数据读取工具详细说明
│   ├── README_file_splitter.md  # 文件分割工具说明
│   └── README_frontmatter_tool.md # Frontmatter工具说明
├── notebook_runners/           # Notebook运行器相关工具
│   ├── nb_runner.py           # Notebook运行器脚本
│   └── README_nb_runner.md    # 运行器使用说明
├── notebook_config/           # Notebook环境初始化工具
│   ├── notebook_env_config.md # Notebook环境配置模板
│   └── README.md              # 环境配置使用说明
└── README.md                  # 本文件
```

## 数据处理流程

DataSourceFileAnalysisAgent 通过 Bash 工具调用脚本处理数据：

```
原始文件 → file_classifier.py → 判定数据类型 → 选择对应脚本 → 生成中间产物 → 检查文件大小 → file_splitter.py(如需要) → frontmatter_tool.py → 最终描述文件（JSON或MD）
```

### 处理示例

#### 结构化数据处理
```bash
# 1. 分类文件
python tools/data_readers/file_classifier.py data.csv

# 2. 生成中间产物
python tools/data_readers/read_structured_data.py --files data.csv --intermediate --sample_rows 20
```

#### 非结构化数据处理
```bash
# 1. 分类文件
python tools/data_readers/file_classifier.py document.docx

# 2. 生成中间产物
python tools/data_readers/document_parser.py document.docx

# 3. 检查大小并分割（如需要）
python tools/data_readers/file_splitter.py intermediate.md -s 20 --delete-original

# 4. 添加 frontmatter
python tools/data_readers/frontmatter_tool.py single intermediate.md \
  --frontmatter '{"source_id": "1", "description": "..."}' \
  -o final.md --merge update
```

## 工具说明

### data_readers

数据源分析工具集，实现了完整的数据处理流程：

- **file_classifier.py**: 智能文件类型分类器
  - 自动判定文件为结构化或非结构化数据
  - 支持图片检测，有图片的文件自动归类为非结构化

- **read_structured_data.py**: 结构化数据处理脚本
  - 处理 CSV、Excel 等结构化数据文件
  - 强大的编码检测和数据类型推断
  - 生成 JSON 格式中间产物供 Agent 使用

- **document_parser.py**: 非结构化数据处理脚本
  - 处理 Markdown、Word、复杂 Excel 等文档类型
  - 支持图片提取和图文混排处理
  - 生成 Markdown 格式中间产物

- **file_splitter.py**: 文件分割工具
  - 智能分割超过 20KB 的 Markdown 文件
  - 在标题处分割，保持内容完整性
  - 自动处理分片文件的 frontmatter

- **frontmatter_tool.py**: Frontmatter 处理工具
  - 流式处理文件，添加或更新 YAML frontmatter
  - 支持多种合并策略（update/replace/merge_deep）
  - 避免大文件内存占用

详细使用方法请参考 `data_readers/README.md`

### notebook_runners

Jupyter Notebook 运行和管理工具：

- **nb_runner.py**: Notebook 运行脚本
  - 支持运行整个 Notebook、特定单元格或单元格范围
  - 提供执行结果验证和错误处理

#### 使用示例

AnalysisExecutionAgent 通过 Bash 工具调用脚本执行 Notebook：

```bash
# 运行整个 Notebook
python tools/notebook_runners/nb_runner.py "D:\Program\jupyter\{project_name}\{current_task_name}\analysis.ipynb" --all

# 运行特定单元格（如第 0, 2, 4 个单元格）
python tools/notebook_runners/nb_runner.py notebook.ipynb --cells "0,2,4"

# 运行单元格范围（如第 1-3 个单元格）
python tools/notebook_runners/nb_runner.py notebook.ipynb --range "1-3"

# 列出所有单元格信息
python tools/notebook_runners/nb_runner.py notebook.ipynb --list

# 读取特定单元格的输出
python tools/notebook_runners/nb_runner.py notebook.ipynb --read-cell "2"
```

详细使用方法请参考 `notebook_runners/README_nb_runner.md`

### notebook_config

Notebook 环境初始化工具：

- **notebook_env_config.md**: Notebook 环境初始化代码模板
  - 导入数据分析必要的基础库（pandas, numpy, plotly等）
  - 配置Python环境设置（警告过滤、显示选项等）
  - 设置Plotly中文字体和可视化模板
  - 解决中文字符显示和图表导出问题

详细使用方法请参考 `notebook_config/README.md`

## 与 Multi-Agent 系统的集成

这些工具脚本是 Claude Code 自动化数据分析系统的重要组成部分：

- **DataSourceFileAnalysisAgent** 使用 `data_readers` 工具进行数据源分析
- **AnalysisExecutionAgent** 使用 `notebook_runners` 工具执行分析代码，使用 `notebook_config` 工具初始化Notebook环境
- 所有脚本都支持 UTF-8 编码，确保在 Windows 环境下的中文兼容性

## 开发规范

1. **编码统一**: 所有脚本都使用 UTF-8 编码输出
2. **错误处理**: 采用统一的错误处理和容错机制
3. **路径兼容**: 使用 `os.path.normpath()` 确保 Windows 路径兼容性
4. **中间产物**: 统一保存在 `intermediate_artifacts` 目录下
5. **文档维护**: 每个工具目录都包含详细的 README 说明文档