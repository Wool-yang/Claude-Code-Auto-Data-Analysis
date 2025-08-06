# Jupyter Notebook Runner 使用说明

## 功能说明

这个脚本可以让你:
1. 运行整个 Jupyter Notebook 文件
2. 运行特定的单元格
3. 运行某个区间的单元格
4. 列出 Notebook 中的所有单元格

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

### 5. 指定 Kernel（可选）

```bash
python nb_runner.py "D:\Program\jupyter\Test\test_notebook.ipynb" --all --kernel "python3"
```

## 参数说明

- `notebook_path`: Notebook 文件路径（必需）
- `--all`: 运行整个 notebook
- `--cells`: 运行特定单元格，用逗号分隔索引
- `--range`: 运行单元格范围，格式为 "start-end"
- `--list`: 列出 notebook 中的所有单元格
- `--kernel`: 指定 kernel 名称（默认为 python3）

## 注意事项

1. 执行结果会直接保存到原 notebook 文件中
2. 单元格索引从 0 开始计数
3. 运行前请确保没有其他程序正在使用该 notebook 文件
4. 如果执行过程中出错，错误信息会显示在控制台中