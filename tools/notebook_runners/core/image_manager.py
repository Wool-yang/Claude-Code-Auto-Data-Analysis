#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Manager Module - 简化版
专门处理notebook cell输出图片的持久化存储，保持原有核心功能
"""

import os
import json
import base64
import hashlib
import shutil
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import nbformat
from utils.helpers import get_cell_id

# 抑制调试警告
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'


class ImageManager:
    """简化的图片管理器，保持核心功能"""
    
    def __init__(self, notebook_path: str):
        self.notebook_path = Path(notebook_path).resolve()
        self.notebook_dir = self.notebook_path.parent
        self.notebook_name = self.notebook_path.stem
        
        # 存储目录
        self.storage_dir = self.notebook_dir / f".nb_storage_{self.notebook_name}"
        self.images_dir = self.storage_dir / "images"
        
        # 确保目录存在
        self._init_storage()
    
    def _init_storage(self):
        """初始化存储目录"""
        try:
            self.images_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"初始化存储目录失败: {e}")
            return False
    
    def _load_notebook(self) -> Optional[nbformat.NotebookNode]:
        """加载notebook文件"""
        try:
            if self.notebook_path.exists():
                with open(self.notebook_path, 'r', encoding='utf-8') as f:
                    return nbformat.read(f, as_version=4)
        except Exception as e:
            print(f"加载notebook失败: {e}")
        return None
    
    def _calculate_cell_hash(self, cell) -> str:
        """计算Cell内容的hash"""
        content = cell.source if hasattr(cell, 'source') else ''
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def extract_cell_images(self, cell: nbformat.NotebookNode, cell_index: int) -> List[Dict[str, Any]]:
        """从cell输出中提取图片数据"""
        images = []
        
        if cell.cell_type != 'code' or not hasattr(cell, 'outputs'):
            return images
        
        for output_idx, output in enumerate(cell.outputs):
            if output.output_type in ['execute_result', 'display_data']:
                if hasattr(output, 'data') and output.data:
                    # 检查图片格式
                    image_formats = {
                        'image/png': 'PNG',
                        'image/jpeg': 'JPEG', 
                        'image/jpg': 'JPG',
                        'image/gif': 'GIF',
                        'image/svg+xml': 'SVG'
                    }
                    
                    # 处理图片格式
                    for mime_type, format_name in image_formats.items():
                        if mime_type in output.data:
                            image_data = output.data[mime_type]
                            
                            # 计算数据hash
                            data_str = str(image_data) if not isinstance(image_data, str) else image_data
                            data_hash = hashlib.md5(data_str.encode()).hexdigest()[:12]
                            
                            images.append({
                                'output_index': output_idx,
                                'mime_type': mime_type,
                                'format': format_name,
                                'data': image_data,
                                'data_hash': data_hash,
                                'size_bytes': len(data_str)
                            })
        
        return images
    
    def save_cell_images(self, cell: nbformat.NotebookNode, cell_index: int) -> Dict[str, Any]:
        """保存cell的图片到持久化存储"""
        try:
            cell_id = get_cell_id(cell)
            content_hash = self._calculate_cell_hash(cell)
            
            # 创建cell图片目录
            cell_dir_name = f"cell_{cell_index}_{cell_id}" if cell_id else f"cell_{cell_index}"
            cell_dir = self.images_dir / cell_dir_name
            
            # 提取图片数据
            images = self.extract_cell_images(cell, cell_index)
            
            if not images:
                # 清理可能存在的旧目录
                if cell_dir.exists():
                    shutil.rmtree(cell_dir)
                    return {
                        'action': 'cleaned',
                        'cell_index': cell_index,
                        'cell_id': cell_id,
                        'message': '清理了无图片cell的目录'
                    }
                else:
                    return {
                        'action': 'skipped',
                        'cell_index': cell_index,
                        'cell_id': cell_id,
                        'message': 'cell无图片输出'
                    }
            
            # 检查是否需要更新
            cell_info_file = cell_dir / 'cell_info.json'
            need_update = True
            
            if cell_info_file.exists():
                try:
                    with open(cell_info_file, 'r', encoding='utf-8') as f:
                        old_info = json.load(f)
                    
                    # 比较content hash和图片数量
                    if (old_info.get('content_hash') == content_hash and 
                        len(old_info.get('images', [])) == len(images)):
                        
                        # 比较图片hash
                        old_hashes = set(img.get('data_hash') for img in old_info.get('images', []))
                        new_hashes = set(img['data_hash'] for img in images)
                        
                        if old_hashes == new_hashes:
                            need_update = False
                
                except (json.JSONDecodeError, IOError):
                    need_update = True
            
            if not need_update:
                return {
                    'action': 'unchanged',
                    'cell_index': cell_index,
                    'cell_id': cell_id,
                    'message': '图片无变化，跳过更新'
                }
            
            # 创建目录并保存图片
            cell_dir.mkdir(parents=True, exist_ok=True)
            
            saved_images = []
            
            for img_info in images:
                output_idx = img_info['output_index']
                format_name = img_info['format']
                image_data = img_info['data']
                
                # 确定文件扩展名
                ext_map = {
                    'PNG': '.png',
                    'JPEG': '.jpg',
                    'JPG': '.jpg', 
                    'GIF': '.gif',
                    'SVG': '.svg'
                }
                ext = ext_map.get(format_name, '.png')
                
                # 文件名
                filename = f"output_{output_idx}_{img_info['data_hash']}{ext}"
                file_path = cell_dir / filename
                
                # 保存图片数据
                if format_name in ['PNG', 'JPEG', 'JPG', 'GIF']:
                    try:
                        image_bytes = base64.b64decode(image_data)
                        with open(file_path, 'wb') as f:
                            f.write(image_bytes)
                    except Exception as e:
                        print(f"⚠️ 保存二进制图片失败: {e}")
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(str(image_data))
                else:
                    # SVG格式
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(str(image_data))
                
                saved_images.append({
                    'filename': filename,
                    'format': format_name,
                    'mime_type': img_info['mime_type'],
                    'size_bytes': img_info['size_bytes'],
                    'data_hash': img_info['data_hash'],
                    'file_path': str(file_path)
                })
            
            # 保存cell信息
            cell_info = {
                'cell_index': cell_index,
                'cell_id': cell_id,
                'content_hash': content_hash,
                'saved_at': datetime.now().isoformat(),
                'notebook_path': str(self.notebook_path),
                'images': saved_images
            }
            
            with open(cell_info_file, 'w', encoding='utf-8') as f:
                json.dump(cell_info, f, indent=2, ensure_ascii=False)
            
            return {
                'action': 'saved',
                'cell_index': cell_index,
                'cell_id': cell_id,
                'images_count': len(saved_images),
                'cell_dir': str(cell_dir),
                'cell_info': cell_info,  # 添加 cell_info 到返回结果
                'message': f'保存了 {len(saved_images)} 个图片'
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'cell_index': cell_index,
                'cell_id': get_cell_id(cell) if cell else None,
                'error': str(e),
                'message': f'保存图片失败: {e}'
            }
    
    def sync_all_images(self, notebook: Optional[nbformat.NotebookNode] = None, silent: bool = False) -> Dict[str, Any]:
        """同步所有cell的图片状态"""
        try:
            if notebook is None:
                notebook = self._load_notebook()
            
            if not notebook:
                return {'error': '无法加载notebook'}
            
            stats = {
                'total_cells': len(notebook.cells),
                'processed_cells': 0,
                'images_saved': 0,
                'images_unchanged': 0,  # 已存在且未变化的图片
                'images_cleaned': 0,
                'directories_removed': 0,
                'errors': 0,
                'actions': []
            }
            
            # 处理每个cell
            for i, cell in enumerate(notebook.cells):
                result = self.save_cell_images(cell, i)
                stats['actions'].append(result)
                stats['processed_cells'] += 1
                
                if result['action'] == 'saved':
                    # 统计保存的图片数量
                    stats['images_saved'] += result.get('images_count', 0)
                elif result['action'] == 'unchanged':
                    # 统计未变化的图片数量（需要读取现有的 cell_info.json）
                    try:
                        cell_dir_name = f"cell_{i}_{result.get('cell_id', '')}" if result.get('cell_id') else f"cell_{i}"
                        cell_dir = self.images_dir / cell_dir_name
                        cell_info_file = cell_dir / 'cell_info.json'
                        
                        if cell_info_file.exists():
                            with open(cell_info_file, 'r', encoding='utf-8') as f:
                                cell_info = json.load(f)
                            
                            images_count = len(cell_info.get('images', []))
                            stats['images_unchanged'] += images_count
                    except (json.JSONDecodeError, IOError, FileNotFoundError):
                        pass
                elif result['action'] == 'cleaned':
                    stats['images_cleaned'] += 1
                elif result['action'] == 'error':
                    stats['errors'] += 1
            
            # 清理孤立的图片目录
            valid_cell_indices = set(range(len(notebook.cells)))
            
            for cell_dir in self.images_dir.glob("cell_*"):
                if cell_dir.is_dir():
                    try:
                        dir_name = cell_dir.name
                        if dir_name.startswith('cell_'):
                            parts = dir_name.split('_')
                            if len(parts) >= 2 and parts[1].isdigit():
                                cell_idx = int(parts[1])
                                
                                if cell_idx not in valid_cell_indices:
                                    shutil.rmtree(cell_dir)
                                    stats['directories_removed'] += 1
                                    stats['actions'].append({
                                        'action': 'orphan_cleaned',
                                        'cell_index': cell_idx,
                                        'cell_dir': str(cell_dir),
                                        'message': f'清理孤立目录: {cell_dir.name}'
                                    })
                    except (ValueError, IndexError):
                        continue
            
            if not silent and stats['directories_removed'] > 0:
                print(f"🧹 自动清理了 {stats['directories_removed']} 个孤立的图片目录")
            
            return stats
            
        except Exception as e:
            return {
                'error': str(e),
                'message': f'同步图片失败: {e}'
            }
    
    def list_images(self) -> List[Dict[str, Any]]:
        """列出所有已保存的图片"""
        images_info = []
        
        try:
            if not self.images_dir.exists():
                return images_info
            
            for cell_dir in self.images_dir.glob("cell_*"):
                if cell_dir.is_dir():
                    cell_info_file = cell_dir / 'cell_info.json'
                    
                    if cell_info_file.exists():
                        try:
                            with open(cell_info_file, 'r', encoding='utf-8') as f:
                                cell_info = json.load(f)
                            
                            # 验证图片文件是否存在
                            valid_images = []
                            for img in cell_info.get('images', []):
                                img_path = cell_dir / img['filename']
                                img['file_exists'] = img_path.exists()
                                img['full_path'] = str(img_path)
                                valid_images.append(img)
                            
                            cell_info['images'] = valid_images
                            cell_info['cell_dir'] = str(cell_dir)
                            images_info.append(cell_info)
                            
                        except (json.JSONDecodeError, IOError):
                            # 元数据文件损坏，直接列出图片文件
                            image_files = [f for f in cell_dir.glob("*") 
                                         if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.json']]
                            
                            if image_files:
                                images_info.append({
                                    'cell_dir': str(cell_dir),
                                    'cell_index': None,
                                    'cell_id': None,
                                    'saved_at': None,
                                    'images': [{'filename': f.name, 'full_path': str(f), 
                                              'file_exists': True} for f in image_files],
                                    'metadata_missing': True
                                })
            
            # 按cell索引排序
            images_info.sort(key=lambda x: x.get('cell_index', 999) if x.get('cell_index') is not None else 999)
            
        except Exception as e:
            print(f"❌ 列出图片信息失败: {e}")
        
        return images_info
    
    def clean_cell_images(self, cell_index: int, cell_id: str = None) -> Dict[str, Any]:
        """清理指定cell的图片目录"""
        try:
            # 查找对应目录
            if cell_id:
                cell_dir = self.images_dir / f"cell_{cell_index}_{cell_id}"
                if not cell_dir.exists():
                    for existing_dir in self.images_dir.glob(f"cell_{cell_index}_*"):
                        cell_dir = existing_dir
                        break
            else:
                cell_dir = None
                for existing_dir in self.images_dir.glob(f"cell_{cell_index}_*"):
                    cell_dir = existing_dir
                    break
                
                if not cell_dir:
                    cell_dir = self.images_dir / f"cell_{cell_index}"
            
            if not cell_dir or not cell_dir.exists():
                return {
                    'action': 'not_found',
                    'cell_index': cell_index,
                    'cell_id': cell_id,
                    'message': '未找到对应的图片目录'
                }
            
            # 统计并删除
            files = list(cell_dir.glob("*"))
            file_count = len([f for f in files if f.is_file()])
            
            shutil.rmtree(cell_dir)
            
            return {
                'action': 'cleaned',
                'cell_index': cell_index,
                'cell_id': cell_id,
                'files_removed': file_count,
                'cell_dir': str(cell_dir),
                'message': f'清理了包含 {file_count} 个文件的图片目录'
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'cell_index': cell_index,
                'cell_id': cell_id,
                'error': str(e),
                'message': f'清理图片目录失败: {e}'
            }
    
    def handle_cell_deletion(self, deleted_index: int) -> Dict[str, Any]:
        """
        处理cell删除：删除对应图片，重命名后续图片索引
        
        Args:
            deleted_index: 被删除的cell索引
        
        Returns:
            处理结果
        """
        try:
            operations = []
            
            # 1. 删除被删除cell的图片目录
            deleted_dirs = []
            for cell_dir in self.images_dir.glob(f"cell_{deleted_index}_*"):
                if cell_dir.is_dir():
                    shutil.rmtree(cell_dir)
                    deleted_dirs.append(str(cell_dir))
                    operations.append(f"删除目录: {cell_dir.name}")
            
            # 也检查没有ID的目录
            simple_dir = self.images_dir / f"cell_{deleted_index}"
            if simple_dir.exists() and simple_dir.is_dir():
                shutil.rmtree(simple_dir)
                deleted_dirs.append(str(simple_dir))
                operations.append(f"删除目录: {simple_dir.name}")
            
            # 2. 重命名所有索引大于deleted_index的目录
            renamed_dirs = []
            for cell_dir in sorted(self.images_dir.glob("cell_*"), key=lambda x: x.name):
                if not cell_dir.is_dir():
                    continue
                
                dir_name = cell_dir.name
                if dir_name.startswith('cell_'):
                    parts = dir_name.split('_')
                    if len(parts) >= 2 and parts[1].isdigit():
                        current_index = int(parts[1])
                        
                        if current_index > deleted_index:
                            new_index = current_index - 1
                            if len(parts) >= 3:
                                # 有cell_id的情况：cell_5_abc -> cell_4_abc
                                new_name = f"cell_{new_index}_{'_'.join(parts[2:])}"
                            else:
                                # 没有cell_id的情况：cell_5 -> cell_4
                                new_name = f"cell_{new_index}"
                            
                            new_dir = cell_dir.parent / new_name
                            cell_dir.rename(new_dir)
                            renamed_dirs.append(f"{dir_name} -> {new_name}")
                            operations.append(f"重命名: {dir_name} -> {new_name}")
                            
                            # 更新目录内的cell_info.json
                            cell_info_file = new_dir / 'cell_info.json'
                            if cell_info_file.exists():
                                try:
                                    with open(cell_info_file, 'r', encoding='utf-8') as f:
                                        cell_info = json.load(f)
                                    
                                    cell_info['cell_index'] = new_index
                                    
                                    with open(cell_info_file, 'w', encoding='utf-8') as f:
                                        json.dump(cell_info, f, indent=2, ensure_ascii=False)
                                except (json.JSONDecodeError, IOError):
                                    pass
            
            return {
                'action': 'deletion_handled',
                'deleted_index': deleted_index,
                'deleted_dirs_count': len(deleted_dirs),
                'renamed_dirs_count': len(renamed_dirs),
                'operations': operations,
                'message': f'处理cell删除: 删除了{len(deleted_dirs)}个目录，重命名了{len(renamed_dirs)}个目录'
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'deleted_index': deleted_index,
                'error': str(e),
                'message': f'处理cell删除失败: {e}'
            }
    
    def handle_cell_insertion(self, inserted_index: int) -> Dict[str, Any]:
        """
        处理cell插入：重命名后续图片索引+1
        
        Args:
            inserted_index: 插入位置的索引
        
        Returns:
            处理结果
        """
        try:
            operations = []
            renamed_dirs = []
            
            # 重命名所有索引>=inserted_index的目录，从大到小处理避免冲突
            existing_dirs = []
            for cell_dir in self.images_dir.glob("cell_*"):
                if cell_dir.is_dir():
                    dir_name = cell_dir.name
                    if dir_name.startswith('cell_'):
                        parts = dir_name.split('_')
                        if len(parts) >= 2 and parts[1].isdigit():
                            current_index = int(parts[1])
                            if current_index >= inserted_index:
                                existing_dirs.append((current_index, cell_dir, parts))
            
            # 按索引从大到小排序，避免重命名冲突
            existing_dirs.sort(key=lambda x: x[0], reverse=True)
            
            for current_index, cell_dir, parts in existing_dirs:
                new_index = current_index + 1
                
                if len(parts) >= 3:
                    # 有cell_id的情况：cell_3_abc -> cell_4_abc
                    new_name = f"cell_{new_index}_{'_'.join(parts[2:])}"
                else:
                    # 没有cell_id的情况：cell_3 -> cell_4
                    new_name = f"cell_{new_index}"
                
                new_dir = cell_dir.parent / new_name
                cell_dir.rename(new_dir)
                renamed_dirs.append(f"{cell_dir.name} -> {new_name}")
                operations.append(f"重命名: {cell_dir.name} -> {new_name}")
                
                # 更新目录内的cell_info.json
                cell_info_file = new_dir / 'cell_info.json'
                if cell_info_file.exists():
                    try:
                        with open(cell_info_file, 'r', encoding='utf-8') as f:
                            cell_info = json.load(f)
                        
                        cell_info['cell_index'] = new_index
                        
                        with open(cell_info_file, 'w', encoding='utf-8') as f:
                            json.dump(cell_info, f, indent=2, ensure_ascii=False)
                    except (json.JSONDecodeError, IOError):
                        pass
            
            return {
                'action': 'insertion_handled',
                'inserted_index': inserted_index,
                'renamed_dirs_count': len(renamed_dirs),
                'operations': operations,
                'message': f'处理cell插入: 重命名了{len(renamed_dirs)}个目录'
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'inserted_index': inserted_index,
                'error': str(e),
                'message': f'处理cell插入失败: {e}'
            }
    
    def handle_cell_move(self, old_index: int, new_index: int) -> Dict[str, Any]:
        """
        处理cell移动：重新映射图片索引
        
        Args:
            old_index: 原始索引
            new_index: 新索引
        
        Returns:
            处理结果
        """
        try:
            if old_index == new_index:
                return {
                    'action': 'no_change',
                    'message': '索引未改变，无需处理'
                }
            
            operations = []
            
            # 1. 先处理移动的cell的目录
            moved_dirs = []
            temp_suffix = f"_temp_{int(time.time())}"
            
            # 找到old_index对应的目录并临时重命名
            for cell_dir in self.images_dir.glob(f"cell_{old_index}_*"):
                if cell_dir.is_dir():
                    temp_name = cell_dir.name + temp_suffix
                    temp_dir = cell_dir.parent / temp_name
                    cell_dir.rename(temp_dir)
                    moved_dirs.append((temp_dir, cell_dir.name.split('_')[2:]))  # 保存原来的ID部分
                    operations.append(f"临时重命名: {cell_dir.name} -> {temp_name}")
            
            # 也处理没有ID的目录
            simple_dir = self.images_dir / f"cell_{old_index}"
            if simple_dir.exists() and simple_dir.is_dir():
                temp_name = simple_dir.name + temp_suffix
                temp_dir = simple_dir.parent / temp_name
                simple_dir.rename(temp_dir)
                moved_dirs.append((temp_dir, []))  # 空列表表示没有ID
                operations.append(f"临时重命名: {simple_dir.name} -> {temp_name}")
            
            # 2. 处理中间受影响的cells
            if old_index < new_index:
                # 向后移动：old_index+1 到 new_index 的cells索引都要-1
                for i in range(old_index + 1, new_index + 1):
                    self._rename_cell_dir_index(i, i - 1, operations)
            else:
                # 向前移动：new_index 到 old_index-1 的cells索引都要+1
                for i in range(new_index, old_index):
                    self._rename_cell_dir_index(i, i + 1, operations)
            
            # 3. 最后处理移动的cell目录
            for temp_dir, id_parts in moved_dirs:
                if id_parts:
                    # 有ID的情况
                    final_name = f"cell_{new_index}_{'_'.join(id_parts)}"
                else:
                    # 没有ID的情况
                    final_name = f"cell_{new_index}"
                
                final_dir = temp_dir.parent / final_name
                temp_dir.rename(final_dir)
                operations.append(f"最终重命名: {temp_dir.name} -> {final_name}")
                
                # 更新cell_info.json
                cell_info_file = final_dir / 'cell_info.json'
                if cell_info_file.exists():
                    try:
                        with open(cell_info_file, 'r', encoding='utf-8') as f:
                            cell_info = json.load(f)
                        
                        cell_info['cell_index'] = new_index
                        
                        with open(cell_info_file, 'w', encoding='utf-8') as f:
                            json.dump(cell_info, f, indent=2, ensure_ascii=False)
                    except (json.JSONDecodeError, IOError):
                        pass
            
            return {
                'action': 'move_handled',
                'old_index': old_index,
                'new_index': new_index,
                'moved_dirs_count': len(moved_dirs),
                'operations': operations,
                'message': f'处理cell移动: 从索引{old_index}移动到{new_index}，处理了{len(moved_dirs)}个目录'
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'old_index': old_index,
                'new_index': new_index,
                'error': str(e),
                'message': f'处理cell移动失败: {e}'
            }
    
    def _rename_cell_dir_index(self, from_index: int, to_index: int, operations: List[str]):
        """重命名指定索引的目录"""
        # 处理有ID的目录
        for cell_dir in self.images_dir.glob(f"cell_{from_index}_*"):
            if cell_dir.is_dir():
                parts = cell_dir.name.split('_')
                if len(parts) >= 3:
                    new_name = f"cell_{to_index}_{'_'.join(parts[2:])}"
                    new_dir = cell_dir.parent / new_name
                    cell_dir.rename(new_dir)
                    operations.append(f"索引更新: {cell_dir.name} -> {new_name}")
                    
                    # 更新cell_info.json
                    cell_info_file = new_dir / 'cell_info.json'
                    if cell_info_file.exists():
                        try:
                            with open(cell_info_file, 'r', encoding='utf-8') as f:
                                cell_info = json.load(f)
                            
                            cell_info['cell_index'] = to_index
                            
                            with open(cell_info_file, 'w', encoding='utf-8') as f:
                                json.dump(cell_info, f, indent=2, ensure_ascii=False)
                        except (json.JSONDecodeError, IOError):
                            pass
        
        # 处理没有ID的目录
        simple_dir = self.images_dir / f"cell_{from_index}"
        if simple_dir.exists() and simple_dir.is_dir():
            new_dir = simple_dir.parent / f"cell_{to_index}"
            simple_dir.rename(new_dir)
            operations.append(f"索引更新: cell_{from_index} -> cell_{to_index}")
    
    def handle_cell_content_change(self, cell_index: int) -> Dict[str, Any]:
        """
        处理cell内容变更：主动同步当前cell的实际图片状态
        
        Args:
            cell_index: 变更的cell索引
        
        Returns:
            处理结果
        """
        try:
            # 加载notebook获取当前cell状态
            notebook = self._load_notebook()
            if not notebook or cell_index >= len(notebook.cells):
                return {
                    'action': 'error',
                    'cell_index': cell_index,
                    'message': '无法加载notebook或cell索引无效'
                }
            
            current_cell = notebook.cells[cell_index]
            
            # 主动同步：基于当前cell的实际输出状态更新图片
            result = self.save_cell_images(current_cell, cell_index)
            
            if result['action'] == 'saved':
                return {
                    'action': 'content_change_handled',
                    'cell_index': cell_index,
                    'images_count': result.get('images_count', 0),
                    'message': f'内容变更，同步了{result.get("images_count", 0)}个图片'
                }
            elif result['action'] == 'cleaned':
                return {
                    'action': 'content_change_handled',
                    'cell_index': cell_index,
                    'files_removed': 1,  # 表示清理了旧图片目录
                    'message': '内容变更，清理了无图片输出的cell目录'
                }
            elif result['action'] == 'unchanged':
                return {
                    'action': 'content_change_handled',
                    'cell_index': cell_index,
                    'files_removed': 0,
                    'message': '内容变更，但图片无需更新'
                }
            elif result['action'] == 'skipped':
                return {
                    'action': 'content_change_handled',
                    'cell_index': cell_index,
                    'files_removed': 0,
                    'message': '内容变更，cell无图片输出'
                }
            else:
                return result
                
        except Exception as e:
            return {
                'action': 'error',
                'cell_index': cell_index,
                'error': str(e),
                'message': f'处理cell内容变更失败: {e}'
            }
    
    def handle_batch_deletion(self, deleted_indices: List[int]) -> Dict[str, Any]:
        """
        处理批量删除后的索引更新
        
        Args:
            deleted_indices: 被删除的cell索引列表（应该是已排序的）
        
        Returns:
            处理结果
        """
        try:
            operations = []
            deleted_dirs_count = 0
            renamed_dirs_count = 0
            
            # 1. 删除被删除cell的图片目录（按逆序处理）
            for deleted_index in sorted(deleted_indices, reverse=True):
                deleted_dirs = []
                
                # 删除有ID的目录
                for cell_dir in self.images_dir.glob(f"cell_{deleted_index}_*"):
                    if cell_dir.is_dir():
                        shutil.rmtree(cell_dir)
                        deleted_dirs.append(str(cell_dir))
                        deleted_dirs_count += 1
                        operations.append(f"删除目录: {cell_dir.name}")
                
                # 删除没有ID的目录
                simple_dir = self.images_dir / f"cell_{deleted_index}"
                if simple_dir.exists() and simple_dir.is_dir():
                    shutil.rmtree(simple_dir)
                    deleted_dirs.append(str(simple_dir))
                    deleted_dirs_count += 1
                    operations.append(f"删除目录: {simple_dir.name}")
            
            # 2. 批量重命名所有受影响的目录
            # 构建索引映射表：old_index -> new_index
            index_mapping = {}
            deleted_set = set(deleted_indices)
            
            # 计算每个现存索引的新位置
            shift = 0
            max_index = max(deleted_indices) if deleted_indices else 0
            
            # 找到所有现存的目录并计算新索引
            existing_dirs = []
            for cell_dir in self.images_dir.glob("cell_*"):
                if cell_dir.is_dir():
                    dir_name = cell_dir.name
                    if dir_name.startswith('cell_'):
                        parts = dir_name.split('_')
                        if len(parts) >= 2 and parts[1].isdigit():
                            current_index = int(parts[1])
                            if current_index not in deleted_set:
                                # 计算新索引（减去之前所有被删除的索引数量）
                                new_index = current_index - len([d for d in deleted_indices if d < current_index])
                                if new_index != current_index:
                                    index_mapping[current_index] = new_index
                                    existing_dirs.append((current_index, new_index, cell_dir, parts))
            
            # 按当前索引从大到小排序，避免重命名冲突
            existing_dirs.sort(key=lambda x: x[0], reverse=True)
            
            # 执行重命名
            for current_index, new_index, cell_dir, parts in existing_dirs:
                if len(parts) >= 3:
                    # 有cell_id的情况：cell_5_abc -> cell_3_abc
                    new_name = f"cell_{new_index}_{'_'.join(parts[2:])}"
                else:
                    # 没有cell_id的情况：cell_5 -> cell_3
                    new_name = f"cell_{new_index}"
                
                new_dir = cell_dir.parent / new_name
                cell_dir.rename(new_dir)
                renamed_dirs_count += 1
                operations.append(f"重命名: {cell_dir.name} -> {new_name}")
                
                # 更新目录内的cell_info.json
                cell_info_file = new_dir / 'cell_info.json'
                if cell_info_file.exists():
                    try:
                        with open(cell_info_file, 'r', encoding='utf-8') as f:
                            cell_info = json.load(f)
                        
                        cell_info['cell_index'] = new_index
                        
                        with open(cell_info_file, 'w', encoding='utf-8') as f:
                            json.dump(cell_info, f, indent=2, ensure_ascii=False)
                    except (json.JSONDecodeError, IOError):
                        pass
            
            return {
                'action': 'batch_deletion_handled',
                'deleted_indices': deleted_indices,
                'deleted_dirs_count': deleted_dirs_count,
                'renamed_dirs_count': renamed_dirs_count,
                'operations': operations,
                'message': f'批量删除处理完成: 删除了{deleted_dirs_count}个目录，重命名了{renamed_dirs_count}个目录'
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'deleted_indices': deleted_indices,
                'error': str(e),
                'message': f'批量删除处理失败: {e}'
            }
    
    def handle_batch_clear_outputs(self, cleared_indices: List[int]) -> Dict[str, Any]:
        """
        处理批量清空输出对应的图片清理
        
        Args:
            cleared_indices: 清空输出的cell索引列表
        
        Returns:
            处理结果
        """
        try:
            operations = []
            cleaned_count = 0
            
            # 重新加载notebook获取当前状态
            notebook = self._load_notebook()
            if not notebook:
                return {
                    'action': 'error', 
                    'message': '无法加载notebook'
                }
            
            # 对每个清空输出的cell处理图片
            for cell_index in cleared_indices:
                if cell_index < len(notebook.cells):
                    cell = notebook.cells[cell_index]
                    result = self.save_cell_images(cell, cell_index)
                    
                    if result['action'] in ['cleaned', 'skipped']:
                        cleaned_count += 1
                        operations.append(f"Cell [{cell_index}]: {result['message']}")
                    elif result['action'] == 'error':
                        operations.append(f"Cell [{cell_index}] 处理失败: {result['message']}")
            
            return {
                'action': 'batch_clear_handled',
                'cleared_indices': cleared_indices,
                'cleaned_count': cleaned_count,
                'operations': operations,
                'message': f'批量清空输出处理完成: 处理了{cleaned_count}个cell的图片'
            }
            
        except Exception as e:
            return {
                'action': 'error',
                'cleared_indices': cleared_indices,
                'error': str(e),
                'message': f'批量清空输出处理失败: {e}'
            }


# 全局函数，保持向后兼容
def get_image_manager(notebook_path: str) -> ImageManager:
    """获取图片管理器实例"""
    return ImageManager(notebook_path)


def save_notebook_images(notebook_path: str) -> None:
    """保存notebook所有cell的图片"""
    manager = get_image_manager(notebook_path)
    stats = manager.sync_all_images()
    
    if 'error' in stats:
        print(f"❌ 同步图片失败: {stats['error']}")
        return
    
    print(f"📊 图片同步完成:")
    print(f"   处理cell数: {stats['processed_cells']}/{stats['total_cells']}")
    
    # 图片统计
    total_images = stats['images_saved'] + stats['images_unchanged']
    if total_images > 0:
        print(f"   📷 图片文件: {total_images} 个 (新保存: {stats['images_saved']}, 已存在: {stats['images_unchanged']})")
    
    # 清理统计
    if stats['images_cleaned'] > 0:
        print(f"   🧹 清理目录: {stats['images_cleaned']} 个")
    if stats['directories_removed'] > 0:
        print(f"   🗑️ 删除孤立目录: {stats['directories_removed']} 个")
    
    if stats['errors'] > 0:
        print(f"   ❌ 错误: {stats['errors']} 个")
    
    if total_images == 0:
        print(f"   ℹ️ 没有发现图片输出内容")


def list_notebook_images(notebook_path: str) -> None:
    """列出notebook的所有图片"""
    manager = get_image_manager(notebook_path)
    images_info = manager.list_images()
    
    if not images_info:
        print("📋 没有找到任何保存的图片")
        return
    
    print(f"🖼️  找到 {len(images_info)} 个cell的图片:")
    print()
    
    total_images = 0
    
    for cell_info in images_info:
        cell_idx = cell_info.get('cell_index', '?')
        cell_id = cell_info.get('cell_id', '无ID')
        saved_at = cell_info.get('saved_at', '未知时间')
        images = cell_info.get('images', [])
        
        if cell_info.get('metadata_missing'):
            print(f"⚠️  Cell [{cell_idx}] - 元数据缺失")
        else:
            print(f"📁 Cell [{cell_idx}] (ID: {cell_id}) - {saved_at}")
        
        for img in images:
            status = "✓" if img.get('file_exists', True) else "✗"
            size_mb = img.get('size_bytes', 0) / 1024 / 1024
            full_path = img.get('full_path', f"路径未知/{img['filename']}")
            
            print(f"   {status} 📷 {img['filename']} - {img.get('format', '未知格式')} - {size_mb:.2f}MB")
            print(f"      📍 路径: {full_path}")
            total_images += 1
        
        print()
    
    print(f"📊 总计: {total_images} 个图片文件")


def clean_notebook_images(notebook_path: str, cell_index: int = None) -> None:
    """清理notebook的图片"""
    manager = get_image_manager(notebook_path)
    
    if cell_index is not None:
        # 清理指定cell的图片
        result = manager.clean_cell_images(cell_index)
        
        if result['action'] == 'cleaned':
            print(f"✅ {result['message']}")
        elif result['action'] == 'not_found':
            print(f"ℹ️ {result['message']}")
        else:
            print(f"❌ {result['message']}")
    else:
        # 清理所有图片
        try:
            if manager.images_dir.exists():
                files_count = len(list(manager.images_dir.rglob("*")))
                shutil.rmtree(manager.images_dir)
                manager.images_dir.mkdir(exist_ok=True)
                print(f"✅ 清理完成，删除了所有图片文件 ({files_count} 个)")
            else:
                print("ℹ️ 图片目录不存在，无需清理")
        except Exception as e:
            print(f"❌ 清理失败: {e}")