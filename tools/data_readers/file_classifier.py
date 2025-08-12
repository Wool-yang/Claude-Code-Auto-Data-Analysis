import os
import zipfile
import argparse
import json
from pathlib import Path

def has_images_in_excel(file_path):
    """检查Excel文件是否包含图片"""
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            namelist = z.namelist()
            # 检查是否有media文件夹或drawing文件
            has_media = any(f.startswith('xl/media/') for f in namelist)
            has_drawings = any(f.startswith('xl/drawings/drawing') and f.endswith('.xml') for f in namelist)
            return has_media or has_drawings
    except Exception:
        return False

def has_images_in_docx(file_path):
    """检查DOCX文件是否包含图片"""
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            namelist = z.namelist()
            return any(f.startswith('word/media/') for f in namelist)
    except Exception:
        return False

def classify_file(file_path):
    """
    分类文件为结构化或非结构化数据
    返回: {
        "file_path": str,
        "file_name": str,
        "extension": str, 
        "classification": "structured" | "unstructured",
        "reason": str,
        "recommended_script": str,
        "has_images": bool
    }
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    file_name = path.name
    
    result = {
        "file_path": str(file_path),
        "file_name": file_name,
        "extension": ext,
        "classification": None,
        "reason": "",
        "recommended_script": "",
        "has_images": False
    }
    
    # 明确的文档类型 -> 非结构化
    if ext in ['.md', '.markdown', '.doc', '.docx', '.pdf', '.txt']:
        if ext in ['.docx']:
            result["has_images"] = has_images_in_docx(file_path)
        
        # TXT文件需要进一步判断是否为分隔符数据文件
        if ext == '.txt':
            try:
                # 简单检查前几行是否像分隔符文件
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_lines = [f.readline().strip() for _ in range(3)]
                
                # 检查是否有明显的分隔符特征
                separators = [',', '\t', ';', '|']
                looks_like_csv = False
                for line in first_lines:
                    if line and any(sep in line for sep in separators):
                        sep_counts = [line.count(sep) for sep in separators]
                        if max(sep_counts) >= 2:  # 至少有2个相同分隔符
                            looks_like_csv = True
                            break
                
                if looks_like_csv:
                    result["classification"] = "structured"
                    result["reason"] = "TXT文件包含分隔符，判定为结构化数据"
                    result["recommended_script"] = "read_structured_data.py"
                else:
                    result["classification"] = "unstructured"
                    result["reason"] = "TXT文件为纯文本，判定为非结构化数据"
                    result["recommended_script"] = "document_parser.py"
                    
            except Exception as e:
                result["classification"] = "unstructured"
                result["reason"] = f"TXT文件读取失败，默认判定为非结构化数据: {e}"
                result["recommended_script"] = "document_parser.py"
        else:
            result["classification"] = "unstructured"
            result["reason"] = "文档类型文件"
            result["recommended_script"] = "document_parser.py"
    
    # 明确的数据文件 -> 结构化
    elif ext in ['.csv', '.tsv']:
        result["classification"] = "structured"
        result["reason"] = "纯数据文件，无图片"
        result["recommended_script"] = "read_structured_data.py"
        result["has_images"] = False
    
    # Excel文件需要检查是否包含图片
    elif ext in ['.xlsx', '.xls', '.xlsm']:
        has_images = has_images_in_excel(file_path)
        result["has_images"] = has_images
        
        if has_images:
            result["classification"] = "unstructured"
            result["reason"] = "Excel文件包含图片，判定为非结构化数据"
            result["recommended_script"] = "document_parser.py"
        else:
            result["classification"] = "structured"
            result["reason"] = "Excel文件为纯数据表格，无图片"
            result["recommended_script"] = "read_structured_data.py"
    
    # 未知文件类型 -> 尝试作为文档处理
    else:
        result["classification"] = "unstructured"
        result["reason"] = f"未知文件类型 {ext}，默认作为非结构化数据处理"
        result["recommended_script"] = "document_parser.py"
        result["has_images"] = False
    
    return result

def main():
    # 设置输出编码，参照read_structured_data.py的方式，在ArgumentParser之前设置
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
    
    parser = argparse.ArgumentParser(description="文件类型分类器")
    parser.add_argument('file_path', help='要分类的文件路径')
    parser.add_argument('--output', help='输出JSON文件路径（可选）')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file_path):
        error_result = {
            "file_path": args.file_path,
            "error": f"文件不存在 - {args.file_path}",
            "classification": "error"
        }
        output_json = json.dumps(error_result, ensure_ascii=False, indent=2)
        try:
            sys.stdout.buffer.write(output_json.encode('utf-8') + b"\n")
            sys.stdout.buffer.flush()
        except Exception:
            sys.stdout.write(output_json + "\n")
        return 1
    
    try:
        result = classify_file(args.file_path)
        
        # 输出结果
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
        
        # 使用与read_structured_data.py相同的输出方式
        try:
            sys.stdout.buffer.write(output_json.encode('utf-8', errors='replace') + b"\n")
            sys.stdout.buffer.flush()
        except Exception:
            try:
                sys.stdout.write(output_json + "\n")
                sys.stdout.flush()
            except Exception:
                pass
        
        # 如果指定了输出文件，保存结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
        
        return 0
        
    except Exception as e:
        error_result = {
            "file_path": args.file_path,
            "error": str(e),
            "classification": "error"
        }
        output_json = json.dumps(error_result, ensure_ascii=False, indent=2)
        try:
            sys.stdout.buffer.write(output_json.encode('utf-8', errors='replace') + b"\n")
            sys.stdout.buffer.flush()
        except Exception:
            sys.stdout.write(output_json + "\n")
        return 1

if __name__ == '__main__':
    exit(main())