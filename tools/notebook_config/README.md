# Notebook 环境配置工具

## 功能说明

本工具提供 Windows 环境下 Notebook 的环境配置，包含基础数据分析库导入和 Plotly 中文字体配置，解决中文显示和图表导出问题。

## 文件说明

- `notebook_env_config.md` - Notebook 环境配置代码模板

## 使用方法

### 在 Notebook 中使用

在 Notebook 的第一个 Cell 中复制 `notebook_env_config.md` 中的代码块内容。

### 配置特点

1. **基础库导入**：
   - pandas, numpy（数据处理）
   - plotly（可视化）
   - datetime, warnings, os（工具库）

2. **环境配置**：
   - 关闭警告显示
   - 优化 pandas 显示选项
   - UTF-8 编码支持

3. **Plotly 中文配置**：
   - 优先使用 Windows 系统自带的微软雅黑字体
   - 提供多级字体回退机制
   - 支持各种中文字体（SimHei、SimSun 等）

4. **导出配置**：
   - 默认导出格式为 PNG
   - 使用 MathJax v3 SVG 渲染，确保公式显示一致
   - 避免 Kaleido 相关的兼容性问题

5. **模板设置**：
   - 创建名为 "zh-CN" 的自定义模板
   - 自动设置为默认模板
   - 包含完整的中文字体配置（标题、图例、坐标轴等）

## 错误解决

该配置可以解决以下常见错误：
- `AttributeError: 'NoneType' object has no attribute 'mathjax'`
- 中文字符显示为方框
- 图表导出时中文乱码

## 注意事项

1. 需要在每个 Notebook 的开头执行一次
2. 仅适用于 Windows 环境
3. 需要 Plotly >= 6.1 版本以获得最佳效果