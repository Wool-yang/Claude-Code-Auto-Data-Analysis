#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件分割工具
用于将大型Markdown文件分割成多个较小的文件
"""

import os
import sys
import argparse
import yaml
import re
from pathlib import Path


def extract_frontmatter(content):
    """提取YAML frontmatter和正文内容"""
    if content.startswith('---\n'):
        try:
            end_index = content.index('\n---\n', 4)
            frontmatter_str = content[4:end_index]
            frontmatter = yaml.safe_load(frontmatter_str)
            body = content[end_index + 5:]
            return frontmatter, body
        except (ValueError, yaml.YAMLError):
            return None, content
    return None, content


def split_markdown_content(content, max_size_kb=20):
    """
    智能分割Markdown内容
    保持段落、代码块、表格等结构的完整性
    """
    max_size = max_size_kb * 1024
    
    # 识别Markdown结构元素
    code_block_pattern = r'```[\s\S]*?```'
    table_pattern = r'(\|.*\|[\r\n]+)+((\|[-:\s]*\|[\r\n]+)?(\|.*\|[\r\n]+)*)?'
    heading_pattern = r'^#{1,6}\s+.*$'
    
    # 将内容按行分割
    lines = content.split('\n')
    
    chunks = []
    current_chunk = []
    current_size = 0
    in_code_block = False
    in_table = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        line_size = len(line.encode('utf-8')) + 1  # +1 for newline
        
        # 检测代码块
        if line.strip().startswith('```'):
            if not in_code_block:
                # 开始代码块，收集整个代码块
                code_block = [line]
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('```'):
                    code_block.append(lines[j])
                    j += 1
                if j < len(lines):
                    code_block.append(lines[j])
                
                block_content = '\n'.join(code_block)
                block_size = len(block_content.encode('utf-8'))
                
                # 如果代码块太大，单独作为一个chunk
                if block_size > max_size:
                    if current_chunk:
                        chunks.append('\n'.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                    chunks.append(block_content)
                    i = j + 1
                    continue
                
                # 如果加上代码块会超出限制，先保存当前chunk
                if current_size + block_size > max_size and current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = code_block
                    current_size = block_size
                else:
                    current_chunk.extend(code_block)
                    current_size += block_size
                
                i = j + 1
                continue
        
        # 检测表格
        if '|' in line and i + 1 < len(lines) and '|' in lines[i + 1]:
            table_lines = [line]
            j = i + 1
            while j < len(lines) and '|' in lines[j]:
                table_lines.append(lines[j])
                j += 1
            
            table_content = '\n'.join(table_lines)
            table_size = len(table_content.encode('utf-8'))
            
            # 如果表格太大，单独作为一个chunk
            if table_size > max_size:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                chunks.append(table_content)
                i = j
                continue
            
            # 如果加上表格会超出限制，先保存当前chunk
            if current_size + table_size > max_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = table_lines
                current_size = table_size
            else:
                current_chunk.extend(table_lines)
                current_size += table_size
            
            i = j
            continue
        
        # 检测标题（尝试在标题处分割）
        if re.match(heading_pattern, line):
            # 如果当前chunk接近限制，在标题处分割
            if current_size > max_size * 0.8 and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size
                i += 1
                continue
        
        # 普通行处理
        if current_size + line_size > max_size and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_size = line_size
        else:
            current_chunk.append(line)
            current_size += line_size
        
        i += 1
    
    # 保存最后的chunk
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks


def split_file(input_file, output_dir=None, max_size_kb=20, keep_original=True):
    """
    分割Markdown文件
    
    Args:
        input_file: 输入文件路径
        output_dir: 输出目录，默认为输入文件所在目录
        max_size_kb: 每个分片的最大大小（KB）
        keep_original: 是否保留原文件（默认True）
    
    Returns:
        list: 生成的分片文件路径列表
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_file}")
    
    # 检查文件大小
    file_size_kb = input_path.stat().st_size / 1024
    if file_size_kb <= max_size_kb:
        print(f"文件大小 {file_size_kb:.2f}KB 未超过 {max_size_kb}KB，无需分割")
        return [str(input_path)]
    
    # 读取文件内容
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取frontmatter和正文
    frontmatter, body = extract_frontmatter(content)
    
    # 分割正文内容
    chunks = split_markdown_content(body, max_size_kb)
    
    if len(chunks) <= 1:
        print(f"文件内容无法有效分割，保持原样")
        return [str(input_path)]
    
    # 确定输出目录
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path.parent
    
    # 生成分片文件
    base_name = input_path.stem
    output_files = []
    
    for i, chunk in enumerate(chunks, 1):
        # 构建输出文件名
        output_file = output_path / f"{base_name}_{i}.md"
        
        # 准备完整的frontmatter
        if frontmatter:
            # 复制原始frontmatter
            split_frontmatter = frontmatter.copy()
            # 添加分片特有字段
            split_frontmatter['is_split'] = True
            split_frontmatter['part_number'] = i
            split_frontmatter['total_parts'] = len(chunks)
            split_frontmatter['parent_file'] = input_path.name
        else:
            # 创建基础frontmatter
            split_frontmatter = {
                'is_split': True,
                'part_number': i,
                'total_parts': len(chunks),
                'parent_file': input_path.name
            }
        
        # 构建输出内容
        output_content = f"---\n{yaml.dump(split_frontmatter, allow_unicode=True, sort_keys=False)}---\n\n{chunk}"
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        output_files.append(str(output_file))
        
        # 显示进度
        file_size = len(output_content.encode('utf-8')) / 1024
        print(f"创建分片 {i}/{len(chunks)}: {output_file.name} ({file_size:.2f}KB)")
    
    # 根据参数决定是否删除原文件
    if not keep_original:
        input_path.unlink()
        print(f"已删除原文件: {input_file}")
    
    print(f"\n文件分割完成，共生成 {len(output_files)} 个分片")
    return output_files


def main():
    # 设置输出编码，参照read_structured_data.py的方式，在ArgumentParser之前设置
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
    
    parser = argparse.ArgumentParser(description='分割大型Markdown文件')
    parser.add_argument('input_file', help='输入文件路径')
    parser.add_argument('-o', '--output-dir', help='输出目录（默认为输入文件所在目录）')
    parser.add_argument('-s', '--max-size', type=int, default=20,
                        help='每个分片的最大大小（KB，默认20KB）')
    parser.add_argument('--delete-original', action='store_true',
                        help='分割后删除原文件')
    
    args = parser.parse_args()
    
    try:
        output_files = split_file(
            args.input_file, 
            args.output_dir, 
            args.max_size,
            keep_original=not args.delete_original
        )
        
        print("\n生成的文件:")
        for f in output_files:
            print(f"  - {f}")
            
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()