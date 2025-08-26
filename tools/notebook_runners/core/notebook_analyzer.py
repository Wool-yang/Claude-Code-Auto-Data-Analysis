#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notebook Analyzer Module
处理notebook结构分析、搜索和依赖查询功能
"""

import os
import re
import ast
from typing import List, Dict, Set, Any, Optional, Tuple
from pathlib import Path

import nbformat

# 抑制调试警告
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'


def parse_error_line_number(traceback_lines: List[str]) -> Optional[str]:
    """
    从traceback信息中解析错误行号
    支持多种Jupyter traceback格式，提供健壮的行号提取
    
    Args:
        traceback_lines: traceback行列表
        
    Returns:
        格式化的行号信息，如 "(第6行)"，解析失败返回None
    """
    if not traceback_lines:
        return None
    
    # 定义多种可能的行号匹配模式
    patterns = [
        # 新版Jupyter格式: Cell [1;32mIn[1], line 6[0m
        r'Cell.*?line (\d+)',
        # 经典格式: <ipython-input-1-abc123> in <module>() line 6
        r'<ipython-input-.*?line (\d+)',
        # 通用格式: line 6
        r'line (\d+)',
        # 行号在箭头后: ----> 6
        r'---->\s*(\d+)',
    ]
    
    for trace_line in traceback_lines:
        # 跳过明显的注释或非traceback行
        if trace_line.strip().startswith('#') or not trace_line.strip():
            continue
            
        for pattern in patterns:
            match = re.search(pattern, trace_line)
            if match:
                line_num = match.group(1)
                return f" (第{line_num}行)"
    
    return None


class NotebookAnalyzer:
    """Notebook分析器"""
    
    def __init__(self, notebook_path: str):
        self.notebook_path = Path(notebook_path)
        self.notebook = None
        self._load_notebook()
    
    def _load_notebook(self):
        """加载notebook文件"""
        try:
            if self.notebook_path.exists():
                with open(self.notebook_path, 'r', encoding='utf-8') as f:
                    self.notebook = nbformat.read(f, as_version=4)
            else:
                raise FileNotFoundError(f"Notebook文件不存在: {self.notebook_path}")
        except Exception as e:
            raise RuntimeError(f"无法加载notebook文件: {e}")
    
    def get_structure_info(self) -> Dict[str, Any]:
        """获取notebook结构信息"""
        if not self.notebook:
            return {}
        
        total_cells = len(self.notebook.cells)
        code_cells = sum(1 for cell in self.notebook.cells if cell.cell_type == 'code')
        markdown_cells = sum(1 for cell in self.notebook.cells if cell.cell_type == 'markdown')
        raw_cells = sum(1 for cell in self.notebook.cells if cell.cell_type == 'raw')
        
        # 统计代码cell的执行状态
        executed_cells = 0
        error_cells = 0
        output_cells = 0
        
        for cell in self.notebook.cells:
            if cell.cell_type == 'code':
                if hasattr(cell, 'execution_count') and cell.execution_count:
                    executed_cells += 1
                
                if hasattr(cell, 'outputs') and cell.outputs:
                    output_cells += 1
                    # 检查是否有错误
                    for output in cell.outputs:
                        if output.output_type == 'error':
                            error_cells += 1
                            break
        
        # 计算总代码行数
        total_lines = sum(len(cell.source.splitlines()) 
                         for cell in self.notebook.cells if cell.cell_type == 'code')
        
        return {
            'total_cells': total_cells,
            'code_cells': code_cells,
            'markdown_cells': markdown_cells,
            'raw_cells': raw_cells,
            'executed_cells': executed_cells,
            'error_cells': error_cells,
            'output_cells': output_cells,
            'total_code_lines': total_lines,
            'file_size': self.notebook_path.stat().st_size if self.notebook_path.exists() else 0
        }
    
    def show_structure(self) -> None:
        """显示notebook结构"""
        info = self.get_structure_info()
        
        print(f"📊 Notebook结构分析: {self.notebook_path.name}")
        print(f"   总Cell数: {info['total_cells']}")
        print(f"   代码Cell: {info['code_cells']} (已执行: {info['executed_cells']}, 有输出: {info['output_cells']}, 有错误: {info['error_cells']})")
        print(f"   Markdown: {info['markdown_cells']}")
        print(f"   Raw: {info['raw_cells']}")
        print(f"   总代码行数: {info['total_code_lines']}")
        print(f"   文件大小: {info['file_size'] / 1024:.1f} KB")
    
    def get_cells_info(self, identifiers=None, output_only=False):
        """
        统一的cell信息获取方法
        
        Args:
            identifiers: cell标识符，支持索引/ID/范围/混合格式，None或'all'表示所有cells
            output_only: 是否仅返回输出信息
        
        Returns:
            格式化的cell信息字符串
        """
        if not self.notebook:
            return "❌ Notebook未加载"
        
        # 使用统一的cell标识符解析
        try:
            from utils.helpers import parse_and_resolve_cells
            target_indices = parse_and_resolve_cells(self.notebook, identifiers)
        except ImportError:
            # 如果导入失败，回退到简单解析
            target_indices = self._simple_parse_identifiers(identifiers)
        
        if not target_indices:
            return f"❌ 未找到有效的cell: {identifiers}"
        
        result = []
        result.append("=== Cell Information ===" if not output_only else "=== Cell Outputs ===")
        result.append(f"Total cells: {len(self.notebook.cells)}")
        result.append(f"Requested cells: {len(target_indices)}")
        result.append("")
        
        for idx in target_indices:
            if idx >= len(self.notebook.cells):
                continue
                
            cell = self.notebook.cells[idx]
            
            # 使用统一的cell引用格式
            from utils.helpers import format_cell_reference
            cell_ref = format_cell_reference(idx, cell_object=cell)
            
            if output_only:
                # 仅输出信息（完整，不截断）
                result.append(f"Cell {cell_ref}")
                if hasattr(cell, 'outputs') and cell.outputs:
                    result.append(f"Outputs: {len(cell.outputs)}")
                    for output in cell.outputs:
                        if output.output_type == 'stream':
                            result.append(f"- stream[{output.name}]:")
                            result.append(output.text)  # 完整内容
                        elif output.output_type == 'execute_result':
                            result.append(f"- execute_result[data]:")
                            if 'text/plain' in output.data:
                                result.append(output.data['text/plain'])  # 完整内容
                            for mime_type in output.data:
                                if mime_type.startswith('image/'):
                                    result.append(f"  {mime_type}: <image data>")
                        elif output.output_type == 'error':
                            result.append(f"- error: {output.ename}: {output.evalue}")
                            # 添加行号信息
                            line_info = parse_error_line_number(output.traceback)
                            if line_info:
                                result.append(f"  行号: {line_info}")
                            result.append("Traceback:")
                            for line in output.traceback:
                                result.append(line)  # 完整追踪
                else:
                    result.append("Outputs: None")
            else:
                # 完整信息（内容+输出，不截断）
                executed = bool(getattr(cell, 'execution_count', 0)) if cell.cell_type == 'code' else 'N/A'
                result.append(f"Cell {cell_ref} type={cell.cell_type} executed={executed}")
                result.append("Content:")
                result.append(cell.source if cell.source else "(empty)")  # 完整源代码
                
                if hasattr(cell, 'outputs') and cell.outputs:
                    result.append("Outputs:")
                    for output in cell.outputs:
                        if output.output_type == 'stream':
                            result.append(f"- {output.name}: {output.text}")  # 完整
                        elif output.output_type == 'execute_result':
                            if 'text/plain' in output.data:
                                result.append(f"- data: {output.data['text/plain']}")  # 完整
                            for mime_type in output.data:
                                if mime_type.startswith('image/'):
                                    result.append(f"- {mime_type}: <image data>")
                        elif output.output_type == 'error':
                            result.append(f"- error: {output.ename}: {output.evalue}")
                            # 添加行号信息
                            line_info = parse_error_line_number(output.traceback)
                            if line_info:
                                result.append(f"  行号: {line_info}")
                            result.append("Traceback:")
                            for line in output.traceback:
                                result.append(f"  {line}")
                else:
                    result.append("Outputs: None")
            result.append("")
        
        return '\n'.join(result)
    
    def _simple_parse_identifiers(self, identifiers_str):
        """简单的标识符解析（备用方法）"""
        parts = identifiers_str.split(',')
        indices = []
        
        for part in parts:
            part = part.strip()
            
            # 范围格式 (仅数字)
            if '-' in part and part.replace('-', '').replace(' ', '').isdigit():
                try:
                    start, end = map(int, part.split('-'))
                    indices.extend(range(start, end + 1))
                except ValueError:
                    continue
            # 数字索引
            elif part.isdigit():
                indices.append(int(part))
            else:
                # Cell ID - 查找对应的索引
                for i, cell in enumerate(self.notebook.cells):
                    if getattr(cell, 'id', '') == part:
                        indices.append(i)
                        break
        
        return sorted(set([idx for idx in indices if 0 <= idx < len(self.notebook.cells)]))
    
    def analyze_dependencies(self) -> Dict[int, Set[int]]:
        """分析cell间的依赖关系"""
        if not self.notebook:
            return {}
        
        dependencies = {}
        defined_vars = {}  # 变量名 -> cell索引
        
        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type != 'code':
                dependencies[i] = set()
                continue
            
            used_vars, new_defined = self._extract_variables(cell.source)
            
            # 找出依赖的cells
            deps = set()
            for var in used_vars:
                if var in defined_vars:
                    deps.add(defined_vars[var])
            
            dependencies[i] = deps
            
            # 更新变量定义位置
            for var in new_defined:
                defined_vars[var] = i
        
        return dependencies
    
    def _extract_variables(self, source: str) -> Tuple[Set[str], Set[str]]:
        """提取代码中的使用变量和定义变量"""
        used_vars = set()
        defined_vars = set()
        
        try:
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                # 变量赋值（定义）
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            defined_vars.add(target.id)
                        elif isinstance(target, (ast.Tuple, ast.List)):
                            for elt in target.elts:
                                if isinstance(elt, ast.Name):
                                    defined_vars.add(elt.id)
                
                # 函数定义
                elif isinstance(node, ast.FunctionDef):
                    defined_vars.add(node.name)
                
                # 类定义
                elif isinstance(node, ast.ClassDef):
                    defined_vars.add(node.name)
                
                # 导入语句
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        defined_vars.add(name)
                
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        if name != '*':
                            defined_vars.add(name)
                
                # 变量使用
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_vars.add(node.id)
        
        except:
            # 解析失败时，回退到简单的正则匹配
            import re
            def_patterns = [
                r'(\w+)\s*=',  # 赋值
                r'def\s+(\w+)',  # 函数定义
                r'class\s+(\w+)',  # 类定义
                r'import\s+(\w+)',  # 导入
                r'from\s+\w+\s+import\s+(\w+)'  # from import
            ]
            
            for pattern in def_patterns:
                matches = re.findall(pattern, source)
                defined_vars.update(matches)
        
        return used_vars, defined_vars
    
    def show_dependencies(self) -> None:
        """显示依赖关系"""
        dependencies = self.analyze_dependencies()
        
        print(f"🔗 Cell依赖关系: {self.notebook_path.name}")
        print()
        
        has_deps = False
        for cell_idx, deps in dependencies.items():
            if deps:
                has_deps = True
                print(f"   Cell [{cell_idx}] 依赖于: {sorted(list(deps))}")
        
        if not has_deps:
            print("   没有发现明显的依赖关系")
    
    def search_content(self, pattern: str, case_sensitive: bool = False, 
                      regex: bool = False) -> List[Dict[str, Any]]:
        """
        搜索cell内容
        
        Args:
            pattern: 搜索模式
            case_sensitive: 是否大小写敏感
            regex: 是否使用正则表达式
        
        Returns:
            匹配结果列表
        """
        if not self.notebook:
            return []
        
        results = []
        
        for i, cell in enumerate(self.notebook.cells):
            matches = []
            
            if regex:
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    pattern_obj = re.compile(pattern, flags)
                    
                    for line_no, line in enumerate(cell.source.splitlines(), 1):
                        for match in pattern_obj.finditer(line):
                            matches.append({
                                'line_number': line_no,
                                'line_content': line,
                                'match_start': match.start(),
                                'match_end': match.end(),
                                'matched_text': match.group()
                            })
                except re.error:
                    continue
            else:
                # 简单文本搜索
                search_text = cell.source if case_sensitive else cell.source.lower()
                search_pattern = pattern if case_sensitive else pattern.lower()
                
                if search_pattern in search_text:
                    for line_no, line in enumerate(cell.source.splitlines(), 1):
                        line_search = line if case_sensitive else line.lower()
                        if search_pattern in line_search:
                            matches.append({
                                'line_number': line_no,
                                'line_content': line,
                                'match_start': line_search.find(search_pattern),
                                'match_end': line_search.find(search_pattern) + len(search_pattern),
                                'matched_text': pattern
                            })
            
            if matches:
                results.append({
                    'cell_index': i,
                    'cell_type': cell.cell_type,
                    'matches': matches
                })
        
        return results
    
    def find_errors(self) -> List[int]:
        """查找包含错误的cells"""
        if not self.notebook:
            return []
        
        error_cells = []
        
        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == 'code' and hasattr(cell, 'outputs'):
                for output in cell.outputs:
                    if output.output_type == 'error':
                        error_cells.append(i)
                        break
        
        return error_cells
    
    def extract_error_details(self) -> List[Dict[str, Any]]:
        """
        提取所有错误cells的详细信息
        
        Returns:
            错误信息列表，每个元素包含：
            - index: cell索引
            - cell_id: cell ID（前6位）
            - error_name: 错误类型
            - error_value: 错误消息
            - line_info: 行号信息（格式化后的字符串）
        """
        if not self.notebook:
            return []
        
        error_details = []
        
        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == 'code' and hasattr(cell, 'outputs'):
                for output in cell.outputs:
                    if output.output_type == 'error':
                        # 获取cell ID
                        cell_id = getattr(cell, 'id', str(i))[:6]
                        
                        # 解析行号信息
                        line_info = parse_error_line_number(output.traceback) or ""
                        
                        error_info = {
                            'index': i,
                            'cell_id': cell_id,
                            'error_name': output.ename,
                            'error_value': output.evalue,
                            'line_info': line_info
                        }
                        error_details.append(error_info)
                        break  # 每个cell只记录第一个错误
        
        return error_details
    
    def find_empty_cells(self) -> List[int]:
        """查找空白cells"""
        if not self.notebook:
            return []
        
        return [i for i, cell in enumerate(self.notebook.cells) 
                if not cell.source.strip()]
    
    def find_cells_with_outputs(self, output_type: Optional[str] = None) -> List[int]:
        """查找有输出的cells"""
        if not self.notebook:
            return []
        
        result_cells = []
        
        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type == 'code' and hasattr(cell, 'outputs') and cell.outputs:
                if output_type is None:
                    result_cells.append(i)
                else:
                    # 查找特定类型的输出
                    for output in cell.outputs:
                        if output.output_type == output_type:
                            result_cells.append(i)
                            break
        
        return result_cells
    
    def filter_cells_by_type(self, cell_type: str) -> List[int]:
        """按类型过滤cells"""
        if not self.notebook:
            return []
        
        return [i for i, cell in enumerate(self.notebook.cells) 
                if cell.cell_type == cell_type]
    
    def _format_output_sequence(self, outputs: List[Any]) -> str:
        """
        按顺序格式化输出内容显示
        
        Args:
            outputs: cell输出列表
        
        Returns:
            格式化的输出序列字符串
        """
        if not outputs:
            return "无输出"
        
        # 输出类型到文字的映射
        type_symbols = {
            'stream': '文本',        # 文本输出
            'display_data': '图表',   # 图表/富媒体输出  
            'execute_result': '数据', # 数据结果输出
            'error': '错误'          # 错误输出
        }
        
        # 按顺序生成文字序列
        sequence = []
        error_count = 0
        
        for output in outputs:
            output_type = output.output_type
            symbol = type_symbols.get(output_type, '未知')
            sequence.append(symbol)
            
            if output_type == 'error':
                error_count += 1
        
        # 生成显示字符串，用箭头连接
        sequence_str = '→'.join(sequence)
        
        if error_count > 0:
            return f"输出{len(outputs)}个内容 [{sequence_str}] ({error_count}错误)"
        else:
            return f"输出{len(outputs)}个内容 [{sequence_str}]"

    def _analyze_cell_outputs(self, outputs: List[Any]) -> List[Dict[str, str]]:
        """分析cell输出内容"""
        output_summary = []
        
        for output in outputs:
            output_type = output.output_type
            
            if output_type == 'stream':
                # 文本输出
                text_content = output.get('text', [])
                if isinstance(text_content, list):
                    text_preview = ''.join(text_content)[:100]
                else:
                    text_preview = str(text_content)[:100]
                
                output_summary.append({
                    'category': 'text',
                    'description': f"文本输出 ({len(str(text_content))} 字符): {text_preview.strip()}..."
                })
                
            elif output_type in ['execute_result', 'display_data']:
                # 数据输出
                if hasattr(output, 'data') and output.data:
                    data_types = []
                    has_image = False
                    
                    for mime_type in output.data.keys():
                        if mime_type.startswith('image/'):
                            has_image = True
                            data_types.append(f"图片({mime_type.split('/')[-1].upper()})")
                        elif mime_type == 'text/plain':
                            data_types.append("文本")
                        elif mime_type == 'text/html':
                            data_types.append("HTML")
                        else:
                            data_types.append(mime_type)
                    
                    if has_image:
                        category = 'image'
                    else:
                        category = 'text'
                    
                    output_summary.append({
                        'category': category,
                        'description': f"数据输出: {', '.join(data_types)}"
                    })
                    
            elif output_type == 'error':
                # 错误输出
                error_name = output.get('ename', '未知错误')
                error_value = output.get('evalue', '')
                output_summary.append({
                    'category': 'error',
                    'description': f"错误: {error_name} - {error_value[:50]}..."
                })
                
            else:
                # 其他类型
                output_summary.append({
                    'category': 'other',
                    'description': f"其他输出类型: {output_type}"
                })
        
        return output_summary
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        if not self.notebook:
            return {}
        
        code_cells = [cell for cell in self.notebook.cells if cell.cell_type == 'code']
        
        executed = sum(1 for cell in code_cells 
                      if hasattr(cell, 'execution_count') and cell.execution_count)
        
        with_outputs = sum(1 for cell in code_cells 
                          if hasattr(cell, 'outputs') and cell.outputs)
        
        with_errors = 0
        for cell in code_cells:
            if hasattr(cell, 'outputs'):
                for output in cell.outputs:
                    if output.output_type == 'error':
                        with_errors += 1
                        break
        
        return {
            'total_code_cells': len(code_cells),
            'executed_cells': executed,
            'cells_with_outputs': with_outputs,
            'cells_with_errors': with_errors,
            'execution_rate': executed / len(code_cells) if code_cells else 0
        }



def show_comprehensive_status(notebook_path: str, status_types: List[str]) -> None:
    """
    显示综合状态信息，支持多种查询类型
    
    Args:
        notebook_path: notebook文件路径
        status_types: 状态类型列表，如['exec', 'structure', 'deps', 'errors', 'all']
    """
    try:
        analyzer = NotebookAnalyzer(notebook_path)
        
        print(f"📊 Notebook状态: {Path(notebook_path).name}")
        print()
        
        # 处理 'all' 选项
        if 'all' in status_types:
            status_types = ['structure', 'exec', 'deps', 'errors']
        
        # 显示结构信息
        if 'structure' in status_types:
            structure = analyzer.get_structure_info()
            print(f"📋 结构信息:")
            print(f"   总cells: {structure['total_cells']}")
            print(f"   代码cells: {structure['code_cells']}, Markdown: {structure['markdown_cells']}, Raw: {structure['raw_cells']}")
            print(f"   文件大小: {structure['file_size'] / 1024:.1f} KB, 总代码行数: {structure['total_code_lines']}")
            print()
        
        # 显示执行状态
        if 'exec' in status_types:
            exec_stats = analyzer.get_execution_statistics()
            print(f"⚡ 执行状态:")
            print(f"   已执行: {exec_stats['executed_cells']}/{exec_stats['total_code_cells']}")
            print(f"   执行率: {exec_stats['execution_rate']:.1%}")
            print(f"   有输出: {exec_stats['cells_with_outputs']}, 有错误: {exec_stats['cells_with_errors']}")
            print()
        
        # 显示依赖关系
        if 'deps' in status_types:
            dependencies = analyzer.analyze_dependencies()
            print(f"🔗 依赖关系:")
            
            has_deps = False
            for cell_idx, deps in dependencies.items():
                if deps:
                    has_deps = True
                    from utils.helpers import format_cell_reference
                    cell = analyzer.notebook.cells[cell_idx] if cell_idx < len(analyzer.notebook.cells) else None
                    cell_ref = format_cell_reference(cell_idx, cell_object=cell)
                    dep_refs = []
                    for dep_idx in sorted(list(deps)):
                        dep_cell = analyzer.notebook.cells[dep_idx] if dep_idx < len(analyzer.notebook.cells) else None
                        dep_refs.append(format_cell_reference(dep_idx, cell_object=dep_cell))
                    print(f"   Cell {cell_ref} → {', '.join(dep_refs)}")
            
            if not has_deps:
                print("   没有发现明显的依赖关系")
            print()
        
        # 显示错误检查
        if 'errors' in status_types:
            error_details = analyzer.extract_error_details()
            if error_details:
                print(f"❌ 错误检查: 发现 {len(error_details)} 个错误")
                for error in error_details:
                    from utils.helpers import format_cell_reference
                    cell = analyzer.notebook.cells[error['index']] if error['index'] < len(analyzer.notebook.cells) else None
                    cell_ref = format_cell_reference(error['index'], cell_object=cell)
                    print(f"   Cell {cell_ref}: {error['error_name']}: {error['error_value']}{error['line_info']}")
            else:
                print("✅ 错误检查: 没有发现错误")
            print()
                
    except Exception as e:
        print(f"获取综合状态失败: {e}")


def show_notebook_status(notebook_path: str) -> None:
    """显示notebook详细状态，包含每个cell的执行状态、类型和错误诊断"""
    try:
        analyzer = NotebookAnalyzer(notebook_path)
        
        # 基本结构信息
        structure = analyzer.get_structure_info()
        
        # 执行统计信息
        exec_stats = analyzer.get_execution_statistics()
        
        print(f"📊 Notebook状态: {Path(notebook_path).name}")
        print()
        print(f"📋 结构信息:")
        print(f"   总cells: {structure['total_cells']}")
        print(f"   代码cells: {structure['code_cells']}")
        print()
        print(f"⚡ 执行状态:")
        print(f"   已执行: {exec_stats['executed_cells']}/{exec_stats['total_code_cells']}")
        print(f"   执行率: {exec_stats['execution_rate']:.1%}")
        print(f"   有输出: {exec_stats['cells_with_outputs']}")
        print(f"   有错误: {exec_stats['cells_with_errors']}")
        print()
        
        # 详细cell状态
        print(f"📝 Cell详细状态:")
        error_details = analyzer.extract_error_details()
        error_dict = {err['index']: err for err in error_details}
        
        for i, cell in enumerate(analyzer.notebook.cells):
            # 使用统一的cell引用格式
            from utils.helpers import format_cell_reference
            cell_ref = format_cell_reference(i, cell_object=cell)
            
            # 确定cell类型
            cell_type = f"[{cell.cell_type}]"
            
            # 确定执行状态和输出状态
            if cell.cell_type == 'code':
                # 执行状态
                if hasattr(cell, 'execution_count') and cell.execution_count:
                    exec_status = "✅ 已执行"
                else:
                    exec_status = "❓ 未执行"
                
                # 输出状态
                if hasattr(cell, 'outputs') and cell.outputs:
                    # 检查是否有错误输出
                    has_error = any(output.output_type == 'error' for output in cell.outputs)
                    if has_error:
                        output_status = "⚠️ 有错误"
                    else:
                        output_status = "✅ 有输出"
                else:
                    output_status = "➖ 无输出"
                
                # 状态说明
                if exec_status == "❓ 未执行":
                    status_desc = "(待执行)"
                elif output_status == "⚠️ 有错误":
                    status_desc = "<-- 需要修复"
                else:
                    status_desc = "(正常)"
                    
            else:
                # 非代码cell
                exec_status = "➖ 非代码类型"
                output_status = "➖ 非代码类型"
                status_desc = ""
            
            print(f"   Cell {cell_ref} {cell_type} {exec_status} {output_status}    {status_desc}")
        
        # 问题诊断
        if error_details:
            print()
            print(f"🔍 问题诊断:")
            for error in error_details:
                from utils.helpers import format_cell_reference
                cell = analyzer.notebook.cells[error['index']] if error['index'] < len(analyzer.notebook.cells) else None
                cell_ref = format_cell_reference(error['index'], cell_object=cell)
                print(f"   Cell {cell_ref}: 执行错误 - {error['error_name']}: {error['error_value']}{error['line_info']}")
        
    except Exception as e:
        print(f"获取状态失败: {e}")


def search_notebook(notebook_path: str, pattern: str, case_sensitive: bool = False) -> None:
    """
    在notebook的所有cell内容和输出中搜索指定文本
    
    Args:
        notebook_path: notebook文件路径
        pattern: 搜索模式
        case_sensitive: 是否大小写敏感
    """
    try:
        analyzer = NotebookAnalyzer(notebook_path)
        if not analyzer.notebook:
            print("❌ 无法加载notebook文件")
            return
        
        # 编译搜索模式
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            compiled_pattern = re.compile(pattern, flags)
        except re.error as e:
            print(f"❌ 搜索模式错误: {e}")
            return
        
        results = []
        total_matches = 0
        
        for cell_index, cell in enumerate(analyzer.notebook.cells):
            from utils.helpers import get_cell_id, format_cell_reference
            cell_id = get_cell_id(cell)
            cell_ref = format_cell_reference(cell_index, cell_id, cell)
            
            # 搜索cell源代码
            if cell.source:
                lines = cell.source.splitlines()
                for line_num, line in enumerate(lines, 1):
                    matches = list(compiled_pattern.finditer(line))
                    if matches:
                        results.append({
                            'cell_index': cell_index,
                            'cell_ref': cell_ref,
                            'cell_type': cell.cell_type,
                            'content_type': 'source',
                            'line_num': line_num,
                            'line_content': line.strip(),
                            'matches': matches
                        })
                        total_matches += len(matches)
            
            # 搜索cell输出（仅对code cell）
            if cell.cell_type == 'code' and hasattr(cell, 'outputs') and cell.outputs:
                for output_index, output in enumerate(cell.outputs):
                    output_text = _extract_output_text(output)
                    if output_text:
                        lines = output_text.splitlines()
                        for line_num, line in enumerate(lines, 1):
                            matches = list(compiled_pattern.finditer(line))
                            if matches:
                                results.append({
                                    'cell_index': cell_index,
                                    'cell_ref': cell_ref,
                                    'cell_type': cell.cell_type,
                                    'content_type': f'output[{output_index}]',
                                    'output_type': output.output_type,
                                    'line_num': line_num,
                                    'line_content': line.strip(),
                                    'matches': matches
                                })
                                total_matches += len(matches)
        
        # 输出搜索结果
        if not results:
            print(f"🔍 搜索完成，未找到匹配项: \"{pattern}\"")
            return
        
        print(f"🔍 搜索结果: \"{pattern}\"")
        print(f"   找到 {total_matches} 个匹配项，分布在 {len(results)} 行")
        print()
        
        # 按cell分组显示结果
        current_cell = None
        for result in results:
            # 如果是新的cell，显示cell标题
            if current_cell != result['cell_index']:
                current_cell = result['cell_index']
                print(f"📝 Cell {result['cell_ref']} [{result['cell_type']}]:")
            
            # 显示匹配行
            content_type = result['content_type']
            line_num = result['line_num']
            line_content = result['line_content']
            
            # 高亮显示匹配部分
            highlighted_line = _highlight_matches(line_content, result['matches'], pattern)
            
            if content_type == 'source':
                print(f"   源代码 第{line_num}行: {highlighted_line}")
            else:
                output_type = result.get('output_type', 'unknown')
                print(f"   {content_type}({output_type}) 第{line_num}行: {highlighted_line}")
        
        print()
        print(f"📊 搜索统计:")
        print(f"   匹配项数: {total_matches}")
        print(f"   涉及行数: {len(results)}")
        print(f"   涉及cell数: {len(set(r['cell_index'] for r in results))}")
        
    except Exception as e:
        print(f"❌ 搜索失败: {e}")


def _extract_output_text(output) -> str:
    """
    从output对象中提取文本内容
    
    Args:
        output: notebook output对象
        
    Returns:
        提取的文本内容
    """
    if not output:
        return ""
    
    # stream输出
    if output.output_type == 'stream':
        if hasattr(output, 'text'):
            # text可能是字符串或列表
            if isinstance(output.text, list):
                return ''.join(output.text)
            return str(output.text) if output.text else ""
        return ""
    
    # execute_result输出
    elif output.output_type == 'execute_result':
        if hasattr(output, 'data') and output.data:
            # 优先获取text/plain
            if 'text/plain' in output.data:
                return str(output.data['text/plain'])
            # 其他文本格式
            for mime_type in ['text/html', 'text/markdown', 'text/latex']:
                if mime_type in output.data:
                    return str(output.data[mime_type])
    
    # display_data输出
    elif output.output_type == 'display_data':
        if hasattr(output, 'data') and output.data:
            if 'text/plain' in output.data:
                return str(output.data['text/plain'])
    
    # error输出
    elif output.output_type == 'error':
        if hasattr(output, 'traceback') and output.traceback:
            return '\n'.join(output.traceback)
        elif hasattr(output, 'evalue') and output.evalue:
            return str(output.evalue)
        # 如果都没有，尝试获取 ename
        elif hasattr(output, 'ename') and output.ename:
            return str(output.ename)
    
    return ""


def _highlight_matches(line: str, matches: List, pattern: str) -> str:
    """
    高亮显示匹配的文本
    
    Args:
        line: 原始行内容
        matches: 匹配对象列表
        pattern: 搜索模式
        
    Returns:
        高亮显示的行内容
    """
    if not matches:
        return line
    
    # 简单高亮：用 **pattern** 包围匹配项
    highlighted = line
    
    # 从后往前替换，避免位置偏移问题
    for match in reversed(matches):
        start, end = match.span()
        matched_text = line[start:end]
        highlighted = highlighted[:start] + f"**{matched_text}**" + highlighted[end:]
    
    return highlighted


