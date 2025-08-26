# Notebook 环境配置代码模板

以下代码应当放在每个Notebook的**第一个Cell**中，用于初始化分析环境：

```python
# Notebook 环境配置（Windows环境，第一个单元格）
# ================================================

# 基础库导入
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from datetime import datetime, timedelta
import warnings
import os

# 环境配置
warnings.filterwarnings('ignore')
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

# Plotly 中文配置与优化布局
# ================================================

# 导出与 MathJax 配置
pio.renderers.default = "notebook_connected+plotly_mimetype+png"
pio.defaults.default_scale = 2
pio.defaults.mathjax = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"

# 中文字体配置
fonts = ["Microsoft YaHei","Microsoft YaHei UI","DengXian","SimHei","SimSun","Noto Sans CJK SC","Source Han Sans SC","PingFang SC","Arial Unicode MS","Segoe UI Emoji","Segoe UI Symbol","sans-serif"]
cn_fonts = ",".join(f"'{f}'" if " " in f and f != "sans-serif" else f for f in fonts)

# 创建优化的中文模板
pio.templates["zh-CN"] = go.layout.Template(
    layout=dict(
        # 基础字体
        font=dict(family=cn_fonts, size=14),
        # 标题配置
        title=dict(
            font=dict(family=cn_fonts, size=18),
            x=0.5,  # 居中
            xanchor='center'
        ),
        # Hover优化 - 清晰易读
        hoverlabel=dict(
            bgcolor="white",  # 纯白背景
            bordercolor="rgba(0,0,0,0.5)",  # 半透明边框
            font=dict(size=13, color="black", family=cn_fonts),  # 黑色文字
            align="left",
            namelength=-1  # 显示完整名称
        ),
        # 图例配置 - 避免重叠
        legend=dict(
            font=dict(family=cn_fonts, size=12),
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1,
            orientation="v",  # 垂直布局
            yanchor="top",
            y=0.95,
            xanchor="left",
            x=1.02  # 放在图表右侧外部
        ),
        # X轴配置
        xaxis=dict(
            title=dict(font=dict(family=cn_fonts, size=14)),
            tickfont=dict(family=cn_fonts, size=11),
            tickangle=-45  # 倾斜标签节省空间
        ),
        # Y轴配置
        yaxis=dict(
            title=dict(font=dict(family=cn_fonts, size=14)),
            tickfont=dict(family=cn_fonts, size=11)
        ),
        # 颜色主题 - 区分度高的配色
        colorway=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
        # 布局边距 - 避免元素重叠
        margin=dict(l=80, r=200, t=100, b=120)  # 左80 右200 上100 下120
    )
)

# 设置为默认模板
pio.templates.default = "zh-CN"

print("✅ Notebook 环境配置已加载")
print("   - 数据处理: pandas, numpy")
print("   - 可视化: plotly (zh-CN模板)")
print("   - 中文字体: 微软雅黑优先，多级回退")
print("   - 布局优化: 图例右侧，避免重叠")
print("   - Hover样式: 白底黑字，清晰易读")
```

## 配置说明

### 基础库导入
- `pandas, numpy` - 数据处理核心库
- `plotly` - 交互式可视化库
- `datetime, warnings, os` - 工具库

### 环境配置
- 关闭警告信息显示，保持输出简洁
- 优化pandas显示选项，便于数据查看

### Plotly可视化优化配置

#### 1. 中文字体配置
- 解决中文字体显示问题
- 多级字体回退机制，确保跨平台兼容
- 配置图表导出格式为PNG
- 使用MathJax v3渲染数学公式

#### 2. 布局优化
- **标题**：18px大小，居中显示
- **图例**：垂直布局，放置在图表右侧外部(x=1.02)，避免与内容重叠
- **X轴标签**：倾斜45度，节省空间避免重叠
- **边距设置**：
  - 左边距: 80px (轴标题和刻度)
  - 右边距: 200px (给图例留充足空间)
  - 上边距: 100px (标题空间)
  - 下边距: 120px (倾斜的X轴标签)

#### 3. Hover交互优化
- **背景色**：纯白色，提高可读性
- **文字颜色**：黑色，最大对比度
- **字体大小**：13px，清晰易读
- **边框**：半透明黑色边框
- **名称显示**：`namelength=-1`显示完整名称

#### 4. 颜色主题
使用区分度高的10色配色方案，适合多系列数据展示

### 字体回退机制
按优先级依次尝试：
1. 微软雅黑 (Windows默认)
2. 其他中文字体 (SimHei, SimSun等)
3. 开源中文字体 (Noto Sans CJK, Source Han Sans)
4. Unicode字体
5. 系统默认sans-serif

### 使用建议

1. **每个Notebook第一个Cell必须运行此配置**
2. **特殊图表可覆盖默认配置**：
   ```python
   fig.update_layout(
       height=600,  # 调整高度
       margin=dict(b=150)  # 增加特定边距
   )
   ```
3. **双轴图表需要额外设置**：
   ```python
   fig.update_xaxes(tickangle=-45)  # 设置X轴倾斜
   fig.update_layout(margin=dict(l=80, r=200, t=100, b=120))
   ```

这个配置解决了常见的中文显示、元素重叠和hover交互问题，提供了一个稳定可靠的可视化基础。