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

# Plotly 中文配置
# ================================================

# 导出与 MathJax 配置
pio.defaults.default_format = "png"
pio.defaults.mathjax = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"

# 中文字体配置
cn_fonts = (
    "'Microsoft YaHei','Microsoft YaHei UI',"
    "DengXian,SimHei,SimSun,"
    "'Noto Sans CJK SC','Source Han Sans SC','PingFang SC',"
    "'Arial Unicode MS','Segoe UI Emoji','Segoe UI Symbol',sans-serif"
)

pio.templates["zh-CN"] = go.layout.Template(
    layout=dict(
        font=dict(family=cn_fonts, size=16),
        title=dict(font=dict(family=cn_fonts)),
        legend=dict(font=dict(family=cn_fonts)),
        hoverlabel=dict(font=dict(family=cn_fonts)),
        # 坐标轴字体
        xaxis=dict(
            title=dict(font=dict(family=cn_fonts)),
            tickfont=dict(family=cn_fonts)
        ),
        yaxis=dict(
            title=dict(font=dict(family=cn_fonts)),
            tickfont=dict(family=cn_fonts)
        ),
        # 颜色主题
        colorway=['#4285F4', '#1877F2', '#FF0050', '#00C851', '#FF6900', '#6F42C1', '#E91E63', '#795548']
    )
)

# 设置为默认模板
pio.templates.default = "zh-CN"

print("✅ Notebook 环境配置已加载")
print("   - 数据处理: pandas, numpy")
print("   - 可视化: plotly (zh-CN模板)")
print("   - 中文字体: 微软雅黑优先，多级回退")
```

## 配置说明

### 基础库导入
- `pandas, numpy` - 数据处理核心库
- `plotly` - 交互式可视化库
- `datetime, warnings, os` - 工具库

### 环境配置
- 关闭警告信息显示，保持输出简洁
- 优化pandas显示选项，便于数据查看

### Plotly中文配置
- 解决中文字体显示问题
- 配置图表导出格式为PNG
- 使用MathJax v3渲染数学公式
- 创建zh-CN模板并设为默认

### 字体回退机制
按优先级依次尝试：
1. 微软雅黑 (Windows默认)
2. 其他中文字体 (SimHei, SimSun等)
3. 开源中文字体
4. Unicode字体
5. 系统默认sans-serif

这个配置可以解决常见的中文显示和Plotly错误问题。