#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jupyter Notebook Runner Script
可以运行整个notebook文件、特定单元格或某个区间的单元格，并可选显示输出。
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


def _print_cell_output(cell, cell_index: int) -> None:
    """内部辅助函数，打印单个单元格的输出"""
    if not hasattr(cell, 'outputs'):
        return
        
    print(f"--- 单元格 {cell_index} 的输出 ---")
    for output in cell.outputs:
        if output.output_type == 'stream':
            print(output.text.strip())
        elif output.output_type == 'execute_result' or output.output_type == 'display_data':
            if 'text/plain' in output.data:
                print(output.data['text/plain'])
            if 'image/png' in output.data:
                print("[图片输出，请在Notebook中查看]")
        elif output.output_type == 'error':
            print(f"错误: {output.ename}")
            print('\\n'.join(output.traceback))
    print(f"--- 输出结束 ---")


def run_entire_notebook(notebook_path: str, kernel_name: str = 'python3', show_output: bool = False) -> None:
    """运行整个notebook"""
    print(f"正在运行整个notebook: {notebook_path}")
    
    notebook = load_notebook(notebook_path)
    ep = ExecutePreprocessor(timeout=600, kernel_name=kernel_name)
    
    try:
        executed_notebook, _ = ep.preprocess(notebook, {'metadata': {'path': os.path.dirname(notebook_path)}})
        
        if show_output:
            print("\\n" + "="*20 + " 运行结果 " + "="*20)
            for i, cell in enumerate(executed_notebook.cells):
                if cell.cell_type == 'code':
                    _print_cell_output(cell, i)
            print("="*52 + "\\n")

        save_notebook(executed_notebook, notebook_path)
        print("notebook执行完成并已保存")
        
    except Exception as e:
        print(f"执行notebook时出错: {str(e)}")
        sys.exit(1)


def run_specific_cells(notebook_path: str, cell_indices: List[int], kernel_name: str = 'python3', show_output: bool = False) -> None:
    """运行特定的单元格"""
    print(f"正在运行notebook: {notebook_path} 中的特定单元格: {cell_indices}")
    
    original_notebook = load_notebook(notebook_path)
    
    for idx in cell_indices:
        if idx < 0 or idx >= len(original_notebook.cells):
            print(f"错误: 单元格索引 {idx} 超出范围 [0, {len(original_notebook.cells)-1}]")
            sys.exit(1)
    
    temp_notebook = nbformat.v4.new_notebook()
    temp_notebook.metadata = original_notebook.metadata
    
    for idx in cell_indices:
        temp_notebook.cells.append(original_notebook.cells[idx])
    
    ep = ExecutePreprocessor(timeout=600, kernel_name=kernel_name)
    
    try:
        executed_temp_notebook, _ = ep.preprocess(temp_notebook, {'metadata': {'path': os.path.dirname(notebook_path)}})
        
        if show_output:
            print("\\n" + "="*20 + " 运行结果 " + "="*20)
            for i, original_idx in enumerate(cell_indices):
                _print_cell_output(executed_temp_notebook.cells[i], original_idx)
            print("="*52 + "\\n")
        
        for i, original_idx in enumerate(cell_indices):
            original_notebook.cells[original_idx] = executed_temp_notebook.cells[i]
        
        save_notebook(original_notebook, notebook_path)
        print(f"指定单元格执行完成并已保存到原notebook")
        
    except Exception as e:
        print(f"执行指定单元格时出错: {str(e)}")
        sys.exit(1)


def run_cell_range(notebook_path: str, start_idx: int, end_idx: int, kernel_name: str = 'python3', show_output: bool = False) -> None:
    """运行指定范围的单元格"""
    print(f"正在运行notebook: {notebook_path} 中索引 {start_idx} 到 {end_idx} 的单元格")
    
    original_notebook = load_notebook(notebook_path)
    
    if start_idx < 0 or end_idx >= len(original_notebook.cells) or start_idx > end_idx:
        print(f"错误: 单元格范围 [{start_idx}, {end_idx}] 无效")
        sys.exit(1)
    
    temp_notebook = nbformat.v4.new_notebook()
    temp_notebook.metadata = original_notebook.metadata
    
    cell_indices_in_range = list(range(start_idx, end_idx + 1))
    for idx in cell_indices_in_range:
        temp_notebook.cells.append(original_notebook.cells[idx])
    
    ep = ExecutePreprocessor(timeout=600, kernel_name=kernel_name)
    
    try:
        executed_temp_notebook, _ = ep.preprocess(temp_notebook, {'metadata': {'path': os.path.dirname(notebook_path)}})
        
        if show_output:
            print("\\n" + "="*20 + " 运行结果 " + "="*20)
            for i, original_idx in enumerate(cell_indices_in_range):
                _print_cell_output(executed_temp_notebook.cells[i], original_idx)
            print("="*52 + "\\n")
            
        for i, original_idx in enumerate(cell_indices_in_range):
            original_notebook.cells[original_idx] = executed_temp_notebook.cells[i]
        
        save_notebook(original_notebook, notebook_path)
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
                source_lines = cell.source.split('\\n')
                preview = source_lines[0][:50] + '...' if len(source_lines[0]) > 50 else source_lines[0]
                if len(source_lines) > 1:
                    preview += ' ...'
                print(f"  [{i}] {cell_type}: {preview}")
            else:
                content_lines = cell.source.strip().split('\\n')
                preview = content_lines[0][:50] + '...' if len(content_lines[0]) > 50 else content_lines[0]
                print(f"  [{i}] {cell_type}: {preview}")
        except Exception as e:
            print(f"  [{i}] {cell_type}: 无法显示预览 (错误: {str(e)})")


def read_cell_output(notebook_path: str, cell_index: int) -> None:
    """读取并显示指定单元格的输出"""
    print(f"正在读取 notebook: {notebook_path} 中索引为 {cell_index} 的单元格输出...")
    
    notebook = load_notebook(notebook_path)

    if cell_index < 0 or cell_index >= len(notebook.cells):
        print(f"错误: 单元格索引 {cell_index} 超出范围 [0, {len(notebook.cells)-1}]")
        sys.exit(1)

    cell = notebook.cells[cell_index]
    if cell.cell_type != 'code':
        print(f"信息: 索引 {cell_index} 的单元格不是代码单元格，没有输出。")
        return

    if not hasattr(cell, 'outputs') or not cell.outputs:
        print(f"信息: 索引 {cell_index} 的代码单元格没有输出。")
        return

    _print_cell_output(cell, cell_index)


def main():
    parser = argparse.ArgumentParser(description='Jupyter Notebook Runner')
    parser.add_argument('notebook_path', help='Notebook文件路径')
    
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument('--all', action='store_true', help='运行整个notebook')
    action_group.add_argument('--cells', type=str, help='运行特定单元格，用逗号分隔索引，如 "1,3,5"')
    action_group.add_argument('--range', type=str, help='运行单元格范围，格式为 "start-end"，如 "2-5"')
    action_group.add_argument('--list', action='store_true', help='列出notebook中的所有单元格')
    action_group.add_argument('--read-cell', type=int, help='读取并显示指定单元格的输出')
    
    parser.add_argument('--show-output', action='store_true', help='运行后在控制台显示输出结果')
    parser.add_argument('--kernel', type=str, default='python3', help='指定kernel名称 (默认: python3)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.notebook_path):
        print(f"错误: 文件 {args.notebook_path} 不存在")
        sys.exit(1)
    
    if not args.notebook_path.endswith('.ipynb'):
        print(f"错误: 文件 {args.notebook_path} 不是有效的notebook文件 (.ipynb)")
        sys.exit(1)
    
    try:
        if args.list:
            list_cells(args.notebook_path)
        elif args.read_cell is not None:
            read_cell_output(args.notebook_path, args.read_cell)
        elif args.all:
            run_entire_notebook(args.notebook_path, args.kernel, args.show_output)
        elif args.cells:
            cell_indices = [int(x.strip()) for x in args.cells.split(',')]
            run_specific_cells(args.notebook_path, cell_indices, args.kernel, args.show_output)
        elif args.range:
            start, end = [int(x.strip()) for x in args.range.split('-')]
            run_cell_range(args.notebook_path, start, end, args.kernel, args.show_output)
        else:
            run_entire_notebook(args.notebook_path, args.kernel, args.show_output)

    except KeyboardInterrupt:
        print("\\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"发生未预期的错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
