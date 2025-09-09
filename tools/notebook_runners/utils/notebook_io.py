#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notebook IO Utils
处理notebook文件的读写、备份等IO操作
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import nbformat

# 抑制调试警告
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'


class NotebookIO:
    """Notebook文件IO管理器"""
    
    @staticmethod
    def create_notebook(path: str) -> bool:
        """创建空白notebook"""
        try:
            nb = nbformat.v4.new_notebook()
            notebook_path = Path(path)
            
            # 确保目录存在
            notebook_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(notebook_path, 'w', encoding='utf-8') as f:
                nbformat.write(nb, f)
            
            return True
        except Exception as e:
            print(f"创建notebook失败: {e}")
            return False
    
    @staticmethod
    def load_notebook(path: str) -> Optional[nbformat.NotebookNode]:
        """加载notebook文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return nbformat.read(f, as_version=4)
        except Exception as e:
            print(f"加载notebook失败: {e}")
            return None
    
    @staticmethod
    def save_notebook(notebook: nbformat.NotebookNode, path: str) -> bool:
        """保存notebook文件"""
        try:
            notebook_path = Path(path)
            notebook_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(notebook_path, 'w', encoding='utf-8') as f:
                nbformat.write(notebook, f)
            
            return True
        except Exception as e:
            print(f"保存notebook失败: {e}")
            return False
    
    @staticmethod
    def get_backup_dir(notebook_path: str) -> Path:
        """获取备份目录"""
        notebook_path = Path(notebook_path)
        backup_dir = notebook_path.parent / f".nb_storage_{notebook_path.stem}" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    @staticmethod
    def create_backup(notebook_path: str, description: str = None) -> Optional[str]:
        """
        创建备份
        
        Args:
            notebook_path: notebook文件路径
            description: 备份描述
        
        Returns:
            备份ID，失败时返回None
        """
        try:
            notebook_path = Path(notebook_path)
            
            if not notebook_path.exists():
                print(f"Notebook文件不存在: {notebook_path}")
                return None
            
            # 生成备份ID（时间戳）
            backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 获取备份目录
            backup_dir = NotebookIO.get_backup_dir(notebook_path)
            
            # 备份文件路径
            backup_file = backup_dir / f"{notebook_path.stem}_{backup_id}.ipynb"
            
            # 复制文件
            shutil.copy2(notebook_path, backup_file)
            
            # 创建备份信息文件
            backup_info = {
                'backup_id': backup_id,
                'original_file': str(notebook_path),
                'backup_file': str(backup_file),
                'created_at': datetime.now().isoformat(),
                'description': description or f"备份于 {backup_id}",
                'file_size': notebook_path.stat().st_size
            }
            
            info_file = backup_dir / f"{backup_id}_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            return backup_id
            
        except Exception as e:
            print(f"创建备份失败: {e}")
            return None
    
    @staticmethod
    def list_backups(notebook_path: str) -> List[Dict[str, Any]]:
        """列出所有备份"""
        try:
            backup_dir = NotebookIO.get_backup_dir(notebook_path)
            
            if not backup_dir.exists():
                return []
            
            backups = []
            
            # 查找所有备份信息文件
            for info_file in backup_dir.glob("*_info.json"):
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        backup_info = json.load(f)
                    
                    # 检查备份文件是否存在
                    backup_file = Path(backup_info['backup_file'])
                    backup_info['file_exists'] = backup_file.exists()
                    
                    if backup_info['file_exists']:
                        backup_info['current_size'] = backup_file.stat().st_size
                    
                    backups.append(backup_info)
                    
                except (json.JSONDecodeError, IOError, KeyError):
                    continue
            
            # 按创建时间排序（最新的在前）
            backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return backups
            
        except Exception as e:
            print(f"列出备份失败: {e}")
            return []
    
    @staticmethod
    def restore_backup(notebook_path: str, backup_id: str) -> bool:
        """
        恢复备份
        
        Args:
            notebook_path: 目标notebook路径
            backup_id: 备份ID
        """
        try:
            backup_dir = NotebookIO.get_backup_dir(notebook_path)
            
            # 查找备份信息
            info_file = backup_dir / f"{backup_id}_info.json"
            
            if not info_file.exists():
                print(f"备份信息不存在: {backup_id}")
                return False
            
            with open(info_file, 'r', encoding='utf-8') as f:
                backup_info = json.load(f)
            
            backup_file = Path(backup_info['backup_file'])
            
            if not backup_file.exists():
                print(f"备份文件不存在: {backup_file}")
                return False
            
            # 创建当前文件的自动备份
            current_backup_id = NotebookIO.create_backup(notebook_path, f"恢复前自动备份")
            if current_backup_id:
                print(f"✅ 已创建当前文件的自动备份: {current_backup_id}")
            
            # 恢复文件
            shutil.copy2(backup_file, notebook_path)
            
            print(f"✅ 成功恢复备份 {backup_id}")
            return True
            
        except Exception as e:
            print(f"恢复备份失败: {e}")
            return False
    
    @staticmethod
    def delete_backup(notebook_path: str, backup_id: str) -> bool:
        """删除指定备份"""
        try:
            backup_dir = NotebookIO.get_backup_dir(notebook_path)
            
            # 查找备份文件
            info_file = backup_dir / f"{backup_id}_info.json"
            
            if not info_file.exists():
                print(f"备份不存在: {backup_id}")
                return False
            
            with open(info_file, 'r', encoding='utf-8') as f:
                backup_info = json.load(f)
            
            backup_file = Path(backup_info['backup_file'])
            
            # 删除文件
            files_deleted = 0
            
            if backup_file.exists():
                backup_file.unlink()
                files_deleted += 1
            
            if info_file.exists():
                info_file.unlink()
                files_deleted += 1
            
            print(f"✅ 删除备份 {backup_id} ({files_deleted} 个文件)")
            return True
            
        except Exception as e:
            print(f"删除备份失败: {e}")
            return False
    
    @staticmethod
    def cleanup_old_backups(notebook_path: str, keep_count: int = 10) -> List[str]:
        """
        清理旧备份，保留最新的N个
        
        Args:
            notebook_path: notebook路径
            keep_count: 保留的备份数量
        
        Returns:
            被删除的备份ID列表
        """
        try:
            backups = NotebookIO.list_backups(notebook_path)
            
            if len(backups) <= keep_count:
                return []
            
            # 按时间排序，保留最新的
            backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 要删除的备份
            to_delete = backups[keep_count:]
            
            # 执行删除
            deleted_ids = []
            
            for backup in to_delete:
                backup_id = backup['backup_id']
                if NotebookIO.delete_backup(notebook_path, backup_id):
                    deleted_ids.append(backup_id)
            
            return deleted_ids
            
        except Exception as e:
            print(f"清理备份失败: {e}")
            return []


# 全局函数，保持向后兼容
def create_backup(notebook_path: str, description: str = None) -> Optional[str]:
    """创建备份（兼容函数）"""
    return NotebookIO.create_backup(notebook_path, description)


def list_backups(notebook_path: str) -> None:
    """列出备份（兼容函数）"""
    backups = NotebookIO.list_backups(notebook_path)
    
    if not backups:
        print("📋 没有找到任何备份")
        return
    
    print(f"📁 备份列表: {len(backups)} 个")
    print()
    
    for backup in backups:
        backup_id = backup['backup_id']
        created_at = backup.get('created_at', '未知时间')
        description = backup.get('description', '无描述')
        file_size = backup.get('current_size', backup.get('file_size', 0))
        file_exists = backup.get('file_exists', False)
        
        status = "✓" if file_exists else "✗"
        size_kb = file_size / 1024
        
        print(f"{status} {backup_id}")
        print(f"    时间: {created_at}")
        print(f"    描述: {description}")
        print(f"    大小: {size_kb:.1f} KB")
        print()


def restore_backup(notebook_path: str, backup_id: str) -> bool:
    """恢复备份（兼容函数）"""
    return NotebookIO.restore_backup(notebook_path, backup_id)


def delete_backup(notebook_path: str, backup_id: str) -> bool:
    """删除备份（兼容函数）"""
    return NotebookIO.delete_backup(notebook_path, backup_id)


def cleanup_old_backups(notebook_path: str, keep_count: int = 10) -> List[str]:
    """清理旧备份（兼容函数）"""
    return NotebookIO.cleanup_old_backups(notebook_path, keep_count)


def show_backup_info(notebook_path: str) -> None:
    """显示备份基本信息（兼容函数）"""
    try:
        backup_dir = NotebookIO.get_backup_dir(notebook_path)
        backups = NotebookIO.list_backups(notebook_path)
        
        total_size = sum(backup.get('current_size', backup.get('file_size', 0)) 
                        for backup in backups if backup.get('file_exists', False))
        
        print(f"📊 备份统计:")
        print(f"   备份目录: {backup_dir}")
        print(f"   备份数量: {len(backups)}")
        print(f"   总大小: {total_size / 1024 / 1024:.2f} MB")
        
        if backups:
            latest = backups[0]  # 已按时间排序
            print(f"   最新备份: {latest['backup_id']} ({latest.get('created_at', '未知时间')})")
        
    except Exception as e:
        print(f"获取备份信息失败: {e}")