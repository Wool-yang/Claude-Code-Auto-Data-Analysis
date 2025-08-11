# 数据读取工具说明文档

## 概述

本目录包含三个核心脚本，用于支持 `DataSourceFileAnalysisAgent` 进行数据源分析：

1. **file_classifier.py** - 文件类型分类器
2. **read_structured_data.py** - 结构化数据处理脚本  
3. **document_parser.py** - 非结构化数据处理脚本

## 工作流程

```
原始文件 → file_classifier.py → 判定文件类型 → 选择对应脚本处理 → DataSourceFileAnalysisAgent 融合结果
```

---

## 1. file_classifier.py

### 功能
智能分类文件为结构化或非结构化数据，为 DataSourceFileAnalysisAgent 提供处理路径建议。

### 分类规则

**结构化数据**（使用 read_structured_data.py）：
- `.csv`, `.tsv` 文件
- `.xlsx`, `.xls` 文件且**不包含图片**
- `.txt` 文件且包含分隔符特征

**非结构化数据**（使用 document_parser.py）：
- `.md`, `.doc`, `.docx`, `.pdf` 文件
- `.xlsx`, `.xls` 文件但**包含图片或复杂格式**
- `.txt` 文件且为纯文本内容
- 未知文件类型

### 使用方法

```bash
# 基本使用
python file_classifier.py /path/to/file.xlsx

# 输出到文件
python file_classifier.py /path/to/file.xlsx --output classification_result.json
```

### 输出格式

```json
{
  "file_path": "/path/to/file.xlsx",
  "file_name": "file.xlsx", 
  "extension": ".xlsx",
  "classification": "unstructured",
  "reason": "Excel文件包含图片，判定为非结构化数据",
  "recommended_script": "document_parser.py",
  "has_images": true
}
```

### 关键特性

- **图片检测**：自动检查 Excel 和 Word 文件中的图片
- **TXT智能判断**：区分分隔符数据文件和纯文本文件
- **容错处理**：文件读取失败时提供默认分类

---

## 2. read_structured_data.py

### 功能
专门处理结构化数据文件（CSV、Excel等），提供强大的编码检测、数据类型推断和采样功能。

### 核心特性

#### 编码检测
- **多重检测**：BOM检测、chardet、charset_normalizer
- **智能评分**：基于可打印字符比例、CJK字符、置信度的综合评分
- **容错处理**：支持损坏编码的修复和回退

#### CSV解析
- **分隔符检测**：自动识别 `,`, `\t`, `;`, `|` 等分隔符
- **列名修复**：修复乱码列名，处理BOM、编码问题
- **头部处理**：智能判断是否包含表头

#### 数据抽样策略

**均匀抽样（默认）**：
- 在全数据范围内均匀分布选择样本点
- 例如100行数据抽取10行：选择第0、11、22、33、44、56、67、78、89、99行
- 更好地代表数据整体分布特征
- 适用于数据可能存在时间序列或分区特征的场景

**头部抽样（--head_sampling）**：
- 提取数据的前N行作为样本
- 适用于数据分布相对均匀的场景
- 执行速度快，内存占用小

#### 数据类型推断
- **integer**：整数类型
- **numeric**：浮点数类型  
- **boolean**：布尔类型
- **datetime**：日期时间类型（自动检测）
- **categorical**：分类变量（基于唯一值比例）
- **text**：文本类型

### 使用方法

```bash
# 生成中间分析结果（推荐用于DataSourceFileAnalysisAgent）
python read_structured_data.py --files data.csv --intermediate --sample_rows 20

# 使用头部抽样策略
python read_structured_data.py --files data.csv --intermediate --sample_rows 20 --head_sampling

# 生成CLAUDE.md标准schema（向后兼容）
python read_structured_data.py --files data.csv --emit_schema

# 基础信息输出
python read_structured_data.py --files data.csv --sample_rows 10
```

### 输出格式

#### 中间分析结果（--intermediate）

```json
{
  "analysis_type": "structured_data",
  "file_info": {
    "file_name": "data.csv",
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
      }
    ],
    "raw_columns": ["用户ID", "姓名", "年龄"],
    "clean_columns": ["用户ID", "姓名", "年龄"]
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
    "sampling_method": "uniform"  # "head" 或 "uniform"
  }
}
```

### 参数说明

- `--files`: 要处理的文件路径（支持多文件）
- `--sample_rows`: 采样行数（默认10）
- `--head_sampling`: 使用头部抽样而不是均匀抽样（默认为均匀抽样）
- `--head_rows`: 限制读取的最大行数
- `--intermediate`: 输出中间分析结果
- `--emit_schema`: 输出CLAUDE.md标准schema格式
- `--temp_output`: 保存结果到指定文件

---

## 3. document_parser.py

### 功能
处理非结构化文档和包含复杂内容的文件，支持全文提取、图片提取、格式保留。

### 支持的文件类型

- **Markdown**：`.md`, `.markdown`
- **Word文档**：`.docx`, `.doc`
- **文本文件**：`.txt`（非结构化）
- **Excel**：`.xlsx`, `.xls`（包含图片的复杂表格）
- **CSV**：`.csv`（作为备选处理方案）

### 核心功能

#### 图片提取
- **Excel图片**：提取并按sheet和位置组织
- **Word图片**：提取media文件夹中的图片
- **Markdown图片**：复制引用的图片到中间产物目录

#### 内容提取  
- **全文提取**：保留文档的完整内容结构
- **表格转换**：将Excel表格转换为Markdown格式
- **位置信息**：记录图片在Excel中的行列位置

#### 中间产物生成
- **Markdown文件**：`{filename}_intermediate.md`
- **图片目录**：`{filename}_images/`
- **相对路径**：确保图片引用正确

### 使用方法

```bash
# 处理单个文件
python document_parser.py /path/to/document.docx

# 批量处理
python document_parser.py /path/to/file1.xlsx /path/to/file2.md
```

### 输出结构

```
archives/{task_name}/data_source/descriptions/intermediate_artifacts/
├── document_intermediate.md     # 主要内容
├── document_images/            # 提取的图片
│   ├── image1.png
│   ├── image2.jpg
│   └── ...
└── ...
```

### 输出示例

#### Markdown中间产物
```markdown  
# document.xlsx

**File Type:** xlsx
**File Size:** 3121353 bytes  
**Modified:** 2025-07-24T20:36:51.177986
**Images Extracted:** 13
**Structured Data:** No

---

## Sheet: 数据表

| 列A | 列B | 列C |
| --- | --- | --- |
| 数据1 | 数据2 | ![image1.png](document_images/image1.png) |
| 数据3 | 数据4 | 数据5 |

## Image Summary

Total images extracted: 13

### 数据表
- **image1.png** at Row 1 Col 2 (783640 bytes)
- **image2.png** at Row 3 Col 1 (147653 bytes)
```

### 特殊处理

#### Excel文件
- **Sheet映射**：准确映射图片到对应工作表
- **位置定位**：记录图片的精确行列坐标  
- **路径处理**：处理复杂的OpenXML关系路径

#### Word文档
- **全文提取**：保留段落结构和换行
- **图片引用**：在文档末尾添加图片列表

#### Markdown文件
- **引用更新**：更新图片引用路径到中间产物目录
- **格式保留**：完整保留原始markdown格式

---

## DataSourceFileAnalysisAgent 集成

### 处理流程

1. **文件分类**：
   ```python
   result = subprocess.run(['python', 'file_classifier.py', file_path], 
                          capture_output=True, text=True)
   classification = json.loads(result.stdout)
   ```

2. **结构化数据处理**：
   ```python
   if classification['classification'] == 'structured':
       result = subprocess.run(['python', 'read_structured_data.py', 
                              '--files', file_path, '--intermediate'], 
                              capture_output=True, text=True)
       analysis_data = json.loads(result.stdout)
   ```

3. **非结构化数据处理**：
   ```python
   elif classification['classification'] == 'unstructured':
       subprocess.run(['python', 'document_parser.py', file_path])
       # 读取生成的中间产物markdown文件
   ```

4. **结果融合**：
   - 结合脚本输出结果
   - 读取 task_background.md 生成 description 和 tags
   - 分配 source_id
   - 格式化为 CLAUDE.md 标准 schema

### 错误处理

- **分类失败**：默认使用 document_parser.py
- **脚本执行失败**：记录错误，跳过该文件
- **编码问题**：使用UTF-8输出，错误时使用replace模式

### 性能优化

- **并发处理**：可并行处理多个文件
- **内存控制**：限制采样行数和文件大小
- **缓存机制**：避免重复处理相同文件

---

## 注意事项

1. **编码处理**：所有脚本都设置为UTF-8输出，避免Windows环境下的编码问题
2. **路径处理**：使用 `os.path.normpath()` 确保Windows路径兼容性  
3. **错误容错**：脚本执行失败时不会中断整个流程
4. **图片判定**：有图片的文件会被强制分类为非结构化数据
5. **中间产物**：所有中间文件都保存在 `intermediate_artifacts` 目录下