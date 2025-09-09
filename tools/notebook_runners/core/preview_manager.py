#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览会话管理器
负责管理预览模式的状态、备份创建和恢复
"""

import json
import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from utils.notebook_io import NotebookIO


class PreviewSessionManager:
    """预览会话管理器"""
    
    def __init__(self, notebook_path: str):
        self.notebook_path = Path(notebook_path)
        self.notebook_name = self.notebook_path.stem
        self.notebook_dir = self.notebook_path.parent
        
        # 存储目录 - 复用现有结构
        self.storage_dir = self.notebook_dir / f".nb_storage_{self.notebook_name}"
        self.preview_session_file = self.storage_dir / ".preview_session.json"
        
        # 确保存储目录存在
        self.storage_dir.mkdir(exist_ok=True)
        
    def is_in_preview_mode(self) -> bool:
        """检查是否处于预览模式"""
        return self.preview_session_file.exists()
    
    def enter_preview_mode(self, description: str = None) -> Dict[str, Any]:
        """
        进入预览模式
        自动创建备份并记录预览会话状态，同时备份图片目录状态
        """
        if self.is_in_preview_mode():
            return {
                "success": False,
                "error": "已经处于预览模式，请先退出当前预览会话"
            }
            
        if not self.notebook_path.exists():
            return {
                "success": False,
                "error": f"Notebook文件不存在: {self.notebook_path}"
            }
        
        # 生成预览备份描述
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_description = description or f"预览模式开始备份_{timestamp}"
        
        # 创建预览起始备份
        backup_id = NotebookIO.create_backup(str(self.notebook_path), f"preview_start_{timestamp}")
        if not backup_id:
            return {
                "success": False,
                "error": "创建预览起始备份失败"
            }
        
        # 备份图片目录状态
        images_backup_result = self._backup_images_state(timestamp)
        if not images_backup_result["success"]:
            # 如果图片备份失败，清理已创建的notebook备份
            NotebookIO.delete_backup(str(self.notebook_path), backup_id)
            return {
                "success": False,
                "error": f"创建图片状态备份失败: {images_backup_result['error']}"
            }
        
        # 创建预览会话记录
        preview_session = {
            "started_at": datetime.now().isoformat(),
            "backup_id": backup_id,
            "description": backup_description,
            "images_backup": images_backup_result.get("backup_path"),
            "operations_log": []
        }
        
        try:
            with open(self.preview_session_file, 'w', encoding='utf-8') as f:
                json.dump(preview_session, f, indent=2, ensure_ascii=False)
                
            return {
                "success": True,
                "backup_id": backup_id,
                "started_at": preview_session["started_at"],
                "message": "成功进入预览模式"
            }
            
        except Exception as e:
            # 如果预览会话文件创建失败，清理备份
            NotebookIO.delete_backup(str(self.notebook_path), backup_id)
            return {
                "success": False,
                "error": f"创建预览会话失败: {str(e)}"
            }
    
    def exit_preview_mode(self, keep_changes: bool = False) -> Dict[str, Any]:
        """
        退出预览模式
        keep_changes=False: 丢弃所有更改（默认）
        keep_changes=True: 保留所有更改
        """
        if not self.is_in_preview_mode():
            return {
                "success": False,
                "error": "当前不在预览模式"
            }
        
        try:
            # 读取预览会话信息
            with open(self.preview_session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            backup_id = session_data.get("backup_id")
            images_backup_path = session_data.get("images_backup")
            started_at = session_data.get("started_at")
            operations_count = len(session_data.get("operations_log", []))
            
            if not keep_changes:
                # 默认行为：丢弃更改，恢复备份
                # 1. 恢复notebook备份
                if backup_id:
                    restore_result = NotebookIO.restore_backup(
                        str(self.notebook_path), 
                        backup_id
                    )
                    if not restore_result:
                        return {
                            "success": False,
                            "error": f"恢复预览起始备份失败: {backup_id}"
                        }
                
                # 2. 恢复图片状态备份
                if images_backup_path:
                    images_restore_result = self._restore_images_state(images_backup_path)
                    if not images_restore_result["success"]:
                        # 图片恢复失败，但不影响整体退出过程
                        print(f"⚠️ 图片状态恢复失败: {images_restore_result.get('message', '未知错误')}")
                
                # 删除预览起始备份（已恢复，无需保留）
                if backup_id:
                    NotebookIO.delete_backup(str(self.notebook_path), backup_id)
                
                # 删除图片状态备份
                if images_backup_path:
                    self._cleanup_images_backup(images_backup_path)
                
                message = f"预览模式已退出，丢弃了 {operations_count} 个操作的更改"
            else:
                # 保留更改：只删除预览起始备份，保留当前状态
                if backup_id:
                    NotebookIO.delete_backup(str(self.notebook_path), backup_id)
                
                # 删除图片状态备份（保留当前图片状态）
                if images_backup_path:
                    self._cleanup_images_backup(images_backup_path)
                
                message = f"预览模式已退出，保留了 {operations_count} 个操作的更改"
            
            # 删除预览会话文件
            self.preview_session_file.unlink()
            
            return {
                "success": True,
                "kept_changes": keep_changes,
                "operations_count": operations_count,
                "started_at": started_at,
                "message": message
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"退出预览模式失败: {str(e)}"
            }
    
    def get_preview_status(self) -> Dict[str, Any]:
        """获取预览模式状态信息"""
        if not self.is_in_preview_mode():
            return {
                "in_preview": False,
                "message": "当前不在预览模式"
            }
        
        try:
            with open(self.preview_session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            started_at = datetime.fromisoformat(session_data["started_at"])
            duration = datetime.now() - started_at
            operations_count = len(session_data.get("operations_log", []))
            
            return {
                "in_preview": True,
                "started_at": session_data["started_at"],
                "duration": str(duration).split('.')[0],  # 移除微秒
                "backup_id": session_data.get("backup_id"),
                "description": session_data.get("description"),
                "operations_count": operations_count,
                "message": f"预览模式运行中，已执行 {operations_count} 个操作"
            }
            
        except Exception as e:
            return {
                "in_preview": True,
                "error": f"读取预览状态失败: {str(e)}"
            }
    
    def log_operation(self, operation: str, details: Dict[str, Any] = None) -> bool:
        """记录预览模式下的操作"""
        if not self.is_in_preview_mode():
            return False
            
        try:
            with open(self.preview_session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # 添加操作记录
            operation_record = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "details": details or {}
            }
            
            session_data["operations_log"].append(operation_record)
            
            # 写回文件
            with open(self.preview_session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception:
            # 记录操作失败不应影响主要功能
            return False
    
    def _backup_images_state(self, timestamp: str) -> Dict[str, Any]:
        """
        备份图片目录状态
        
        Args:
            timestamp: 时间戳用于备份文件命名
            
        Returns:
            备份结果字典
        """
        try:
            from core.image_manager import ImageManager
            
            # 获取图片管理器
            image_mgr = ImageManager(str(self.notebook_path))
            images_dir = image_mgr.images_dir
            
            # 如果图片目录不存在，创建空备份记录
            if not images_dir.exists():
                return {
                    "success": True,
                    "backup_path": None,
                    "message": "无图片目录，创建空备份记录"
                }
            
            # 创建图片状态备份文件
            backup_filename = f"images_backup_{timestamp}.tar.gz"
            backup_path = self.storage_dir / backup_filename
            
            # 使用tar.gz压缩备份图片目录
            with tarfile.open(backup_path, 'w:gz') as tar:
                # 备份整个images目录
                if images_dir.exists():
                    tar.add(images_dir, arcname='images')
                
                # 创建备份元数据
                metadata = {
                    "backup_time": datetime.now().isoformat(),
                    "notebook_path": str(self.notebook_path),
                    "images_dir": str(images_dir),
                    "backup_type": "preview_images_state"
                }
                
                # 将元数据写入临时文件并添加到tar
                metadata_file = self.storage_dir / f"temp_metadata_{timestamp}.json"
                try:
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    tar.add(metadata_file, arcname='backup_metadata.json')
                finally:
                    # 清理临时文件
                    if metadata_file.exists():
                        metadata_file.unlink()
            
            return {
                "success": True,
                "backup_path": str(backup_path.relative_to(self.storage_dir)),
                "full_backup_path": str(backup_path),
                "message": f"图片状态备份完成: {backup_filename}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"图片状态备份失败: {e}"
            }
    
    def _restore_images_state(self, backup_path: str) -> Dict[str, Any]:
        """
        恢复图片目录状态
        
        Args:
            backup_path: 备份文件路径（相对于storage_dir）
            
        Returns:
            恢复结果字典
        """
        try:
            from core.image_manager import ImageManager
            
            # 获取完整备份路径
            if backup_path is None:
                return {
                    "success": True,
                    "message": "无需恢复图片状态（原本无图片目录）"
                }
            
            full_backup_path = self.storage_dir / backup_path
            if not full_backup_path.exists():
                return {
                    "success": False,
                    "error": f"备份文件不存在: {full_backup_path}",
                    "message": "图片状态恢复失败：备份文件缺失"
                }
            
            # 获取图片管理器和目标目录
            image_mgr = ImageManager(str(self.notebook_path))
            images_dir = image_mgr.images_dir
            
            # 如果当前存在图片目录，先备份（以防恢复失败）
            temp_backup = None
            if images_dir.exists():
                temp_backup = images_dir.parent / f"{images_dir.name}_temp_backup"
                if temp_backup.exists():
                    shutil.rmtree(temp_backup)
                shutil.move(str(images_dir), str(temp_backup))
            
            try:
                # 解压恢复备份
                with tarfile.open(full_backup_path, 'r:gz') as tar:
                    # 提取到临时目录
                    temp_extract = self.storage_dir / "temp_extract"
                    if temp_extract.exists():
                        shutil.rmtree(temp_extract)
                    
                    tar.extractall(temp_extract)
                    
                    # 移动images目录到正确位置
                    extracted_images = temp_extract / "images"
                    if extracted_images.exists():
                        # 确保父目录存在
                        images_dir.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(extracted_images), str(images_dir))
                    
                    # 清理临时目录
                    shutil.rmtree(temp_extract)
                
                # 恢复成功，删除临时备份
                if temp_backup and temp_backup.exists():
                    shutil.rmtree(temp_backup)
                
                return {
                    "success": True,
                    "message": "图片状态恢复成功"
                }
                
            except Exception as restore_error:
                # 恢复失败，尝试还原临时备份
                if temp_backup and temp_backup.exists():
                    if images_dir.exists():
                        shutil.rmtree(images_dir)
                    shutil.move(str(temp_backup), str(images_dir))
                
                return {
                    "success": False,
                    "error": str(restore_error),
                    "message": f"图片状态恢复失败，已回滚: {restore_error}"
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"图片状态恢复失败: {e}"
            }
    
    def _cleanup_images_backup(self, backup_path: str) -> bool:
        """
        清理图片状态备份文件
        
        Args:
            backup_path: 备份文件路径（相对于storage_dir）
            
        Returns:
            清理是否成功
        """
        try:
            if backup_path is None:
                return True  # 无备份文件，清理成功
            
            full_backup_path = self.storage_dir / backup_path
            if full_backup_path.exists():
                full_backup_path.unlink()
            
            return True
            
        except Exception:
            return False
    
    def get_preview_indicator(self) -> str:
        """获取预览模式标识符"""
        return "[PREVIEW] " if self.is_in_preview_mode() else ""