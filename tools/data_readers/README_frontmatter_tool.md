# Frontmatter 处理工具 (frontmatter_tool.py)

## 功能概述
智能处理 Markdown 文件的 YAML frontmatter，支持添加、更新和合并操作，特别设计用于处理大型文件而不占用过多内存。

## 主要特性
- **智能检测**：自动检测文件是否已有 frontmatter
- **流式处理**：采用流式读写，避免一次性加载整个文件
- **多种合并策略**：支持 update、replace、merge_deep 三种合并模式

## 使用场景

### 1. DataSourceFileAnalysisAgent 集成
在数据源分析流程中，避免直接读取可能很大的中间产物文件：
- 不直接读取中间文件内容
- 流式添加 frontmatter 元数据
- 智能处理分片文件的元数据

### 2. 文档元数据管理
为文档添加或更新元数据信息：
- 添加文档分类信息
- 更新文档状态
- 合并来自不同来源的元数据

## 命令详解

### check - 检查 frontmatter
检查文件是否已有 frontmatter 及其内容：

```bash
python frontmatter_tool.py check document.md
```

**输出示例**：
```
发现 frontmatter:
source_id: "1"
title: "测试文档"
tags: ["测试"]
内容开始位置: 45 字节
```

### single - 单文件处理
处理单个文件的 frontmatter：

```bash
# 基本用法
python frontmatter_tool.py single input.md \
  --frontmatter '{"source_id": "1", "title": "新标题"}'

# 输出到新文件
python frontmatter_tool.py single input.md \
  -o output.md \
  --frontmatter '{"description": "文档描述"}' \
  --merge update
```

### DataSourceFileAnalysisAgent 集成示例

在处理非结构化数据时，Agent 使用此工具添加完整的元数据：

```bash
# 为中间产物文件添加完整的 frontmatter 元数据
python frontmatter_tool.py single \
  archives/{current_task_name}/data_source/descriptions/intermediate_artifacts/document_intermediate.md \
  --frontmatter '{"source_id": "1", "file_name": "document.docx", "file_type": "docx", "is_structured": false, "size": 45231, "description": "项目文档", "tags": ["文档", "项目"], "structure": {"row_count": 0, "column_count": 0, "columns": []}, "metadata": {"encoding": "utf-8", "delimiter": null, "has_header": false}, "intermediate_artifacts": {"has_intermediate_file": true, "intermediate_file_path": "intermediate_artifacts/document_intermediate.md", "has_images": false, "images_directory": null, "processing_method": "document_script"}}' \
  -o archives/{current_task_name}/data_source/descriptions/document.md \
  --merge update
```

## 合并策略详解

### update（默认策略）
更新已存在的字段，保留其他字段：

**原有 frontmatter**：
```yaml
---
title: "原标题"
author: "作者"
tags: ["tag1"]
---
```

**新增数据**：
```json
{"title": "新标题", "version": "1.0"}
```

**合并结果**：
```yaml
---
title: "新标题"      # 已更新
author: "作者"        # 保留
tags: ["tag1"]       # 保留
version: "1.0"       # 新增
---
```

### replace
完全替换现有 frontmatter：

**合并结果**：
```yaml
---
title: "新标题"
version: "1.0"
---
```

### merge_deep
深度合并嵌套结构：

**原有 frontmatter**：
```yaml
---
metadata:
  author: "作者"
  created: "2024-01-01"
tags: ["tag1"]
---
```

**新增数据**：
```json
{
  "metadata": {"version": "1.0", "created": "2024-01-02"},
  "description": "描述"
}
```

**合并结果**：
```yaml
---
metadata:
  author: "作者"         # 保留
  created: "2024-01-02"  # 更新
  version: "1.0"         # 新增
tags: ["tag1"]          # 保留
description: "描述"      # 新增
---
```

## 技术细节

### 内存优化
- **流式读取**：只读取文件的 frontmatter 部分，不加载整个文件
- **分块处理**：大文件采用逐行处理，避免内存峰值

### 错误处理
- **文件不存在**：提供明确的错误信息
- **YAML 格式错误**：自动修复或跳过无效的 frontmatter
- **编码问题**：统一使用 UTF-8 编码，支持中文内容

## 最佳实践

### 1. 选择合适的合并策略
- **日常更新**：使用 `update` 策略保留现有信息
- **重新生成**：使用 `replace` 策略完全刷新
- **复杂结构**：使用 `merge_deep` 策略处理嵌套数据

## 依赖项
- **Python 3.6+**
- **PyYAML**: 用于解析和生成 YAML frontmatter

## 安装依赖
```bash
pip install pyyaml>=6.0
```

## 故障排除

### 常见问题

**问题**：`ModuleNotFoundError: No module named 'yaml'`
**解决**：安装 PyYAML：`pip install pyyaml`

**问题**：文件权限错误
**解决**：确保对目标目录有写权限，或使用 `-o` 参数指定有权限的输出目录

**问题**：中文乱码
**解决**：确保文件使用 UTF-8 编码保存