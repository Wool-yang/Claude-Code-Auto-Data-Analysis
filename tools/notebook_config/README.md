# Notebook 环境配置工具

## 功能说明

本工具提供 Windows 环境下 Notebook 的环境配置，包含基础数据分析库导入、Plotly 中文字体配置和布局优化，解决中文显示、元素重叠和hover交互问题。

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

4. **布局优化**（新增）：
   - **标题居中**：18px大小，x=0.5居中显示
   - **图例外置**：垂直布局，放在图表右侧外部(x=1.02)
   - **X轴倾斜**：标签倾斜45度，避免重叠
   - **智能边距**：左80 右200 上100 下120，避免所有元素重叠

5. **Hover交互优化**（新增）：
   - **纯白背景**：提高可读性
   - **黑色文字**：最大对比度
   - **13px字体**：清晰易读
   - **完整名称**：namelength=-1显示完整图例名

6. **导出配置**：
   - 默认导出格式为 PNG
   - 使用 MathJax v3 SVG 渲染，确保公式显示一致
   - 避免 Kaleido 相关的兼容性问题

7. **模板设置**：
   - 创建名为 "zh-CN" 的自定义模板
   - 自动设置为默认模板
   - 包含完整的中文字体配置（标题、图例、坐标轴等）

## 错误解决

该配置可以解决以下常见错误：
- `AttributeError: 'NoneType' object has no attribute 'mathjax'`
- 中文字符显示为方框
- 图表导出时中文乱码
- 图例与X轴标签重叠
- 标题与图例重叠
- Hover提示文字模糊难读

## 高级用法

### 特殊图表调整
```python
# 增加特定边距
fig.update_layout(
    height=600,
    margin=dict(b=150)  # 底部边距加大
)
```

### 双轴图表配置
```python
from plotly.subplots import make_subplots

fig = make_subplots(specs=[[{"secondary_y": True}]])
# ... 添加数据
fig.update_xaxes(tickangle=-45)
fig.update_layout(margin=dict(l=80, r=200, t=100, b=120))
```

### 饼图特殊处理
```python
# 饼图图例可能需要调整位置
fig.update_layout(
    legend=dict(
        orientation="v",
        yanchor="middle",
        y=0.5,
        xanchor="left",
        x=1.02
    )
)
```

## 注意事项

1. **必须在每个 Notebook 的开头执行一次**
2. 仅适用于 Windows 环境
3. 需要 Plotly >= 5.0 版本以获得最佳效果
4. 配置为通用优化，特殊情况可覆盖默认设置

## 更新历史

- v2.0: 新增布局优化和hover交互改进
- v1.0: 基础中文配置和导出设置