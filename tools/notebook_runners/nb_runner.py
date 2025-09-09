#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jupyter Notebook Runner Script
简化重构版本：去除过度设计，保持核心功能，完全向后兼容
"""

import sys
import os
import argparse

# 抑制IPython调试器警告，优化Agent体验
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'


def print_error_and_exit(message: str, exit_code: int = 1):
    """统一的错误输出和退出函数"""
    print(f"错误: {message}")
    sys.exit(exit_code)


# 导入重构后的核心模块
try:
    from core.notebook_executor import NotebookExecutor, run_entire_notebook
    from core.notebook_editor import NotebookEditor, create_blank_notebook, edit_cell_content, delete_cell, insert_cell, move_cell, copy_cell, convert_cell_type, clear_cell_output, batch_delete_cells, batch_clear_outputs, batch_convert_cells, get_cell_info
    from core.notebook_analyzer import NotebookAnalyzer, show_notebook_status, show_comprehensive_status
    from core.image_manager import ImageManager, save_notebook_images, list_notebook_images, clean_notebook_images
    from core.preview_manager import PreviewSessionManager
    from utils.notebook_io import NotebookIO, create_backup, list_backups, restore_backup, delete_backup, cleanup_old_backups, show_backup_info
    from utils.helpers import parse_cell_range, format_execution_result, resolve_cell_identifiers
except ImportError as e:
    print(f"模块导入失败: {e}")
    print("请检查新模块是否正确创建")
    sys.exit(1)


def main():
    # 设置输出编码，解决Windows gbk编码问题
    import sys
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
    
    parser = argparse.ArgumentParser(
        description='Jupyter Notebook Runner - 专为AnalysisExecutionAgent优化的智能执行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
核心功能分类:

  执行操作:
    --all --show-output                   # 执行所有cell
    --cells "0,1,2" --show-output         # 执行指定cell(支持批量)
  
  查询分析:
    --status [exec|structure|deps|errors|all]  # 状态查询
    --get [INDEX|ID|all]                       # 获取cell信息  
    --search "pattern"                          # 搜索(支持正则)
  
  编辑操作:
    --create                              # 创建空白notebook
    --edit-cell N --code-stdin            # 编辑cell(Here Document)
    --insert-cell N [TYPE] --code-stdin   # 插入cell(Here Document)
  
  批量操作:
    --batch-delete "1,3,5"    --batch-clear-outputs "1-10"
    --batch-convert "2-4" markdown
  
  备份管理:
    --backup "description"    --list-backups    --restore-backup ID

  预览模式:
    --enter-preview                       # 进入预览模式(自动备份)
    --exit-preview [keep]                 # 退出预览(默认discard，可选keep)
    --preview-status                      # 查看预览状态

附加选项:
  --show-output                         # 执行cell时在控制台显示输出结果
  --output-only                         # 配合--get使用，仅获取输出信息
  --code-stdin                          # 从标准输入读取代码内容(配合编辑操作)
  --case-sensitive                      # 搜索时大小写敏感

标准代码输入方式 (Here Document + stdin):
  cat <<'EOF' | python nb_runner.py notebook.ipynb --edit-cell 0 --code-stdin
  import pandas as pd
  data = {"name": ["Alice", "Bob"], "age": [25, 30]}
  df = pd.DataFrame(data)
  print('支持所有引号类型!')
  EOF

预览模式使用示例:
  python nb_runner.py notebook.ipynb --enter-preview           # 进入预览模式
  python nb_runner.py notebook.ipynb --insert-cell 0 --code-stdin  # [PREVIEW] 模式下操作
  python nb_runner.py notebook.ipynb --exit-preview            # 退出并丢弃更改
  python nb_runner.py notebook.ipynb --exit-preview keep       # 退出并保留更改

详细文档: tools/notebook_runners/README.md
        ''')
    parser.add_argument('notebook_path', help='Notebook文件路径')
    
    # 核心执行选项（保持向后兼容）
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument('--all', action='store_true', help='执行整个notebook')
    action_group.add_argument('--cells', type=str, help='执行指定cell(支持批量执行)，格式: "0,1,2" 或 "1-5" 或 "0,2-4,6"，支持数字索引和cell ID混合，如 "1c29d688,4896f9ab"')
    action_group.add_argument('--get', type=str, nargs='?', const='all', help='获取cell完整信息(内容+输出)，支持索引/ID/范围/混合格式')
    action_group.add_argument('--status', nargs='*', 
                             choices=['exec', 'structure', 'deps', 'errors', 'all'],
                             help='显示状态信息: exec(执行), structure(结构), deps(依赖), errors(错误), all(全部)')
    action_group.add_argument('--search', type=str, help='在所有cell内容和输出中搜索指定文本(支持正则表达式)')
    
    # 基础文件操作
    action_group.add_argument('--create', action='store_true', help='创建全新的空白notebook文件')
    
    # 编辑功能
    action_group.add_argument('--edit-cell', nargs=1, metavar='CELL_ID', help="编辑指定cell的内容，支持数字索引或cell ID，必须配合 --code-stdin 使用标准输入")
    action_group.add_argument('--delete-cell', type=str, help='删除指定cell，支持数字索引或cell ID')
    action_group.add_argument('--move-cell', nargs=2, metavar=('FROM', 'TO'), help='移动cell位置，支持数字索引或cell ID')
    action_group.add_argument('--insert-cell', nargs='+', metavar=('POS', '[TYPE]'), help="插入新cell，必须配合 --code-stdin 使用标准输入")
    action_group.add_argument('--copy-cell', nargs=2, metavar=('FROM', 'TO'), help='复制cell到指定位置，支持数字索引或cell ID')
    action_group.add_argument('--convert-cell', nargs=2, metavar=('CELL_ID', 'TYPE'), help='转换cell类型，支持数字索引或cell ID')
    action_group.add_argument('--clear-output', type=str, help='清空指定cell的输出，支持数字索引或cell ID')
    
    # 批量操作功能
    action_group.add_argument('--batch-delete', type=str, help='批量删除cell，格式: "1,2,3" 或 "1-5"，支持cell ID')
    action_group.add_argument('--batch-clear-outputs', type=str, help='批量清空输出，格式: "1,2,3" 或 "1-5"，支持cell ID')
    action_group.add_argument('--batch-convert', nargs=2, metavar=('RANGE', 'TYPE'), help='批量转换cell类型，支持cell ID')
    
    # 文件操作功能
    action_group.add_argument('--backup', nargs='?', const='', help='创建备份，可指定描述')
    action_group.add_argument('--list-backups', action='store_true', help='列出所有备份')
    action_group.add_argument('--restore-backup', type=str, help='恢复指定备份（使用备份ID）')
    action_group.add_argument('--delete-backup', type=str, help='删除指定备份（使用备份ID）')
    action_group.add_argument('--cleanup-backups', nargs='?', type=int, const=10, help='清理旧备份，保留最新N个（默认10个）')
    action_group.add_argument('--backup-info', action='store_true', help='显示备份基本信息')
    
    # 图片管理功能
    action_group.add_argument('--sync-images', action='store_true', help='强制全量同步图片状态（用于故障恢复）')
    action_group.add_argument('--list-images', action='store_true', help='查看已保存的图片详情')
    action_group.add_argument('--storage-info', action='store_true', help='显示存储统计信息')
    
    # 预览模式管理功能
    action_group.add_argument('--enter-preview', action='store_true', help='进入预览模式（自动创建备份）')
    action_group.add_argument('--exit-preview', nargs='?', const='discard', choices=['discard', 'keep'], help='退出预览模式，默认discard丢弃更改，可选keep保留更改')
    action_group.add_argument('--preview-status', action='store_true', help='查看当前预览模式状态')
    
    # 基础选项
    parser.add_argument('--show-output', action='store_true', help='执行cell时在控制台显示输出结果（配合--all, --cells使用）')
    parser.add_argument('--output-only', action='store_true', help='配合--get使用，仅获取输出信息，不显示源代码')
    parser.add_argument('--code-stdin', action='store_true', help='从标准输入读取代码内容，配合--edit-cell或--insert-cell使用Here Document格式')
    
    # 通用选项
    parser.add_argument('--case-sensitive', action='store_true', help='搜索时大小写敏感，配合--search使用')
    
    args = parser.parse_args()
    
    # 辅助函数：读取标准输入内容
    def read_code_from_stdin():
        """从标准输入读取代码内容，处理编码问题"""
        try:
            if sys.stdin.isatty():
                print_error_and_exit("--code-stdin 需要通过管道传入代码内容")
            
            # 更强的编码处理，优先使用buffer.read()避免编码问题
            content = None
            
            # 方法1: 尝试使用buffer读取（推荐方式）
            if hasattr(sys.stdin, 'buffer'):
                try:
                    raw_content = sys.stdin.buffer.read()
                    # 尝试UTF-8解码，失败则尝试其他编码
                    try:
                        content = raw_content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            # Windows下尝试GBK编码
                            content = raw_content.decode('gbk')
                        except UnicodeDecodeError:
                            # 最后使用errors='replace'处理
                            content = raw_content.decode('utf-8', errors='replace')
                except Exception as e:
                    print(f"Warning: buffer读取失败: {e}")
                    content = None
            
            # 方法2: 回退到普通读取
            if content is None:
                try:
                    content = sys.stdin.read()
                except UnicodeDecodeError as e:
                    print_error_and_exit(f"输入内容编码错误: {e}\n提示: 请确保输入内容使用UTF-8或系统默认编码")
            
            if not content or not content.strip():
                print_error_and_exit("从标准输入未读取到任何内容")
                
            return content.rstrip('\r\n')  # 移除末尾的换行符
            
        except Exception as e:
            print_error_and_exit(f"读取标准输入失败: {e}")
    
    # 验证--code-stdin的使用场景
    if args.code_stdin:
        if not (args.edit_cell or args.insert_cell):
            print_error_and_exit("--code-stdin 只能配合 --edit-cell 或 --insert-cell 使用")
    
    # 验证edit-cell和insert-cell必须配合code-stdin使用
    if args.edit_cell and not args.code_stdin:
        print_error_and_exit("--edit-cell 必须配合 --code-stdin 使用\n标准用法: cat <<'EOF' | python nb_runner.py notebook.ipynb --edit-cell N --code-stdin")
    
    if args.insert_cell and not args.code_stdin:
        print_error_and_exit("--insert-cell 必须配合 --code-stdin 使用\n标准用法: cat <<'EOF' | python nb_runner.py notebook.ipynb --insert-cell N [TYPE] --code-stdin")
    
    # 检查文件路径格式
    if not args.notebook_path.endswith('.ipynb'):
        print_error_and_exit(f"文件路径 {args.notebook_path} 不是有效的notebook文件格式 (.ipynb)")
    
    # 处理创建新文件的情况
    if args.create:
        if os.path.exists(args.notebook_path):
            print_error_and_exit(f"文件 {args.notebook_path} 已存在，无法创建")
        create_blank_notebook(args.notebook_path)
        print(f"✅ 成功创建空白notebook: {args.notebook_path}")
        return
    
    # 对于非创建模式，检查文件是否存在
    if not os.path.exists(args.notebook_path):
        print_error_and_exit(f"文件 {args.notebook_path} 不存在\n提示: 使用 --create 参数创建新文件")
    
    try:
        # 初始化预览会话管理器
        preview_manager = PreviewSessionManager(args.notebook_path)
        preview_indicator = preview_manager.get_preview_indicator()
        
        # 处理预览模式管理功能
        if args.enter_preview:
            result = preview_manager.enter_preview_mode()
            if result["success"]:
                print(f"✅ {result['message']}")
                print(f"   备份ID: {result['backup_id']}")
                print(f"   开始时间: {result['started_at']}")
                print(f"   现在可以在 [PREVIEW] 模式下进行任何操作")
            else:
                print(f"❌ 进入预览模式失败: {result['error']}")
                sys.exit(1)
            return
        elif args.exit_preview is not None:
            keep_changes = (args.exit_preview == 'keep')
            result = preview_manager.exit_preview_mode(keep_changes)
            if result["success"]:
                print(f"✅ {result['message']}")
                print(f"   预览持续时间: {result.get('started_at', 'N/A')}")
                print(f"   操作数量: {result.get('operations_count', 0)}")
            else:
                print(f"❌ 退出预览模式失败: {result['error']}")
                sys.exit(1)
            return
        elif args.preview_status:
            status = preview_manager.get_preview_status()
            if status["in_preview"]:
                print(f"📋 预览模式状态:")
                print(f"   状态: 预览模式运行中")
                print(f"   开始时间: {status.get('started_at', 'N/A')}")
                print(f"   运行时间: {status.get('duration', 'N/A')}")
                print(f"   备份ID: {status.get('backup_id', 'N/A')}")
                print(f"   执行操作数: {status.get('operations_count', 0)}")
                print(f"   描述: {status.get('description', 'N/A')}")
            else:
                print("📋 当前不在预览模式")
            return
        
        # 处理新增结构查询功能
        if args.get is not None:
            from core.notebook_analyzer import NotebookAnalyzer
            analyzer = NotebookAnalyzer(args.notebook_path)
            result = analyzer.get_cells_info(args.get, output_only=args.output_only)
            print(result)
            return
        elif args.status is not None:
            # 综合状态查询功能
            if len(args.status) == 0:
                # 默认显示执行状态
                from core.notebook_analyzer import show_notebook_status
                show_notebook_status(args.notebook_path)
            else:
                # 显示指定的状态信息
                show_comprehensive_status(args.notebook_path, args.status)
            return
        elif args.search:
            # 搜索功能
            from core.notebook_analyzer import search_notebook
            search_notebook(args.notebook_path, args.search, args.case_sensitive)
            return
        elif args.edit_cell:
            cell_identifier = args.edit_cell[0]
            content = read_code_from_stdin()
            
            # 记录预览操作日志
            preview_manager.log_operation("edit_cell", {
                "cell_identifier": cell_identifier,
                "content_length": len(content)
            })
            
            if edit_cell_content(args.notebook_path, cell_identifier, content):
                print(f"{preview_indicator}✅ Cell [{cell_identifier}] 编辑完成")
            return
        elif args.delete_cell is not None:
            # 记录预览操作日志
            preview_manager.log_operation("delete_cell", {
                "cell_identifier": args.delete_cell
            })
            
            if delete_cell(args.notebook_path, args.delete_cell):
                print(f"{preview_indicator}✅ Cell [{args.delete_cell}] 删除完成")
            return
        elif args.move_cell:
            from_identifier, to_identifier = args.move_cell
            
            # 记录预览操作日志
            preview_manager.log_operation("move_cell", {
                "from_identifier": from_identifier,
                "to_identifier": to_identifier
            })
            
            if move_cell(args.notebook_path, from_identifier, to_identifier):
                print(f"{preview_indicator}✅ Cell 从 [{from_identifier}] 移动到 [{to_identifier}] 完成")
            return
        elif args.insert_cell:
            # 验证插入位置参数
            try:
                pos = int(args.insert_cell[0])
            except (ValueError, IndexError):
                print_error_and_exit("插入位置必须是有效的数字")
            
            if pos < 0:
                print_error_and_exit("插入位置不能为负数")
            
            cell_type = args.insert_cell[1] if len(args.insert_cell) > 1 else 'code'
            
            # 验证cell类型
            if cell_type not in ['code', 'markdown', 'raw']:
                print_error_and_exit(f"不支持的cell类型: {cell_type}，仅支持: code, markdown, raw")
            
            content = read_code_from_stdin()
            
            # 记录预览操作日志
            preview_manager.log_operation("insert_cell", {
                "position": pos,
                "cell_type": cell_type,
                "content_length": len(content)
            })
            
            if insert_cell(args.notebook_path, pos, cell_type, content):
                print(f"{preview_indicator}✅ 在位置 [{pos}] 插入 {cell_type} Cell 完成")
            return
        elif args.copy_cell:
            from_identifier, to_identifier = args.copy_cell
            
            # 记录预览操作日志
            preview_manager.log_operation("copy_cell", {
                "from_identifier": from_identifier,
                "to_identifier": to_identifier
            })
            
            if copy_cell(args.notebook_path, from_identifier, to_identifier):
                print(f"{preview_indicator}✅ Cell 从 [{from_identifier}] 复制到 [{to_identifier}] 完成")
            return
        elif args.convert_cell:
            cell_identifier, target_type = args.convert_cell[0], args.convert_cell[1]
            
            # 记录预览操作日志
            preview_manager.log_operation("convert_cell", {
                "cell_identifier": cell_identifier,
                "target_type": target_type
            })
            
            if convert_cell_type(args.notebook_path, cell_identifier, target_type):
                print(f"{preview_indicator}✅ Cell [{cell_identifier}] 转换为 {target_type} 类型完成")
            return
        elif args.clear_output is not None:
            # 记录预览操作日志
            preview_manager.log_operation("clear_output", {
                "cell_identifier": args.clear_output
            })
            
            if clear_cell_output(args.notebook_path, args.clear_output):
                print(f"{preview_indicator}✅ Cell [{args.clear_output}] 输出清空完成")
            return
        
        # 处理批量操作功能
        elif args.batch_delete:
            # 记录预览操作日志
            preview_manager.log_operation("batch_delete", {
                "cell_range": args.batch_delete
            })
            
            if batch_delete_cells(args.notebook_path, args.batch_delete):
                print(f"{preview_indicator}✅ 批量删除操作完成")
            return
        elif args.batch_clear_outputs:
            # 记录预览操作日志
            preview_manager.log_operation("batch_clear_outputs", {
                "cell_range": args.batch_clear_outputs
            })
            
            if batch_clear_outputs(args.notebook_path, args.batch_clear_outputs):
                print(f"{preview_indicator}✅ 批量清空输出操作完成")
            return
        elif args.batch_convert:
            cell_range, target_type = args.batch_convert
            
            # 记录预览操作日志
            preview_manager.log_operation("batch_convert", {
                "cell_range": cell_range,
                "target_type": target_type
            })
            
            if batch_convert_cells(args.notebook_path, cell_range, target_type):
                print(f"{preview_indicator}✅ 批量转换类型操作完成")
            return
        
        # 处理备份管理功能
        elif args.backup is not None:
            description = args.backup if args.backup else None
            backup_id = create_backup(args.notebook_path, description)
            if backup_id:
                print(f"✅ 备份创建完成: {backup_id}")
            return
        elif args.list_backups:
            list_backups(args.notebook_path)
            return
        elif args.restore_backup:
            if restore_backup(args.notebook_path, args.restore_backup):
                print("✅ 备份恢复完成")
            return
        elif args.delete_backup:
            if delete_backup(args.notebook_path, args.delete_backup):
                print("✅ 备份删除完成")
            return
        elif args.cleanup_backups is not None:
            deleted_ids = cleanup_old_backups(args.notebook_path, args.cleanup_backups)
            if deleted_ids:
                print(f"✅ 清理完成，删除了 {len(deleted_ids)} 个旧备份")
            return
        elif args.backup_info:
            show_backup_info(args.notebook_path)
            return
        
        # 处理持久化存储功能
        elif args.sync_images:
            save_notebook_images(args.notebook_path)
            return
        elif args.list_images:
            list_notebook_images(args.notebook_path)
            return
        elif args.storage_info:
            # 显示存储统计信息
            manager = ImageManager(args.notebook_path)
            images_info = manager.list_images()
            print(f"📊 存储统计:")
            print(f"   图片cell数: {len(images_info)}")
            
            total_images = 0
            for info in images_info:
                total_images += len(info.get('images', []))
            
            print(f"   总图片数: {total_images}")
            return
        
        # 默认执行模式
        elif args.all:
            # 记录预览操作日志
            preview_manager.log_operation("execute_all", {})
            
            executor = NotebookExecutor(args.notebook_path)
            result = executor.execute_all(args.show_output)
            
            # 执行后自动同步图片
            try:
                image_manager = ImageManager(args.notebook_path)
                image_manager.sync_all_images(silent=True)
            except Exception as e:
                # 图片同步失败不影响主流程
                pass
            
            if not args.show_output:
                # 如果没有显示输出，则显示执行报告
                formatted_result = format_execution_result(result)
                print(f"{preview_indicator}{formatted_result}")
            else:
                print(f"{preview_indicator}执行完成")
            
            if 'error' in result or result.get('error_count', 0) > 0:
                sys.exit(1)
        elif args.cells:
            # 记录预览操作日志
            preview_manager.log_operation("execute_cells", {
                "cells": args.cells
            })
            
            # 使用统一的cell标识符解析
            from utils.helpers import parse_and_resolve_cells
            executor = NotebookExecutor(args.notebook_path)
            cell_indices = parse_and_resolve_cells(executor.notebook, args.cells)
            
            if not cell_indices:
                print_error_and_exit("没有找到有效的cell")
            
            result = executor.execute_cells(cell_indices, args.show_output)
            
            # 执行后自动同步图片
            try:
                image_manager = ImageManager(args.notebook_path)
                image_manager.sync_all_images(silent=True)
            except Exception as e:
                # 图片同步失败不影响主流程
                pass
            
            if not args.show_output:
                # 如果没有显示输出，则显示执行报告
                formatted_result = format_execution_result(result)
                print(f"{preview_indicator}{formatted_result}")
            else:
                print(f"{preview_indicator}执行完成")
            
            if 'error' in result or result.get('error_count', 0) > 0:
                sys.exit(1)
        else:
            # 默认运行整个notebook
            # 记录预览操作日志
            preview_manager.log_operation("execute_all_default", {})
            
            executor = NotebookExecutor(args.notebook_path)
            result = executor.execute_all(args.show_output)
            
            # 执行后自动同步图片
            try:
                image_manager = ImageManager(args.notebook_path)
                image_manager.sync_all_images(silent=True)
            except Exception as e:
                # 图片同步失败不影响主流程
                pass
            
            if not args.show_output:
                # 如果没有显示输出，则显示执行报告
                formatted_result = format_execution_result(result)
                print(f"{preview_indicator}{formatted_result}")
            else:
                print(f"{preview_indicator}执行完成")
            
            if 'error' in result or result.get('error_count', 0) > 0:
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"发生未预期的错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()