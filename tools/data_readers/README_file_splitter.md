# 文件分割工具 (file_splitter.py)

## 功能概述
用于将大型Markdown文件分割成多个较小的文件，确保每个分片不超过指定大小（默认20KB）。

## 主要特性
- 智能分割：保持Markdown结构的完整性（段落、代码块、表格等）
- frontmatter处理：自动为每个分片维护完整的YAML frontmatter
- 灵活配置：可自定义分片大小和输出目录

## 使用方法

### 命令行使用
```bash
python file_splitter.py input_file.md [选项]
```

### 参数说明
- `input_file`: 必需，输入的Markdown文件路径
- `-o, --output-dir`: 可选，输出目录（默认为输入文件所在目录）
- `-s, --max-size`: 可选，每个分片的最大大小，单位KB（默认20）
- `--delete-original`: 可选，分割后删除原文件

### 使用示例

1. 基本分割（保留原文件）：
```bash
python file_splitter.py data_description.md
```

2. 指定输出目录和大小：
```bash
python file_splitter.py data_description.md -o ./output -s 15
```

3. 分割后删除原文件：
```bash
python file_splitter.py data_description.md --delete-original
```

### Python代码调用
```python
from file_splitter import split_file

# 分割文件
output_files = split_file(
    input_file='data_description.md',
    output_dir='./output',  # 可选
    max_size_kb=20,         # 可选，默认20KB
    keep_original=True      # 可选，是否保留原文件
)

# output_files 返回生成的所有分片文件路径列表
```

## 分割策略

### 智能分割规则
1. **代码块保护**：完整的代码块不会被分割
2. **表格保护**：完整的表格结构不会被分割
3. **标题优先**：优先在标题处进行分割
4. **段落完整**：尽量保持段落的完整性

### frontmatter处理
每个分片都会包含完整的frontmatter信息：
- 保留原始文件的所有frontmatter字段
- 添加分片特有字段：
  - `is_split`: true（标记为分割文件）
  - `part_number`: 当前分片序号
  - `total_parts`: 总分片数
  - `parent_file`: 原始文件名

## 输出格式

### 文件命名
- 原文件：`example.md`
- 分片文件：`example_1.md`, `example_2.md`, `example_3.md`...

### 分片示例
第一个分片（example_1.md）：
```markdown
---
source_id: "1"
file_name: "example.docx"
# ... 其他原始frontmatter字段 ...
is_split: true
part_number: 1
total_parts: 3
parent_file: "example.md"
---

# 文档内容第一部分
...
```

## 注意事项
1. 文件编码：使用UTF-8编码读写文件
2. 大小计算：基于UTF-8编码的字节数计算文件大小
3. 特殊情况：如果单个代码块或表格超过限制大小，会单独作为一个分片

## 依赖项
- Python 3.6+
- PyYAML（用于处理YAML frontmatter）

安装依赖：
```bash
pip install pyyaml
```