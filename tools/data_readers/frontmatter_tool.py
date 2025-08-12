#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Frontmatter 添加工具
用于给 Markdown 文件添加或更新 YAML frontmatter，智能处理已存在的 frontmatter
特别适合处理大型文件，采用流式处理避免一次性读取整个文件
"""

import os
import sys
import argparse
import yaml
import json
from pathlib import Path
from datetime import datetime
import tempfile


def extract_existing_frontmatter(file_path):
    """
    提取文件中已存在的 frontmatter（如果有）
    只读取文件开头部分，不读取整个文件
    
    Returns:
        tuple: (frontmatter_dict, content_start_position)
    """
    frontmatter = None
    content_start = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        
        # 检查是否以 --- 开头（YAML frontmatter 标记）
        if first_line.strip() == '---':
            yaml_lines = []
            current_pos = f.tell()
            
            # 读取直到找到结束标记 ---
            while True:
                line = f.readline()
                if not line:
                    # 文件结束，没有找到结束标记
                    return None, 0
                
                if line.strip() == '---':
                    # 找到结束标记
                    content_start = f.tell()
                    try:
                        frontmatter = yaml.safe_load('\n'.join(yaml_lines))
                        if not isinstance(frontmatter, dict):
                            frontmatter = {}
                    except yaml.YAMLError:
                        frontmatter = {}
                    break
                
                yaml_lines.append(line.rstrip('\n'))
                current_pos = f.tell()
                
                # 防止读取过多内容（限制在前1000行）
                if len(yaml_lines) > 1000:
                    return None, 0
    
    return frontmatter, content_start


def merge_frontmatter(existing, new, merge_strategy='update'):
    """
    合并已存在的和新的 frontmatter
    
    Args:
        existing: 已存在的 frontmatter 字典
        new: 新的 frontmatter 字典
        merge_strategy: 合并策略
            - 'update': 更新已存在的字段（默认）
            - 'replace': 完全替换
            - 'merge_deep': 深度合并
    
    Returns:
        dict: 合并后的 frontmatter
    """
    if merge_strategy == 'replace':
        return new
    
    if existing is None:
        return new
    
    if merge_strategy == 'update':
        # 浅合并：新值覆盖旧值
        result = existing.copy()
        result.update(new)
        return result
    
    elif merge_strategy == 'merge_deep':
        # 深度合并：递归合并嵌套字典
        def deep_merge(d1, d2):
            result = d1.copy()
            for key, value in d2.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(existing, new)
    
    return new


def add_frontmatter_to_file(input_file, frontmatter_data, output_file=None, merge_strategy='update'):
    """
    给文件添加或更新 frontmatter，智能处理已存在的 frontmatter
    
    Args:
        input_file: 输入文件路径
        frontmatter_data: frontmatter 数据（字典）
        output_file: 输出文件路径（如果为 None，则覆盖原文件）
        merge_strategy: 合并策略（'update', 'replace', 'merge_deep'）
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_file}")
    
    # 检查文件是否已有 frontmatter
    existing_frontmatter, content_start = extract_existing_frontmatter(input_path)
    
    # 合并 frontmatter
    if existing_frontmatter is not None:
        final_frontmatter = merge_frontmatter(existing_frontmatter, frontmatter_data, merge_strategy)
    else:
        final_frontmatter = frontmatter_data
    
    # 准备新的 frontmatter 内容
    frontmatter_yaml = yaml.dump(final_frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False)
    frontmatter_content = f"---\n{frontmatter_yaml}---\n\n"
    
    # 确定输出路径
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path
    
    # 写入新文件
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, 
                                    dir=output_path.parent, suffix='.tmp') as tmp_file:
        # 写入新的 frontmatter
        tmp_file.write(frontmatter_content)
        
        # 复制原文件内容（跳过已存在的 frontmatter）
        with open(input_path, 'r', encoding='utf-8') as infile:
            if content_start > 0:
                # 跳过原有的 frontmatter
                infile.seek(content_start)
                # 跳过 frontmatter 后的空行
                first_content_line = infile.readline()
                if first_content_line and first_content_line.strip() != '':
                    tmp_file.write(first_content_line)
            
            # 流式复制剩余内容
            for line in infile:
                tmp_file.write(line)
        
        tmp_name = tmp_file.name
    
    # 替换目标文件
    Path(tmp_name).replace(output_path)
    
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description='给 Markdown 文件添加或更新 YAML frontmatter')
    
    # 设置输出编码，参照read_structured_data.py的方式
    import io
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 单文件处理命令
    single_parser = subparsers.add_parser('single', help='处理单个文件')
    single_parser.add_argument('input_file', help='输入文件路径')
    single_parser.add_argument('-o', '--output', help='输出文件路径（默认覆盖原文件）')
    single_parser.add_argument('--frontmatter', required=True, help='Frontmatter JSON 字符串')
    single_parser.add_argument('--merge', choices=['update', 'replace', 'merge_deep'], 
                              default='update', help='合并策略（默认: update）')
    
    # 检查 frontmatter 命令
    check_parser = subparsers.add_parser('check', help='检查文件的 frontmatter')
    check_parser.add_argument('input_file', help='要检查的文件路径')
    
    args = parser.parse_args()
    
    if args.command == 'single':
        try:
            frontmatter_data = json.loads(args.frontmatter)
            output_path = add_frontmatter_to_file(args.input_file, frontmatter_data, 
                                                 args.output, args.merge)
            print(f"成功添加/更新 frontmatter: {output_path}")
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'check':
        try:
            frontmatter, content_start = extract_existing_frontmatter(args.input_file)
            if frontmatter is not None:
                print("发现 frontmatter:")
                print(yaml.dump(frontmatter, allow_unicode=True, sort_keys=False))
                print(f"内容开始位置: {content_start} 字节")
            else:
                print("文件没有 frontmatter")
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()