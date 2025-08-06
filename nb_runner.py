#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jupyter Notebook Runner Script
可以运行整个notebook文件、特定单元格或某个区间的单元格
"""

import sys
import io
import json
import os
import argparse
from typing import List, Optional
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_notebook(notebook_path: str) -> nbformat.NotebookNode:
    """加载notebook文件"""
    with open(notebook_path, 'r', encoding='utf-8') as f:
        return nbformat.read(f, as_version=4)


def save_notebook(notebook: nbformat.NotebookNode, notebook_path: str) -> None:
    """保存notebook文件"""
    with open(notebook_path, 'w', encoding='utf-8') as f:
        nbformat.write(notebook, f)


def run_entire_notebook(notebook_path: str, kernel_name: str = 'python3') -> None:
    """运行整个notebook"""
    print(f"正在运行整个notebook: {notebook_path}")
    
    notebook = load_notebook(notebook_path)
    ep = ExecutePreprocessor(timeout=600, kernel_name=kernel_name)
    
    try:
        # 执行notebook
        ep.preprocess(notebook, {'metadata': {'path': os.path.dirname(notebook_path)}})
        
        # 保存执行结果
        save_notebook(notebook, notebook_path)
        print("notebook执行完成并已保存")
        
    except Exception as e:
        print(f"执行notebook时出错: {str(e)}")
        sys.exit(1)


def run_specific_cells(notebook_path: str, cell_indices: List[int], kernel_name: str = 'python3') -> None:
    """运行特定的单元格"""
    print(f"正在运行notebook: {notebook_path} 中的特定单元格: {cell_indices}")
    
    notebook = load_notebook(notebook_path)
    
    # 验证索引有效性
    for idx in cell_indices:
        if idx < 0 or idx >= len(notebook.cells):
            print(f"错误: 单元格索引 {idx} 超出范围 [0, {len(notebook.cells)-1}]")
            sys.exit(1)
    
    # 创建只包含指定单元格的新notebook
    new_notebook = nbformat.v4.new_notebook()
    new_notebook.metadata = notebook.metadata
    
    for idx in cell_indices:
        new_notebook.cells.append(notebook.cells[idx])
    
    ep = ExecutePreprocessor(timeout=600, kernel_name=kernel_name)
    
    try:
        # 执行选定的单元格
        ep.preprocess(new_notebook, {'metadata': {'path': os.path.dirname(notebook_path)}})
        
        # 将执行结果写回原notebook
        for i, idx in enumerate(cell_indices):
            notebook.cells[idx] = new_notebook.cells[i]
        
        # 保存执行结果
        save_notebook(notebook, notebook_path)
        print(f"指定单元格执行完成并已保存到原notebook")
        
    except Exception as e:
        print(f"执行指定单元格时出错: {str(e)}")
        sys.exit(1)


def run_cell_range(notebook_path: str, start_idx: int, end_idx: int, kernel_name: str = 'python3') -> None:
    """运行指定范围的单元格"""
    print(f"正在运行notebook: {notebook_path} 中索引 {start_idx} 到 {end_idx} 的单元格")
    
    notebook = load_notebook(notebook_path)
    
    # 验证索引有效性
    if start_idx < 0 or end_idx >= len(notebook.cells) or start_idx > end_idx:
        print(f"错误: 单元格范围 [{start_idx}, {end_idx}] 无效")
        sys.exit(1)
    
    # 创建只包含指定范围内单元格的新notebook
    new_notebook = nbformat.v4.new_notebook()
    new_notebook.metadata = notebook.metadata
    
    for idx in range(start_idx, end_idx + 1):
        new_notebook.cells.append(notebook.cells[idx])
    
    ep = ExecutePreprocessor(timeout=600, kernel_name=kernel_name)
    
    try:
        # 执行指定范围的单元格
        ep.preprocess(new_notebook, {'metadata': {'path': os.path.dirname(notebook_path)}})
        
        # 将执行结果写回原notebook
        for i, idx in enumerate(range(start_idx, end_idx + 1)):
            notebook.cells[idx] = new_notebook.cells[i]
        
        # 保存执行结果
        save_notebook(notebook, notebook_path)
        print(f"单元格范围 [{start_idx}, {end_idx}] 执行完成并已保存到原notebook")
        
    except Exception as e:
        print(f"执行单元格范围时出错: {str(e)}")
        sys.exit(1)


def list_cells(notebook_path: str) -> None:
    """列出notebook中的所有单元格"""
    print(f"notebook: {notebook_path} 中的单元格:")
    
    notebook = load_notebook(notebook_path)
    
    for i, cell in enumerate(notebook.cells):
        cell_type = cell.cell_type
        try:
            if cell_type == 'code':
                # 获取代码的前几行作为预览
                source_lines = cell.source.split('\n')
                preview = source_lines[0][:50] + '...' if len(source_lines[0]) > 50 else source_lines[0]
                if len(source_lines) > 1:
                    preview += ' ...'
                print(f"  [{i}] {cell_type}: {preview}")
            else:
                # 对于markdown等其他类型单元格，显示前几行内容
                content_lines = cell.source.strip().split('\n')
                preview = content_lines[0][:50] + '...' if len(content_lines[0]) > 50 else content_lines[0]
                print(f"  [{i}] {cell_type}: {preview}")
        except Exception as e:
            print(f"  [{i}] {cell_type}: 无法显示预览 (错误: {str(e)})")


def main():
    parser = argparse.ArgumentParser(description='Jupyter Notebook Runner')
    parser.add_argument('notebook_path', help='Notebook文件路径')
    parser.add_argument('--all', action='store_true', help='运行整个notebook')
    parser.add_argument('--cells', type=str, help='运行特定单元格，用逗号分隔索引，如 "1,3,5"')
    parser.add_argument('--range', type=str, help='运行单元格范围，格式为 "start-end"，如 "2-5"')
    parser.add_argument('--list', action='store_true', help='列出notebook中的所有单元格')
    parser.add_argument('--kernel', type=str, default='python3', help='指定kernel名称 (默认: python3)')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.notebook_path):
        print(f"错误: 文件 {args.notebook_path} 不存在")
        sys.exit(1)
    
    # 检查文件扩展名
    if not args.notebook_path.endswith('.ipynb'):
        print(f"错误: 文件 {args.notebook_path} 不是有效的notebook文件 (.ipynb)")
        sys.exit(1)
    
    try:
        if args.list:
            list_cells(args.notebook_path)
        elif args.all:
            run_entire_notebook(args.notebook_path, args.kernel)
        elif args.cells:
            cell_indices = [int(x.strip()) for x in args.cells.split(',')]
            run_specific_cells(args.notebook_path, cell_indices, args.kernel)
        elif args.range:
            start, end = [int(x.strip()) for x in args.range.split('-')]
            run_cell_range(args.notebook_path, start, end, args.kernel)
        else:
            # 默认运行整个notebook
            run_entire_notebook(args.notebook_path, args.kernel)
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"发生未预期的错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()