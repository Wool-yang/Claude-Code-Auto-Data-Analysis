#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notebook Editor Module
处理所有notebook编辑操作，保持原有功能的完整性
"""

import os
import json
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

import nbformat
from utils.helpers import get_cell_id

# 抑制调试警告
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'


class NotebookEditor:
    """Notebook编辑器"""
    
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
                # 如果文件不存在，创建空的notebook
                self.notebook = nbformat.v4.new_notebook()
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
            return False
    
    def _sync_images_after_edit(self, operation: str, **kwargs):
        """
        编辑后强制同步图片索引
        对所有编辑操作进行无条件图片同步
        """
        try:
            from core.image_manager import ImageManager
            
            # 执行图片同步（无条件）
            image_mgr = ImageManager(str(self.notebook_path))
            result = None
            
            if operation == "delete":
                result = image_mgr.handle_cell_deletion(kwargs.get('deleted_index'))
            elif operation == "insert":
                result = image_mgr.handle_cell_insertion(kwargs.get('inserted_index'))
            elif operation == "move":
                result = image_mgr.handle_cell_move(kwargs.get('old_index'), kwargs.get('new_index'))
            elif operation == "edit":
                result = image_mgr.handle_cell_content_change(kwargs.get('cell_index'))
            elif operation == "clear_output":
                result = image_mgr.handle_cell_content_change(kwargs.get('cell_index'))
            
            # 只在实际有图片操作时才输出信息
            if result and result.get('action') not in ['no_change', 'content_change_handled']:
                # 检查是否有实际的图片操作
                has_real_operation = False
                if result.get('action') == 'deletion_handled':
                    has_real_operation = result.get('deleted_dirs_count', 0) > 0 or result.get('renamed_dirs_count', 0) > 0
                elif result.get('action') == 'insertion_handled':
                    has_real_operation = result.get('renamed_dirs_count', 0) > 0
                elif result.get('action') == 'move_handled':
                    has_real_operation = result.get('moved_dirs_count', 0) > 0
                elif result.get('action') in ['cleaned', 'saved', 'preserved']:
                    has_real_operation = True
                
                if has_real_operation:
                    print(f"🖼️  {result.get('message', '图片同步完成')}")
                
        except Exception as e:
            print(f"Warning: 图片同步失败: {e}")
    
    def _sync_images_after_batch_delete(self, deleted_indices: List[int]):
        """
        批量删除后强制同步图片索引
        批量操作总是需要同步，因为涉及索引重排
        """
        try:
            from core.image_manager import ImageManager
            image_mgr = ImageManager(str(self.notebook_path))
            
            result = image_mgr.handle_batch_deletion(deleted_indices)
            
            # 只在实际有图片操作时才输出信息
            if result and result.get('action') == 'batch_deletion_handled':
                deleted_count = result.get('deleted_dirs_count', 0)
                renamed_count = result.get('renamed_dirs_count', 0)
                
                if deleted_count > 0 or renamed_count > 0:
                    print(f"🖼️  {result.get('message', '批量图片同步完成')}")
                    
        except Exception as e:
            print(f"Warning: 批量图片同步失败: {e}")
    
    def _sync_images_after_batch_clear(self, cleared_indices: List[int]):
        """
        批量清空输出后强制同步图片状态
        对所有清空输出的cell进行无条件图片处理
        """
        try:
            from core.image_manager import ImageManager
            
            # 执行同步（无条件）
            image_mgr = ImageManager(str(self.notebook_path))
            result = image_mgr.handle_batch_clear_outputs(cleared_indices)
            
            # 只在实际有图片操作时才输出信息
            if result and result.get('action') == 'batch_clear_handled':
                cleaned_count = result.get('cleaned_count', 0)
                
                if cleaned_count > 0:
                    message = f"批量清理了 {cleaned_count}/{len(cleared_indices)} 个cells的图片"
                    print(f"🖼️  {message}")
                    
        except Exception as e:
            print(f"Warning: 批量图片清理失败: {e}")
    
    def _resolve_cell_identifier(self, identifier: str) -> Optional[int]:
        """解析cell标识符（索引或ID）"""
        if not self.notebook:
            return None
        
        # 尝试作为数字索引
        try:
            idx = int(identifier)
            if 0 <= idx < len(self.notebook.cells):
                return idx
        except ValueError:
            pass
        
        # 尝试作为cell ID
        for i, cell in enumerate(self.notebook.cells):
            cell_id = get_cell_id(cell)
            if cell_id == identifier:
                return i
        
        return None
    
    def create_notebook(self) -> bool:
        """创建新的空白notebook"""
        try:
            self.notebook = nbformat.v4.new_notebook()
            return self._save_notebook()
        except Exception as e:
            print(f"创建notebook失败: {e}")
            return False
    
    def insert_cell(self, position: int, cell_type: str = 'code', content: str = '') -> bool:
        """
        插入新cell
        
        Args:
            position: 插入位置
            cell_type: cell类型 ('code', 'markdown', 'raw')
            content: cell内容
        """
        try:
            if not self.notebook:
                return False
            
            # 创建新cell
            if cell_type == 'code':
                cell = nbformat.v4.new_code_cell(content)
            elif cell_type == 'markdown':
                cell = nbformat.v4.new_markdown_cell(content)
            elif cell_type == 'raw':
                cell = nbformat.v4.new_raw_cell(content)
            else:
                print(f"未知的cell类型: {cell_type}")
                return False
            
            # 确保position在有效范围内
            position = max(0, min(position, len(self.notebook.cells)))
            
            # 插入cell
            self.notebook.cells.insert(position, cell)
            
            success = self._save_notebook()
            
            if success:
                self._sync_images_after_edit("insert", inserted_index=position)
            
            return success
            
        except Exception as e:
            print(f"插入cell失败: {e}")
            return False
    
    def edit_cell(self, identifier: str, content: str) -> bool:
        """
        编辑cell内容
        
        Args:
            identifier: cell索引或ID
            content: 新内容
        """
        try:
            index = self._resolve_cell_identifier(identifier)
            if index is None:
                print(f"未找到cell: {identifier}")
                return False
            
            self.notebook.cells[index].source = content
            success = self._save_notebook()
            
            if success:
                self._sync_images_after_edit("edit", cell_index=index)
            
            return success
            
        except Exception as e:
            print(f"编辑cell失败: {e}")
            return False
    
    def delete_cell(self, identifier: str) -> bool:
        """
        删除cell
        
        Args:
            identifier: cell索引或ID
        """
        try:
            index = self._resolve_cell_identifier(identifier)
            if index is None:
                print(f"未找到cell: {identifier}")
                return False
            
            del self.notebook.cells[index]
            success = self._save_notebook()
            
            if success:
                self._sync_images_after_edit("delete", deleted_index=index)
            
            return success
            
        except Exception as e:
            print(f"删除cell失败: {e}")
            return False
    
    def move_cell(self, from_idx: int, to_idx: int) -> bool:
        """
        移动cell位置
        
        Args:
            from_idx: 源位置
            to_idx: 目标位置
        """
        try:
            if not (0 <= from_idx < len(self.notebook.cells)):
                print(f"无效的源位置: {from_idx}")
                return False
            
            # 移除cell
            cell = self.notebook.cells.pop(from_idx)
            
            # 调整目标位置
            to_idx = max(0, min(to_idx, len(self.notebook.cells)))
            
            # 插入到新位置
            self.notebook.cells.insert(to_idx, cell)
            
            success = self._save_notebook()
            
            if success:
                self._sync_images_after_edit("move", old_index=from_idx, new_index=to_idx)
            
            return success
            
        except Exception as e:
            print(f"移动cell失败: {e}")
            return False
    
    def copy_cell(self, from_idx: int, to_idx: int) -> bool:
        """
        复制cell到指定位置
        
        Args:
            from_idx: 源位置
            to_idx: 目标位置
        """
        try:
            if not (0 <= from_idx < len(self.notebook.cells)):
                print(f"无效的源位置: {from_idx}")
                return False
            
            # 复制cell
            source_cell = self.notebook.cells[from_idx]
            
            if source_cell.cell_type == 'code':
                new_cell = nbformat.v4.new_code_cell(source_cell.source)
            elif source_cell.cell_type == 'markdown':
                new_cell = nbformat.v4.new_markdown_cell(source_cell.source)
            else:
                new_cell = nbformat.v4.new_raw_cell(source_cell.source)
            
            # 调整目标位置
            to_idx = max(0, min(to_idx, len(self.notebook.cells)))
            
            # 插入到新位置
            self.notebook.cells.insert(to_idx, new_cell)
            
            success = self._save_notebook()
            
            if success:
                # 同步图片索引（插入操作）
                self._sync_images_after_edit("insert", inserted_index=to_idx)
            
            return success
            
        except Exception as e:
            print(f"复制cell失败: {e}")
            return False
    
    def convert_cell_type(self, identifier: str, target_type: str) -> bool:
        """
        转换cell类型
        
        Args:
            identifier: cell索引或ID
            target_type: 目标类型 ('code', 'markdown', 'raw')
        """
        try:
            index = self._resolve_cell_identifier(identifier)
            if index is None:
                print(f"未找到cell: {identifier}")
                return False
            
            cell = self.notebook.cells[index]
            content = cell.source
            
            # 创建新类型的cell
            if target_type == 'code':
                new_cell = nbformat.v4.new_code_cell(content)
            elif target_type == 'markdown':
                new_cell = nbformat.v4.new_markdown_cell(content)
            elif target_type == 'raw':
                new_cell = nbformat.v4.new_raw_cell(content)
            else:
                print(f"未知的cell类型: {target_type}")
                return False
            
            # 替换cell
            self.notebook.cells[index] = new_cell
            
            return self._save_notebook()
            
        except Exception as e:
            print(f"转换cell类型失败: {e}")
            return False
    
    def clear_cell_output(self, identifier: str) -> bool:
        """
        清空cell输出
        
        Args:
            identifier: cell索引或ID
        """
        try:
            index = self._resolve_cell_identifier(identifier)
            if index is None:
                print(f"未找到cell: {identifier}")
                return False
            
            cell = self.notebook.cells[index]
            if cell.cell_type == 'code':
                cell.outputs = []
                cell.execution_count = None
            
            success = self._save_notebook()
            
            # 清除输出时同步清理对应的图片
            if success:
                self._sync_images_after_edit("clear_output", cell_index=index)
            
            return success
            
        except Exception as e:
            print(f"清空输出失败: {e}")
            return False
    
    def clear_all_outputs(self) -> bool:
        """清空所有cell的输出"""
        try:
            for cell in self.notebook.cells:
                if cell.cell_type == 'code':
                    cell.outputs = []
                    cell.execution_count = None
            
            return self._save_notebook()
            
        except Exception as e:
            print(f"清空所有输出失败: {e}")
            return False
    
    def batch_delete_cells(self, indices: List[int]) -> bool:
        """
        批量删除cells
        
        Args:
            indices: 要删除的cell索引列表
        """
        try:
            # 记录实际删除的索引
            deleted_indices = []
            
            # 按逆序删除，避免索引变化
            for idx in sorted(set(indices), reverse=True):
                if 0 <= idx < len(self.notebook.cells):
                    del self.notebook.cells[idx]
                    deleted_indices.append(idx)
            
            success = self._save_notebook()
            
            if success and deleted_indices:
                # 批量同步图片索引
                self._sync_images_after_batch_delete(deleted_indices)
            
            return success
            
        except Exception as e:
            print(f"批量删除失败: {e}")
            return False
    
    def batch_clear_outputs(self, indices: List[int]) -> bool:
        """
        批量清空输出
        
        Args:
            indices: 要清空输出的cell索引列表
        """
        try:
            # 记录实际清空的索引
            cleared_indices = []
            
            for idx in indices:
                if 0 <= idx < len(self.notebook.cells):
                    cell = self.notebook.cells[idx]
                    if cell.cell_type == 'code':
                        cell.outputs = []
                        cell.execution_count = None
                        cleared_indices.append(idx)
            
            success = self._save_notebook()
            
            if success and cleared_indices:
                # 批量同步图片清理
                self._sync_images_after_batch_clear(cleared_indices)
            
            return success
            
        except Exception as e:
            print(f"批量清空输出失败: {e}")
            return False
    
    def batch_convert_cells(self, indices: List[int], target_type: str) -> bool:
        """
        批量转换cell类型
        
        Args:
            indices: 要转换的cell索引列表
            target_type: 目标类型
        """
        try:
            for idx in indices:
                if 0 <= idx < len(self.notebook.cells):
                    cell = self.notebook.cells[idx]
                    content = cell.source
                    
                    # 创建新类型的cell
                    if target_type == 'code':
                        new_cell = nbformat.v4.new_code_cell(content)
                    elif target_type == 'markdown':
                        new_cell = nbformat.v4.new_markdown_cell(content)
                    elif target_type == 'raw':
                        new_cell = nbformat.v4.new_raw_cell(content)
                    else:
                        continue
                    
                    # 替换cell
                    self.notebook.cells[idx] = new_cell
            
            return self._save_notebook()
            
        except Exception as e:
            print(f"批量转换失败: {e}")
            return False
    
    def get_cell_count(self) -> int:
        """获取cell总数"""
        return len(self.notebook.cells) if self.notebook else 0
    
    def get_cell_info(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        获取cell详细信息
        
        Args:
            identifier: cell索引或ID
        """
        try:
            index = self._resolve_cell_identifier(identifier)
            if index is None:
                return None
            
            cell = self.notebook.cells[index]
            
            return {
                'index': index,
                'id': get_cell_id(cell),
                'cell_type': cell.cell_type,
                'source': cell.source,
                'source_length': len(cell.source),
                'has_outputs': hasattr(cell, 'outputs') and len(cell.outputs) > 0,
                'execution_count': getattr(cell, 'execution_count', None),
                'metadata': cell.metadata if hasattr(cell, 'metadata') else {}
            }
            
        except Exception as e:
            print(f"获取cell信息失败: {e}")
            return None


# 全局函数，保持向后兼容
def create_blank_notebook(notebook_path: str) -> bool:
    """创建空白notebook（兼容函数）"""
    try:
        editor = NotebookEditor(notebook_path)
        return editor.create_notebook()
    except Exception as e:
        print(f"创建失败: {e}")
        return False


def edit_cell_content(notebook_path: str, identifier: str, content: str) -> bool:
    """编辑cell内容（兼容函数）"""
    try:
        editor = NotebookEditor(notebook_path)
        return editor.edit_cell(identifier, content)
    except Exception as e:
        print(f"编辑失败: {e}")
        return False


def delete_cell(notebook_path: str, identifier: str) -> bool:
    """删除cell（兼容函数）"""
    try:
        editor = NotebookEditor(notebook_path)
        return editor.delete_cell(identifier)
    except Exception as e:
        print(f"删除失败: {e}")
        return False


def insert_cell(notebook_path: str, position: int, cell_type: str, content: str) -> bool:
    """插入cell（兼容函数）"""
    try:
        editor = NotebookEditor(notebook_path)
        return editor.insert_cell(position, cell_type, content)
    except Exception as e:
        print(f"插入失败: {e}")
        return False


def move_cell(notebook_path: str, from_idx: int, to_idx: int) -> bool:
    """移动cell（兼容函数）"""
    try:
        editor = NotebookEditor(notebook_path)
        return editor.move_cell(from_idx, to_idx)
    except Exception as e:
        print(f"移动失败: {e}")
        return False


def copy_cell(notebook_path: str, from_idx: int, to_idx: int) -> bool:
    """复制cell（兼容函数）"""
    try:
        editor = NotebookEditor(notebook_path)
        return editor.copy_cell(from_idx, to_idx)
    except Exception as e:
        print(f"复制失败: {e}")
        return False


def convert_cell_type(notebook_path: str, identifier: str, target_type: str) -> bool:
    """转换cell类型（兼容函数）"""
    try:
        editor = NotebookEditor(notebook_path)
        return editor.convert_cell_type(identifier, target_type)
    except Exception as e:
        print(f"转换失败: {e}")
        return False


def clear_cell_output(notebook_path: str, identifier: str) -> bool:
    """清空cell输出（兼容函数）"""
    try:
        editor = NotebookEditor(notebook_path)
        return editor.clear_cell_output(identifier)
    except Exception as e:
        print(f"清空输出失败: {e}")
        return False


def batch_delete_cells(notebook_path: str, range_str: str) -> bool:
    """批量删除cells（兼容函数）"""
    try:
        from utils.helpers import parse_cell_range, resolve_cell_identifiers
        
        # 解析范围字符串，支持cell_id
        cell_identifiers = parse_cell_range(range_str)
        
        editor = NotebookEditor(notebook_path)
        # 将标识符解析为索引
        indices = resolve_cell_identifiers(editor.notebook, cell_identifiers)
        
        if not indices:
            print(f"错误: 没有找到有效的cell: {range_str}")
            return False
        
        return editor.batch_delete_cells(indices)
        
    except Exception as e:
        print(f"批量删除失败: {e}")
        return False


def batch_clear_outputs(notebook_path: str, range_str: str) -> bool:
    """批量清空输出（兼容函数）"""
    try:
        from utils.helpers import parse_cell_range, resolve_cell_identifiers
        
        # 解析范围字符串，支持cell_id
        cell_identifiers = parse_cell_range(range_str)
        
        editor = NotebookEditor(notebook_path)
        # 将标识符解析为索引
        indices = resolve_cell_identifiers(editor.notebook, cell_identifiers)
        
        if not indices:
            print(f"错误: 没有找到有效的cell: {range_str}")
            return False
        
        return editor.batch_clear_outputs(indices)
        
    except Exception as e:
        print(f"批量清空输出失败: {e}")
        return False


def batch_convert_cells(notebook_path: str, range_str: str, target_type: str) -> bool:
    """批量转换cell类型（兼容函数）"""
    try:
        from utils.helpers import parse_cell_range, resolve_cell_identifiers
        
        # 解析范围字符串，支持cell_id
        cell_identifiers = parse_cell_range(range_str)
        
        editor = NotebookEditor(notebook_path)
        # 将标识符解析为索引
        indices = resolve_cell_identifiers(editor.notebook, cell_identifiers)
        
        if not indices:
            print(f"错误: 没有找到有效的cell: {range_str}")
            return False
        
        return editor.batch_convert_cells(indices, target_type)
        
    except Exception as e:
        print(f"批量转换失败: {e}")
        return False


def get_cell_info(notebook_path: str, identifier: str) -> None:
    """获取并打印cell信息（兼容函数）"""
    try:
        editor = NotebookEditor(notebook_path)
        info = editor.get_cell_info(identifier)
        
        if info:
            print(f"📋 Cell [{info['index']}] 信息:")
            print(f"   ID: {info['id'] or '无'}")
            print(f"   类型: {info['cell_type']}")
            print(f"   代码长度: {info['source_length']} 字符")
            print(f"   有输出: {'是' if info['has_outputs'] else '否'}")
            print(f"   完整内容:")
            print(info['source'])
        else:
            print(f"❌ 未找到cell: {identifier}")
            
    except Exception as e:
        print(f"获取cell信息失败: {e}")