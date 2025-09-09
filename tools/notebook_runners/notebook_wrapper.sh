#!/bin/bash
# notebook_wrapper.sh - nb_runner.py的完整功能封装脚本
# 位置: tools/notebook_runners/notebook_wrapper.sh
# 
# 目的: 封装所有nb_runner.py的技术细节，提供统一的调用接口
# 使用: notebook_wrapper.sh <operation> <notebook_path> [additional_params...]

set -e

# 自动处理Windows编码问题
if [[ "$OS" == "Windows_NT" ]] || command -v powershell.exe &> /dev/null; then
    # 在Windows环境下，通过PowerShell设置控制台编码
    powershell.exe -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8" 2>/dev/null || true
    # 设置代码页为UTF-8
    cmd.exe /c "chcp 65001 >nul 2>&1" || true
fi

# 设置环境变量
export PYTHONIOENCODING=utf-8
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8

# nb_runner.py 脚本路径
NB_RUNNER="tools/notebook_runners/nb_runner.py"

# === 执行类操作封装 ===

# 执行所有cell
execute_all_cells() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --all --show-output
}

# 执行指定cells（支持批量、索引/ID/范围）
execute_specific_cells() {
    local notebook_path="$1"
    local cells="$2"
    python "$NB_RUNNER" "$notebook_path" --cells "$cells" --show-output
}

# === 查询类操作封装 ===

# 查看notebook结构
get_notebook_structure() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --status structure
}

# 查看执行状态
get_execution_status() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --status exec
}

# 获取执行状态（默认）
get_status() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --status
}

# 分析依赖关系
get_dependency_analysis() {
    local notebook_path="$1" 
    python "$NB_RUNNER" "$notebook_path" --status deps
}

# 查找错误cell
get_error_cells() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --status errors
}

# 获取所有状态信息
get_all_status() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --status all
}

# 获取cell信息
get_cell_info() {
    local notebook_path="$1"
    local cell_index="$2"
    if [[ "$cell_index" == "all" ]]; then
        python "$NB_RUNNER" "$notebook_path" --get all
    else
        python "$NB_RUNNER" "$notebook_path" --get "$cell_index"
    fi
}

# 获取cell输出信息
get_cell_output_only() {
    local notebook_path="$1"
    local cell_index="$2"
    python "$NB_RUNNER" "$notebook_path" --get "$cell_index" --output-only
}

# 搜索包含文本的cell
search_cells() {
    local notebook_path="$1"
    local search_text="$2"
    local case_sensitive="${3:-false}"
    
    if [[ "$case_sensitive" == "true" ]]; then
        python "$NB_RUNNER" "$notebook_path" --search "$search_text" --case-sensitive
    else
        python "$NB_RUNNER" "$notebook_path" --search "$search_text"
    fi
}

# === 编辑类操作封装 ===

# 创建notebook
create_notebook() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --create
}

# 从文件插入cell（核心功能 - 避免引号冲突）
insert_cell_from_file() {
    local notebook_path="$1"
    local position="$2"
    local cell_type="$3"
    local code_file="$4"
    
    if [[ ! -f "$code_file" ]]; then
        echo "错误: 代码文件不存在: $code_file" >&2
        return 1
    fi
    
    cat "$code_file" | python "$NB_RUNNER" "$notebook_path" --insert-cell "$position" "$cell_type" --code-stdin
}

# 从文件编辑cell
edit_cell_from_file() {
    local notebook_path="$1"
    local cell_index="$2"
    local code_file="$3"
    
    if [[ ! -f "$code_file" ]]; then
        echo "错误: 代码文件不存在: $code_file" >&2
        return 1
    fi
    
    cat "$code_file" | python "$NB_RUNNER" "$notebook_path" --edit-cell "$cell_index" --code-stdin
}

# 删除cell
delete_cell() {
    local notebook_path="$1"
    local cell_index="$2"
    python "$NB_RUNNER" "$notebook_path" --delete-cell "$cell_index"
}

# 移动cell
move_cell() {
    local notebook_path="$1"
    local from_index="$2"
    local to_index="$3"
    python "$NB_RUNNER" "$notebook_path" --move-cell "$from_index" "$to_index"
}

# 复制cell
copy_cell() {
    local notebook_path="$1"
    local from_index="$2"
    local to_index="$3"
    python "$NB_RUNNER" "$notebook_path" --copy-cell "$from_index" "$to_index"
}

# 转换cell类型
convert_cell_type() {
    local notebook_path="$1"
    local cell_index="$2"
    local new_type="$3"
    python "$NB_RUNNER" "$notebook_path" --convert-cell "$cell_index" "$new_type"
}

# 清空cell输出
clear_cell_output() {
    local notebook_path="$1"
    local cell_index="$2"
    python "$NB_RUNNER" "$notebook_path" --clear-output "$cell_index"
}

# === 批量操作封装 ===

# 批量删除cells
batch_delete_cells() {
    local notebook_path="$1"
    local cell_range="$2"
    
    python "$NB_RUNNER" "$notebook_path" --batch-delete "$cell_range"
}

# 批量清空输出
batch_clear_outputs() {
    local notebook_path="$1"
    local cell_range="$2"
    python "$NB_RUNNER" "$notebook_path" --batch-clear-outputs "$cell_range"
}

# 批量转换cell类型
batch_convert_cells() {
    local notebook_path="$1"
    local cell_range="$2"
    local new_type="$3"
    python "$NB_RUNNER" "$notebook_path" --batch-convert "$cell_range" "$new_type"
}

# === 备份管理封装 ===

# 创建备份
create_backup() {
    local notebook_path="$1"
    local description="$2"
    python "$NB_RUNNER" "$notebook_path" --backup "$description"
}

# 列出所有备份
list_backups() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --list-backups
}

# 恢复备份
restore_backup() {
    local notebook_path="$1"
    local backup_id="$2"
    python "$NB_RUNNER" "$notebook_path" --restore-backup "$backup_id"
}

# 删除备份
delete_backup() {
    local notebook_path="$1"
    local backup_id="$2"
    python "$NB_RUNNER" "$notebook_path" --delete-backup "$backup_id"
}

# 清理旧备份
cleanup_backups() {
    local notebook_path="$1"
    local keep_count="$2"
    python "$NB_RUNNER" "$notebook_path" --cleanup-backups "$keep_count"
}

# 显示备份信息
show_backup_info() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --backup-info
}

# === 图片管理封装 ===

# 同步图片状态
sync_images() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --sync-images
}

# 列出图片详情
list_images() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --list-images
}

# 获取存储信息
get_storage_info() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --storage-info
}

# === 预览模式管理封装 ===

# 进入预览模式
enter_preview_mode() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --enter-preview
}

# 退出预览模式
exit_preview_mode() {
    local notebook_path="$1"
    local action="${2:-discard}"  # 默认为discard
    
    if [[ "$action" == "keep" ]]; then
        python "$NB_RUNNER" "$notebook_path" --exit-preview keep
    else
        python "$NB_RUNNER" "$notebook_path" --exit-preview
    fi
}

# 查看预览状态
get_preview_status() {
    local notebook_path="$1"
    python "$NB_RUNNER" "$notebook_path" --preview-status
}

# === 统一调用接口 ===
main() {
    local operation="$1"
    shift  # 移除第一个参数
    
    case "$operation" in
        # 执行类
        "execute_all") execute_all_cells "$@" ;;
        "execute_cells") execute_specific_cells "$@" ;;
        
        # 查询类  
        "get_structure") get_notebook_structure "$@" ;;
        "get_status") get_status "$@" ;;
        "get_exec_status") get_execution_status "$@" ;;
        "get_dependencies") get_dependency_analysis "$@" ;;
        "get_errors") get_error_cells "$@" ;;
        "get_all_status") get_all_status "$@" ;;
        "get_cell") get_cell_info "$@" ;;
        "get_cell_output") get_cell_output_only "$@" ;;
        "search") search_cells "$@" ;;
        
        # 编辑类
        "create") create_notebook "$@" ;;
        "insert_cell_file") insert_cell_from_file "$@" ;;
        "edit_cell_file") edit_cell_from_file "$@" ;;
        "delete_cell") delete_cell "$@" ;;
        "move_cell") move_cell "$@" ;;
        "copy_cell") copy_cell "$@" ;;
        "convert_cell") convert_cell_type "$@" ;;
        "clear_output") clear_cell_output "$@" ;;
        
        # 批量操作
        "batch_delete") batch_delete_cells "$@" ;;
        "batch_clear_outputs") batch_clear_outputs "$@" ;;
        "batch_convert") batch_convert_cells "$@" ;;
        
        # 备份管理
        "backup") create_backup "$@" ;;
        "list_backups") list_backups "$@" ;;
        "restore") restore_backup "$@" ;;
        "delete_backup") delete_backup "$@" ;;
        "cleanup") cleanup_backups "$@" ;;
        "backup_info") show_backup_info "$@" ;;
        
        # 图片管理
        "sync_images") sync_images "$@" ;;
        "list_images") list_images "$@" ;;
        "storage_info") get_storage_info "$@" ;;
        
        # 预览模式管理
        "enter_preview") enter_preview_mode "$@" ;;
        "exit_preview") exit_preview_mode "$@" ;;
        "preview_status") get_preview_status "$@" ;;
        
        *)
            echo "错误: 未知操作 '$operation'"
            echo "使用方法: $0 <operation> <notebook_path> [additional_args...]"
            echo ""
            echo "可用操作:"
            echo "  执行类: execute_all, execute_cells"
            echo "  查询类: get_structure, get_status, get_exec_status, get_dependencies, get_errors, get_all_status, get_cell, get_cell_output, search"
            echo "  编辑类: create, insert_cell_file, edit_cell_file, delete_cell, move_cell, copy_cell, convert_cell, clear_output"
            echo "  批量操作: batch_delete, batch_clear_outputs, batch_convert"
            echo "  备份管理: backup, list_backups, restore, delete_backup, cleanup, backup_info"
            echo "  图片管理: sync_images, list_images, storage_info"
            echo "  预览模式: enter_preview, exit_preview, preview_status"
            echo ""
            echo "预览模式使用示例:"
            echo "  $0 enter_preview notebook.ipynb                    # 进入预览模式"
            echo "  $0 insert_cell_file notebook.ipynb 0 code cell.py  # [PREVIEW] 模式下插入cell"
            echo "  $0 exit_preview notebook.ipynb                     # 退出预览并丢弃更改(默认)"
            echo "  $0 exit_preview notebook.ipynb keep                # 退出预览并保留更改"
            echo "  $0 preview_status notebook.ipynb                   # 查看预览状态"
            echo ""
            echo "重要说明:"
            echo "  - 文件传递方式避免引号冲突，推荐用于Agent系统集成"
            echo "  - get_status: 获取默认详细状态，get_exec_status: 获取执行状态统计"
            echo "  - 预览模式提供完整的工作空间隔离，支持任意操作后选择保留/丢弃"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"