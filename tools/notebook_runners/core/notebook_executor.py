#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notebook Executor Module
简化的notebook执行器，采用无状态设计，每次执行启动新kernel，基于依赖自动执行所需cells
"""

import os
import ast
import sys
import time
import hashlib
from typing import List, Dict, Set, Any, Optional, Tuple
from pathlib import Path

import nbformat
from jupyter_client import KernelManager

# 抑制调试警告
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'


class SimpleAST_Analyzer:
    """简化的AST分析器，提取变量依赖关系"""
    
    @staticmethod
    def extract_variables(source: str) -> Tuple[Set[str], Set[str]]:
        """
        提取代码中的使用变量和定义变量
        
        Returns:
            (used_vars, defined_vars)
        """
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
                        elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
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
            # 简单的变量定义匹配
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


class NotebookExecutor:
    """简化的Notebook执行器"""
    
    def __init__(self, notebook_path: str):
        self.notebook_path = Path(notebook_path)
        self.notebook = None
        self.dependencies = {}
        self._load_notebook()
        self._analyze_dependencies()
    
    def _load_notebook(self):
        """加载notebook文件"""
        try:
            with open(self.notebook_path, 'r', encoding='utf-8') as f:
                self.notebook = nbformat.read(f, as_version=4)
        except Exception as e:
            raise RuntimeError(f"无法加载notebook文件: {e}")
    
    def _save_notebook(self):
        """保存notebook文件"""
        try:
            # 确保目录存在
            self.notebook_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.notebook_path, 'w', encoding='utf-8') as f:
                nbformat.write(self.notebook, f)
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _analyze_dependencies(self):
        """分析cell间的依赖关系"""
        if not self.notebook:
            return
        
        defined_vars = {}  # 变量名 -> cell索引
        self.dependencies = {}  # cell索引 -> 依赖的cell索引集合
        
        for i, cell in enumerate(self.notebook.cells):
            if cell.cell_type != 'code':
                self.dependencies[i] = set()
                continue
            
            # 分析当前cell
            used_vars, new_defined = SimpleAST_Analyzer.extract_variables(cell.source)
            
            # 找出依赖的cells
            deps = set()
            for var in used_vars:
                if var in defined_vars:
                    deps.add(defined_vars[var])
            
            self.dependencies[i] = deps
            
            # 更新变量定义位置
            for var in new_defined:
                defined_vars[var] = i
    
    def _get_execution_order(self, target_cells: List[int]) -> List[int]:
        """根据依赖关系确定执行顺序"""
        to_execute = set()
        visited = set()
        
        def add_dependencies(cell_idx):
            if cell_idx in visited or cell_idx >= len(self.notebook.cells):
                return
            visited.add(cell_idx)
            
            # 添加依赖的cells
            if cell_idx in self.dependencies:
                for dep in self.dependencies[cell_idx]:
                    add_dependencies(dep)
                    to_execute.add(dep)
            
            to_execute.add(cell_idx)
        
        # 为每个目标cell添加其依赖
        for cell_idx in target_cells:
            add_dependencies(cell_idx)
        
        # 返回按索引排序的执行列表
        return sorted([idx for idx in to_execute 
                      if idx < len(self.notebook.cells) and 
                      self.notebook.cells[idx].cell_type == 'code'])
    
    def _calculate_timeout(self, source: str) -> int:
        """根据代码内容计算合理的超时时间"""
        base_timeout = 30  # 基础超时30秒
        
        # 根据代码特征调整超时
        if any(keyword in source.lower() for keyword in 
               ['train', 'fit', 'predict', 'model', 'sklearn', 'tensorflow', 'pytorch']):
            return 300  # 机器学习相关：5分钟
        elif any(keyword in source.lower() for keyword in 
                ['plot', 'figure', 'plt.', 'plotly', 'seaborn']):
            return 60   # 绘图相关：1分钟
        elif any(keyword in source.lower() for keyword in 
                ['read_csv', 'read_excel', 'pd.read', 'load', 'download']):
            return 120  # 数据加载：2分钟
        elif len(source) > 1000:
            return 90   # 长代码：1.5分钟
        else:
            return base_timeout
    
    def _execute_single_cell(self, kc, cell_idx: int, source: str, show_output: bool = False) -> Dict[str, Any]:
        """执行单个cell"""
        timeout = self._calculate_timeout(source)
        
        try:
            # 执行代码
            msg_id = kc.execute(source)
            
            # 收集输出（结构化格式，保存到notebook）
            cell_outputs = []
            text_outputs = []  # 用于控制台显示
            errors = []
            execution_count = None
            
            start_time = time.time()
            while True:
                try:
                    msg = kc.get_iopub_msg(timeout=5)
                    msg_type = msg['header']['msg_type']
                    content = msg['content']
                    
                    if msg_type == 'status' and content['execution_state'] == 'idle':
                        break
                    elif msg_type == 'execute_input':
                        # 获取执行计数
                        execution_count = content.get('execution_count')
                    elif msg_type == 'stream':
                        # 流输出（print语句等）
                        stream_output = nbformat.v4.new_output(
                            output_type='stream',
                            name=content['name'],
                            text=content['text']
                        )
                        cell_outputs.append(stream_output)
                        text_outputs.append(content['text'])
                        if show_output:
                            print(f"[Cell {cell_idx}] {content['text']}", end='')
                    elif msg_type == 'execute_result':
                        # 执行结果输出
                        execute_result = nbformat.v4.new_output(
                            output_type='execute_result',
                            execution_count=content['execution_count'],
                            data=content['data'],
                            metadata=content.get('metadata', {})
                        )
                        cell_outputs.append(execute_result)
                        
                        # 控制台显示文本部分
                        text_result = content['data'].get('text/plain', '')
                        text_outputs.append(text_result)
                        if show_output:
                            print(f"[Cell {cell_idx}] Out: {text_result}")
                            
                        # 检查是否有图像数据
                        data = content['data']
                        image_types = ['image/png', 'image/jpeg', 'application/vnd.plotly.v1+json']
                        for img_type in image_types:
                            if img_type in data:
                                if show_output:
                                    print(f"[Cell {cell_idx}] 📊 发现 {img_type} 图像输出")
                                break
                                
                    elif msg_type == 'display_data':
                        # 显示数据输出（如Plotly图表）
                        display_output = nbformat.v4.new_output(
                            output_type='display_data',
                            data=content['data'],
                            metadata=content.get('metadata', {})
                        )
                        cell_outputs.append(display_output)
                        
                        # 检查图像数据
                        data = content['data']
                        image_types = ['image/png', 'image/jpeg', 'application/vnd.plotly.v1+json']
                        found_image = False
                        for img_type in image_types:
                            if img_type in data:
                                if show_output:
                                    print(f"[Cell {cell_idx}] 📊 显示 {img_type} 图像")
                                found_image = True
                                break
                        
                        if not found_image and 'text/plain' in data:
                            text_outputs.append(data['text/plain'])
                            
                    elif msg_type == 'error':
                        # 错误输出
                        error_output = nbformat.v4.new_output(
                            output_type='error',
                            ename=content['ename'],
                            evalue=content['evalue'],
                            traceback=content['traceback']
                        )
                        cell_outputs.append(error_output)
                        
                        error_msg = '\n'.join(content['traceback'])
                        errors.append(error_msg)
                        if show_output:
                            print(f"[Cell {cell_idx}] ERROR: {error_msg}")
                
                except Exception:
                    if time.time() - start_time > timeout:
                        errors.append(f"Cell执行超时 ({timeout}s)")
                        break
                    continue
            
            # 提取traceback信息用于行号解析
            traceback_info = []
            for output in cell_outputs:
                if output.output_type == 'error':
                    traceback_info = output.traceback
                    break
            
            return {
                'cell_index': cell_idx,
                'cell_id': self.notebook.cells[cell_idx].id if hasattr(self.notebook.cells[cell_idx], 'id') else None,
                'cell_content': source,  # 完整代码内容
                'success': len(errors) == 0,
                'outputs': text_outputs,  # 文本输出用于显示
                'cell_outputs': cell_outputs,  # 结构化输出用于保存
                'execution_count': execution_count,
                'errors': errors,
                'traceback': traceback_info,  # 添加traceback信息供行号解析使用
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            return {
                'cell_index': cell_idx,
                'success': False,
                'outputs': [],
                'errors': [str(e)],
                'execution_time': 0
            }
    
    def _execute_cells_direct(self, cell_indices: List[int], show_output: bool = False) -> Dict[str, Any]:
        """
        直接按给定顺序执行cells，不进行依赖排序
        
        Args:
            cell_indices: cell索引列表
            show_output: 是否显示输出
        
        Returns:
            执行结果统计
        """
        if not self.notebook:
            return {'error': 'Notebook未加载'}
        
        if show_output:
            print(f"🚀 按序执行: {len(cell_indices)} 个cells")
            print(f"   执行顺序: {cell_indices}")
            print()
        
        # 创建新kernel
        km = KernelManager(kernel_name='python3')
        km.start_kernel()
        kc = km.client()
        kc.start_channels()
        
        results = []
        total_time = 0
        success_count = 0
        error_count = 0
        
        try:
            # 等待kernel就绪
            kc.wait_for_ready(timeout=30)
            
            # 按给定顺序逐个执行cells
            for cell_idx in cell_indices:
                if cell_idx >= len(self.notebook.cells):
                    continue
                    
                cell = self.notebook.cells[cell_idx]
                
                if cell.cell_type != 'code':
                    continue
                
                if show_output:
                    print(f"[{cell_idx}] 执行中...")
                
                result = self._execute_single_cell(
                    kc, cell_idx, cell.source, show_output
                )
                
                # 保存输出到notebook（增强调试）
                if 'cell_outputs' in result and result['cell_outputs']:
                    if show_output:
                        print(f"[Cell {cell_idx}] 保存 {len(result['cell_outputs'])} 个输出到notebook")
                        for i, output in enumerate(result['cell_outputs']):
                            output_type = getattr(output, 'output_type', 'unknown')
                            if hasattr(output, 'data') and output.data:
                                data_keys = list(output.data.keys())
                                print(f"   输出 {i}: {output_type}, 数据类型: {data_keys}")
                            else:
                                print(f"   输出 {i}: {output_type}")
                    cell.outputs = result['cell_outputs']
                else:
                    if show_output:
                        print(f"[Cell {cell_idx}] 清空输出")
                    cell.outputs = []
                
                # 保存执行计数
                if result.get('execution_count'):
                    cell.execution_count = result['execution_count']
                    if show_output:
                        print(f"[Cell {cell_idx}] ✓ 执行完成")
                
                # 立即保存notebook（改进的保存时机）
                save_result = self._save_notebook()
                if show_output:
                    if save_result:
                        print(f"[Cell {cell_idx}] ✓ notebook已保存")
                    else:
                        print(f"[Cell {cell_idx}] ✗ notebook保存失败")
                
                results.append(result)
                total_time += result['execution_time']
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    if show_output:
                        print(f"❌ Cell {cell_idx} 执行失败")
                        for error in result['errors']:
                            print(f"   {error}")
        
        finally:
            # 清理kernel
            try:
                kc.stop_channels()
                km.shutdown_kernel()
            except:
                pass
        
        # 执行完成后同步图片状态
        self._sync_images_after_execution(cell_indices, show_output)
        
        return {
            'target_cells': cell_indices,
            'execution_order': cell_indices,  # 直接按输入顺序
            'total_cells_executed': len([r for r in results if r['success'] or r['errors']]),
            'success_count': success_count,
            'error_count': error_count,
            'total_time': total_time,
            'results': results
        }
    
    def execute_cells(self, target_cells: List[int], show_output: bool = False) -> Dict[str, Any]:
        """
        执行指定的cells及其依赖
        
        Args:
            target_cells: 目标cell索引列表
            show_output: 是否显示输出
        
        Returns:
            执行结果统计
        """
        if not self.notebook:
            return {'error': 'Notebook未加载'}
        
        # 获取执行顺序（包含依赖）
        execution_order = self._get_execution_order(target_cells)
        
        if show_output:
            print(f"🚀 执行计划: {len(execution_order)} 个cells")
            print(f"   目标cells: {target_cells}")
            print(f"   执行顺序: {execution_order}")
            print()
        
        # 创建新kernel
        km = KernelManager(kernel_name='python3')
        km.start_kernel()
        kc = km.client()
        kc.start_channels()
        
        results = []
        total_time = 0
        success_count = 0
        error_count = 0
        
        try:
            # 等待kernel就绪
            kc.wait_for_ready(timeout=30)
            
            # 逐个执行cells
            for cell_idx in execution_order:
                cell = self.notebook.cells[cell_idx]
                
                if show_output:
                    print(f"[{cell_idx}] 执行中...")
                
                result = self._execute_single_cell(
                    kc, cell_idx, cell.source, show_output
                )
                
                # 保存输出到notebook（增强调试）
                if 'cell_outputs' in result and result['cell_outputs']:
                    if show_output:
                        print(f"[Cell {cell_idx}] 保存 {len(result['cell_outputs'])} 个输出到notebook")
                        for i, output in enumerate(result['cell_outputs']):
                            output_type = getattr(output, 'output_type', 'unknown')
                            if hasattr(output, 'data') and output.data:
                                data_keys = list(output.data.keys())
                                print(f"   输出 {i}: {output_type}, 数据类型: {data_keys}")
                            else:
                                print(f"   输出 {i}: {output_type}")
                    cell.outputs = result['cell_outputs']
                else:
                    if show_output:
                        print(f"[Cell {cell_idx}] 清空输出")
                    cell.outputs = []
                
                # 保存执行计数
                if result.get('execution_count'):
                    cell.execution_count = result['execution_count']
                    if show_output:
                        print(f"[Cell {cell_idx}] ✓ 执行完成")
                
                # 立即保存notebook（改进的保存时机）
                save_result = self._save_notebook()
                if show_output:
                    if save_result:
                        print(f"[Cell {cell_idx}] ✓ notebook已保存")
                    else:
                        print(f"[Cell {cell_idx}] ✗ notebook保存失败")
                
                results.append(result)
                total_time += result['execution_time']
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    if show_output:
                        print(f"❌ Cell {cell_idx} 执行失败")
                        for error in result['errors']:
                            print(f"   {error}")
        
        finally:
            # 清理kernel
            try:
                kc.stop_channels()
                km.shutdown_kernel()
            except:
                pass
        
        # 执行完成后同步图片状态
        self._sync_images_after_execution(execution_order, show_output)
        
        return {
            'target_cells': target_cells,
            'execution_order': execution_order,
            'total_cells_executed': len(execution_order),
            'success_count': success_count,
            'error_count': error_count,
            'total_time': total_time,
            'results': results
        }
    
    def execute_all(self, show_output: bool = False) -> Dict[str, Any]:
        """按原始顺序执行所有code cells（不进行依赖排序）"""
        if not self.notebook:
            return {'error': 'Notebook未加载'}
        
        code_cells = [i for i, cell in enumerate(self.notebook.cells) 
                     if cell.cell_type == 'code']
        
        return self._execute_cells_direct(code_cells, show_output)
    
    def execute_range(self, start: int, end: int, show_output: bool = False) -> Dict[str, Any]:
        """执行指定范围的cells"""
        if start < 0 or end >= len(self.notebook.cells) or start > end:
            return {'error': f'无效的范围: {start}-{end}'}
        
        target_cells = list(range(start, end + 1))
        return self.execute_cells(target_cells, show_output)
    
    def get_cell_count(self) -> int:
        """获取cell总数"""
        return len(self.notebook.cells) if self.notebook else 0
    
    def _sync_images_after_execution(self, executed_cells: List[int], show_output: bool = False):
        """
        执行完成后强制同步图片状态
        对所有已执行的cell进行无条件图片同步
        
        Args:
            executed_cells: 已执行的cell索引列表
            show_output: 是否显示输出信息
        """
        try:
            from core.image_manager import ImageManager
            
            image_mgr = ImageManager(str(self.notebook_path))
            
            # 重新加载notebook获取最新的输出状态
            updated_notebook = image_mgr._load_notebook()
            if not updated_notebook:
                return
            
            synced_count = 0
            total_images = 0
            
            if show_output:
                print(f"🔄 强制同步 {len(executed_cells)} 个已执行cell的图片状态")
            
            # 对所有已执行的cells进行强制图片同步
            cells_with_images = []
            for cell_idx in executed_cells:
                if cell_idx < len(updated_notebook.cells):
                    cell = updated_notebook.cells[cell_idx]
                    if cell.cell_type == 'code':
                        result = image_mgr.save_cell_images(cell, cell_idx)
                        
                        if result['action'] == 'saved':
                            synced_count += 1
                            image_count = result.get('images_count', 0)
                            total_images += image_count
                            cells_with_images.append((cell_idx, image_count))
                        elif result['action'] == 'cleaned':
                            synced_count += 1
            
            # 输出同步结果摘要 - 只显示含图片的cell
            if show_output:
                if cells_with_images:
                    for cell_idx, image_count in cells_with_images:
                        print(f"🖼️  Cell [{cell_idx}] 包含 {image_count} 个图片")
                else:
                    print(f"ℹ️  本次执行无图片输出")
                    
        except Exception as e:
            if show_output:
                print(f"⚠️  图片同步失败: {e}")
    
    def get_dependencies(self) -> Dict[int, Set[int]]:
        """获取依赖关系映射"""
        return self.dependencies.copy()


# 全局函数，保持向后兼容
def run_entire_notebook(notebook_path: str, kernel_name: str = 'python3', 
                       show_output: bool = False) -> bool:
    """执行整个notebook（兼容函数）"""
    try:
        executor = NotebookExecutor(notebook_path)
        result = executor.execute_all(show_output)
        return 'error' not in result and result['error_count'] == 0
    except Exception as e:
        print(f"执行失败: {e}")
        return False