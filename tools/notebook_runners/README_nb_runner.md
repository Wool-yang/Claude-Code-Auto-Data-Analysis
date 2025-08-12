# Jupyter Notebook Runner 使用说明

## 功能说明

这个脚本可以让你:
1. 运行整个 Jupyter Notebook 文件
2. 运行特定的单元格
3. 运行某个区间的单元格
4. 列出 Notebook 中的所有单元格
5. 读取并显示指定单元格的输出
6. 运行后在控制台显示输出结果

## 安装依赖

在使用此脚本之前，请确保安装了必要的依赖包：

```bash
pip install nbformat nbconvert jupyter
```

## 使用方法

### 1. 运行整个 Notebook

```bash
python nb_runner.py "D:\Program\jupyter\Test\test_notebook.ipynb" --all
```

### 2. 运行特定单元格

```bash
python nb_runner.py "D:\Program\jupyter\Test\test_notebook.ipynb" --cells "0,2,4"
```

### 3. 运行单元格范围

```bash
python nb_runner.py "D:\Program\jupyter\Test\test_notebook.ipynb" --range "1-3"
```

### 4. 列出所有单元格

```bash
python nb_runner.py "D:\Program\jupyter\Test\test_notebook.ipynb" --list
```

### 5. 读取指定单元格输出

```bash
python nb_runner.py "D:\Program\jupyter\Test\test_notebook.ipynb" --read-cell "2"
```

### 6. 运行并显示输出结果

```bash
python nb_runner.py "D:\Program\jupyter\Test\test_notebook.ipynb" --all --show-output
```

### 7. 指定 Kernel（可选）

```bash
python nb_runner.py "D:\Program\jupyter\Test\test_notebook.ipynb" --all --kernel "python3"
```

## 参数说明

- `notebook_path`: Notebook 文件路径（必需）
- `--all`: 运行整个 notebook
- `--cells`: 运行特定单元格，用逗号分隔索引，如 "1,3,5"
- `--range`: 运行单元格范围，格式为 "start-end"，如 "2-5"
- `--list`: 列出 notebook 中的所有单元格
- `--read-cell`: 读取并显示指定单元格的输出
- `--show-output`: 运行后在控制台显示输出结果
- `--kernel`: 指定 kernel 名称（默认为 python3）

## Agent 使用规范

### Multi-Agent 系统中的角色

在 Claude Code Auto Analysis 项目中，`nb_runner.py` 是 **AnalysisExecutionAgent** 的核心工具，用于：

1. **逐步执行验证**：每生成一个 Cell 后立即执行并验证结果
2. **程序化运行**：确保 Notebook 执行的一致性和稳定性
3. **错误检测**：及时发现执行过程中的问题
4. **结果验证**：验证每个分析步骤是否产生预期输出

### Agent 执行流程

1. **生成 Notebook**：基于分析规划文件创建 .ipynb 文件
2. **逐 Cell 执行**：使用 `--cells` 参数逐个执行单元格
   ```bash
   python nb_runner.py notebook.ipynb --cells "0" --show-output
   python nb_runner.py notebook.ipynb --cells "1" --show-output
   ```
3. **验证输出**：检查每个 Cell 的执行结果是否符合预期
4. **错误处理**：如果执行失败，基于错误类型自动调整代码并重试
5. **完整性检查**：最后使用 `--all` 参数完整运行一遍验证

### 权限配置

在 `.claude/settings.local.json` 中已配置自动批准权限：
```json
"Bash(python tools/notebook_runners/nb_runner.py:*)"
```

这意味着所有 `nb_runner.py` 的操作都会自动执行，无需用户手动批准。

## 使用场景示例

### 场景1：验证单个 Cell 执行
```bash
python tools/notebook_runners/nb_runner.py "D:\Program\jupyter\项目名\任务名\分析文件.ipynb" --cells "0" --show-output
```

### 场景2：批量执行多个关键 Cell
```bash
python tools/notebook_runners/nb_runner.py "D:\Program\jupyter\项目名\任务名\分析文件.ipynb" --cells "0,1,2" --show-output
```

### 场景3：执行整个分析流程
```bash
python tools/notebook_runners/nb_runner.py "D:\Program\jupyter\项目名\任务名\分析文件.ipynb" --all --show-output
```

### 场景4：检查分析结果
```bash
python tools/notebook_runners/nb_runner.py "D:\Program\jupyter\项目名\任务名\分析文件.ipynb" --read-cell "5"
```

## 注意事项

1. **执行结果保存**：执行结果会直接保存到原 notebook 文件中
2. **索引规则**：单元格索引从 0 开始计数
3. **文件锁定**：运行前请确保没有其他程序正在使用该 notebook 文件
4. **错误处理**：如果执行过程中出错，错误信息会显示在控制台中
5. **环境依赖**：确保运行环境中安装了 notebook 中使用的所有 Python 包
6. **路径规范**：Windows 环境下使用双反斜杠或单正斜杠表示路径
7. **编码支持**：支持包含中文字符的文件路径和文件内容

## 故障排除

### 常见错误及解决方案

1. **Kernel 连接失败**
   ```
   解决方案：检查 Jupyter 环境是否正确安装，尝试指定 --kernel 参数
   ```

2. **模块导入错误**
   ```
   解决方案：确保当前环境已安装 notebook 中使用的所有依赖包
   ```

3. **文件路径错误**
   ```
   解决方案：检查文件路径是否正确，注意 Windows 路径格式
   ```

4. **权限问题**
   ```
   解决方案：确保对 notebook 文件和目标目录有读写权限
   ```