#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper Utilities
通用辅助函数
"""

import re
from typing import List, Dict, Any, Optional
from pathlib import Path


def parse_cell_range(range_str: str) -> List[str]:
    """
    解析cell范围字符串，支持数字索引和cell_id
    
    Args:
        range_str: 范围字符串，如 "1,2,3" 或 "1-5" 或 "1,3-5,7" 或 "abc123,def456"
    
    Returns:
        cell标识符列表（可能是数字字符串或cell_id）
    
    Examples:
        parse_cell_range("1,2,3") -> ["1", "2", "3"]
        parse_cell_range("1-5") -> ["1", "2", "3", "4", "5"]
        parse_cell_range("1,abc123,7") -> ["1", "abc123", "7"]
        parse_cell_range("abc123,def456") -> ["abc123", "def456"]
    """
    identifiers = []
    
    try:
        # 按逗号分割
        parts = range_str.split(',')
        
        for part in parts:
            part = part.strip()
            
            if '-' in part:
                # 检查是否为有效的数字范围格式：start-end（只包含一个连字符，且两端都是数字）
                dash_count = part.count('-')
                if dash_count == 1:
                    try:
                        start_str, end_str = part.split('-', 1)
                        start_str = start_str.strip()
                        end_str = end_str.strip()
                        
                        # 检查两端都是数字
                        if start_str.isdigit() and end_str.isdigit():
                            # 数字范围格式：start-end
                            start_idx = int(start_str)
                            end_idx = int(end_str)
                            
                            # 确保start <= end
                            if start_idx <= end_idx:
                                identifiers.extend(str(i) for i in range(start_idx, end_idx + 1))
                            else:
                                identifiers.extend(str(i) for i in range(end_idx, start_idx + 1))
                        else:
                            # 包含非数字字符，当作单个标识符处理
                            identifiers.append(part)
                    except ValueError:
                        # 解析失败，当作单个标识符处理
                        identifiers.append(part)
                else:
                    # 多个连字符或其他情况，当作单个标识符处理
                    identifiers.append(part)
            else:
                # 单个标识符（数字索引或cell_id）
                identifiers.append(part)
        
        # 去重但保持顺序
        seen = set()
        result = []
        for identifier in identifiers:
            if identifier not in seen:
                seen.add(identifier)
                result.append(identifier)
        
        return result
        
    except (ValueError, AttributeError) as e:
        print(f"解析范围字符串失败: {range_str}, 错误: {e}")
        return []


def resolve_cell_identifiers(notebook, identifiers: List[str]) -> List[int]:
    """
    解析cell标识符列表（索引或ID）
    
    Args:
        notebook: notebook对象
        identifiers: 标识符列表
    
    Returns:
        有效的cell索引列表
    """
    indices = []
    
    if not notebook:
        return indices
    
    for identifier in identifiers:
        identifier = identifier.strip()
        
        # 尝试作为数字索引
        try:
            idx = int(identifier)
            if 0 <= idx < len(notebook.cells):
                indices.append(idx)
            continue
        except ValueError:
            pass
        
        # 尝试作为cell ID
        for i, cell in enumerate(notebook.cells):
            cell_id = get_cell_id(cell)
            if cell_id == identifier:
                indices.append(i)
                break
    
    return sorted(list(set(indices)))


def parse_and_resolve_cells(notebook, identifiers_str):
    """
    统一的cell标识符解析入口函数
    支持数字索引、cell ID、范围、混合格式
    
    Args:
        notebook: notebook对象
        identifiers_str: 标识符字符串或None/'all'
        
    Returns:
        有效的cell索引列表
    """
    if identifiers_str in [None, 'all']:
        return list(range(len(notebook.cells))) if notebook else []
    
    # 使用现有的解析函数
    identifier_list = parse_cell_range(identifiers_str)
    return resolve_cell_identifiers(notebook, identifier_list)


def format_cell_reference(cell_index, cell_id=None, cell_object=None):
    """
    统一的cell引用格式化函数
    格式: [index] cell_id[:6] 或 [index]
    
    Args:
        cell_index: cell索引
        cell_id: cell ID（可选）
        cell_object: cell对象（可选，用于自动获取ID）
        
    Returns:
        格式化的cell引用字符串
    """
    if cell_id is None and cell_object is not None:
        cell_id = get_cell_id(cell_object)
    
    if cell_id:
        return f"[{cell_index}] {cell_id[:6]}"
    return f"[{cell_index}]"


def get_cell_id(cell) -> str:
    """获取cell的ID"""
    if hasattr(cell, 'id') and cell.id:
        return cell.id
    elif hasattr(cell, 'metadata') and 'id' in cell.metadata:
        return cell.metadata['id']
    else:
        return ""


def format_execution_result(result: Dict[str, Any]) -> str:
    """
    格式化执行结果为可读字符串，提供详细的单cell执行状态
    
    Args:
        result: 执行结果字典
    
    Returns:
        格式化的结果字符串
    """
    if 'error' in result:
        return f"❌ 执行失败: {result['error']}"
    
    lines = []
    
    # 总体状态标题
    success = result.get('success_count', 0)
    failed = result.get('error_count', 0)
    total = success + failed
    
    if failed == 0:
        status_icon = "✅"
        status_text = "成功"
    elif success == 0:
        status_icon = "❌"
        status_text = "失败"
    else:
        status_icon = "⚠️"
        status_text = "部分成功"
    
    lines.append(f"{status_icon} {status_text} 批量执行: {total} 个cells")
    lines.append("")
    
    # 显示每个cell的详细执行结果
    if 'results' in result:
        for cell_result in result['results']:
            idx = cell_result['cell_index']
            cell_id = cell_result.get('cell_id', '')
            success = cell_result['success']
            exec_time = cell_result.get('execution_time', 0)
            
            # 统一的cell引用格式
            cell_ref = format_cell_reference(idx, cell_id)
            
            if success:
                lines.append(f"✅ Cell {cell_ref}: 执行成功 ({exec_time:.1f}s)")
                
                # 显示输出预览（如果有）
                if cell_result.get('outputs'):
                    output_preview = str(cell_result['outputs'][0])[:80] if cell_result['outputs'] else ""
                    if len(output_preview) > 77:
                        output_preview = output_preview[:77] + "..."
                    if output_preview.strip():
                        lines.append(f"   输出: {output_preview}")
            else:
                lines.append(f"❌ Cell {cell_ref}: 执行失败 ({exec_time:.1f}s)")
                
                # 显示错误信息
                if cell_result.get('errors'):
                    error_msg = cell_result['errors'][0] if cell_result['errors'] else "未知错误"
                    # 尝试提取错误类型
                    if ':' in error_msg:
                        error_type = error_msg.split(':')[0].strip()
                        error_detail = error_msg.split(':', 1)[1].strip()
                        lines.append(f"   错误: {error_type}")
                        if len(error_detail) > 60:
                            error_detail = error_detail[:57] + "..."
                        lines.append(f"   详情: {error_detail}")
                    else:
                        if len(error_msg) > 60:
                            error_msg = error_msg[:57] + "..."
                        lines.append(f"   错误: {error_msg}")
                
                # 尝试提取行号信息（如果有traceback）
                if 'traceback' in cell_result:
                    # 使用已有的行号解析逻辑
                    try:
                        # 确保模块路径
                        import sys
                        current_dir = Path(__file__).parent.parent
                        if str(current_dir) not in sys.path:
                            sys.path.insert(0, str(current_dir))
                        
                        from core.notebook_analyzer import parse_error_line_number
                        line_info = parse_error_line_number(cell_result['traceback'])
                        if line_info:
                            lines.append(f"   位置: {line_info}")
                    except ImportError:
                        # 导入失败时忽略行号信息
                        pass
            
            lines.append("")
    
    # 汇总统计信息
    lines.append("📊 执行统计:")
    lines.append(f"   成功: {success} 个")
    lines.append(f"   失败: {failed} 个")
    lines.append(f"   成功率: {(success/total*100):.1f}%" if total > 0 else "   成功率: 0%")
    
    if 'total_time' in result:
        total_time = result['total_time']
        lines.append(f"   总耗时: {total_time:.1f}s")
    
    return '\n'.join(lines)