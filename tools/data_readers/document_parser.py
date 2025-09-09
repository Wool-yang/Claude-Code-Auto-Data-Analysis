import os
import sys
import json
import zipfile
import argparse
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import chardet
import shutil
import string

try:
    import fitz  # pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# 调试输出控制标志
DEBUG_OUTPUT = False  # 设置为True可启用详细调试输出

def debug_print(*args, **kwargs):
    """条件调试输出函数"""
    if DEBUG_OUTPUT:
        print(*args, **kwargs)


if getattr(sys.stdout, 'encoding', None) != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass

def detect_encoding(path):
    """Detect file encoding using chardet"""
    try:
        with open(path, 'rb') as f:
            raw = f.read()
        result = chardet.detect(raw)
        if result and result.get('encoding'):
            return result['encoding']
        return 'utf-8'
    except Exception:
        return 'utf-8'

def escape_table_breaking_chars(text):
    """只转义会破坏Markdown表格结构的字符"""
    if not text:
        return ""
    
    text = str(text).strip()
    # 管道符 - 会破坏表格列分隔
    text = text.replace('|', '｜')
    # 换行符 - 会破坏表格行结构  
    text = text.replace('\n', ' ').replace('\r', ' ')
    # 合并多余空格
    text = ' '.join(text.split())
    
    return text

def read_text_file(path):
    """Read text file with encoding detection"""
    encoding = detect_encoding(path)
    try:
        with open(path, 'r', encoding=encoding) as f:
            text = f.read()
    except UnicodeDecodeError:
        # fallback to utf-8 with error handling
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
    
    return text


def create_images_directory(path, file_name):
    """创建图片存储目录的通用函数"""
    base_name = os.path.splitext(file_name)[0]
    raw_data_dir = os.path.dirname(path)
    descriptions_dir = os.path.join(os.path.dirname(raw_data_dir), "descriptions")
    intermediate_artifacts_dir = os.path.join(descriptions_dir, "intermediate_artifacts")
    images_dir = os.path.join(intermediate_artifacts_dir, f"{base_name}_images")
    os.makedirs(images_dir, exist_ok=True)
    return images_dir, base_name

def parse_markdown(path):
    """Parse markdown file"""
    text = read_text_file(path)
    return {
        "file_type": "markdown",
        "full_text": text,  # 统一使用full_text
        "text_length": len(text),
        "is_structured": False
    }

def parse_docx(path):
    """Parse DOCX file to extract full text content"""
    try:
        with zipfile.ZipFile(path, 'r') as z:
            # Extract main document text
            if 'word/document.xml' in z.namelist():
                doc_xml = z.read('word/document.xml')
                root = ET.fromstring(doc_xml)
                
                # Extract ALL text from all text nodes (full document)
                texts = []
                for elem in root.iter():
                    if elem.tag.endswith('}t') and elem.text:
                        texts.append(elem.text)
                    elif elem.tag.endswith('}br'):  # Line breaks
                        texts.append('\n')
                    elif elem.tag.endswith('}p'):  # Paragraphs
                        if texts and not texts[-1].endswith('\n'):
                            texts.append('\n')
                
                full_text = ''.join(texts)
                
                return {
                    "file_type": "docx",
                    "full_text": full_text,
                    "text_length": len(full_text),
                    "is_structured": False
                }
    except Exception as e:
        return {"file_type": "docx", "error": str(e), "is_structured": False}

def parse_doc(path):
    """Parse DOC file - try using antiword if available, otherwise basic text extraction"""
    try:
        # Try to use antiword if available (Linux/Unix tool)
        import subprocess
        result = subprocess.run(['antiword', path], capture_output=True, text=True)
        if result.returncode == 0:
            full_text = result.stdout
            return {
                "file_type": "doc",
                "full_text": full_text,
                "text_length": len(full_text),
                "is_structured": False
            }
    except Exception:
        pass
    
    # Fallback: try to extract text using basic methods
    try:
        # Try reading as binary and extracting readable text
        with open(path, 'rb') as f:
            data = f.read()
        # Extract printable ASCII text
        printable = set(string.printable)
        text = ''.join(filter(lambda x: x in printable, data.decode('latin1', errors='ignore')))
        
        return {
            "file_type": "doc",
            "full_text": text,
            "text_length": len(text),
            "is_structured": False,
            "extraction_method": "binary_fallback"
        }
    except Exception as e:
        return {"file_type": "doc", "error": str(e), "is_structured": False}



def parse_txt(path):
    """Parse TXT file - extract full content"""
    try:
        text = read_text_file(path)
        return {
            "file_type": "txt",
            "full_text": text,
            "text_length": len(text),
            "is_structured": False
        }
    except Exception as e:
        return {"file_type": "txt", "error": str(e), "is_structured": False}


def parse_pdf(path):
    """Parse PDF file - extract full text content and page information"""
    if not PYMUPDF_AVAILABLE:
        return {
            "file_type": "pdf", 
            "error": "pymupdf library not available. Install with: pip install pymupdf",
            "is_structured": False
        }
    
    try:
        doc = fitz.open(path)
        full_text = ""
        pages_info = []
        total_images = 0
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            
            # Extract text from page
            page_text = page.get_text()
            full_text += f"\n\n--- 第 {page_num + 1} 页 ---\n"
            full_text += page_text
            
            # Count images on this page
            page_images = page.get_images()
            page_image_count = len(page_images)
            total_images += page_image_count
            
            pages_info.append({
                "page_number": page_num + 1,
                "text_length": len(page_text),
                "image_count": page_image_count,
                "has_text": len(page_text.strip()) > 0
            })
        
        doc.close()
        
        # Clean up text
        full_text = full_text.strip()
        
        return {
            "file_type": "pdf",
            "full_text": full_text,
            "text_length": len(full_text),
            "page_count": len(pages_info),
            "total_images": total_images,
            "pages_info": pages_info,
            "is_structured": False
        }
        
    except Exception as e:
        return {"file_type": "pdf", "error": f"PDF parsing failed: {str(e)}", "is_structured": False}


def extract_images_from_pdf(path, output_dir):
    """Extract images from PDF file and save them to specified directory"""
    if not PYMUPDF_AVAILABLE:
        return []
    
    extracted_images = []
    
    try:
        doc = fitz.open(path)
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    # Get image data
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Generate filename
                    image_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                    image_path = os.path.join(output_dir, image_filename)
                    
                    # Save image
                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    
                    extracted_images.append({
                        'filename': image_filename,
                        'path': image_path,
                        'page_number': page_num + 1,
                        'image_index': img_index + 1,
                        'size_bytes': len(image_bytes),
                        'format': image_ext.upper()
                    })
                    
                except Exception as e:
                    print(f"Failed to extract image {img_index + 1} from page {page_num + 1}: {e}")
        
        doc.close()
        
    except Exception as e:
        print(f"Failed to extract images from PDF: {e}")
    
    return extracted_images



def extract_images_from_xlsx(z, namelist, output_dir, sheets_info=None):
    """Extract images from Excel file and save them to data source directory"""
    extracted_images = []
    
    # 显示Excel中所有可能与图片相关的文件
    image_related_files = [f for f in namelist if any(keyword in f.lower() for keyword in ['image', 'media', 'drawing', 'chart', 'picture'])]
    
    # Build mapping of drawing files to sheet names
    drawing_to_sheet = {}
    if sheets_info:
        # Parse worksheet relationship files to map drawings to sheets
        for sheet_info in sheets_info:
            sheet_path = sheet_info.get('path', '')
            sheet_name = sheet_info.get('name', '')
            
            # Get worksheet relationships
            sheet_rels_path = sheet_path.replace('xl/worksheets/', 'xl/worksheets/_rels/') + '.rels'
            if sheet_rels_path in namelist:
                try:
                    rels_xml = z.read(sheet_rels_path)
                    rels_root = ET.fromstring(rels_xml)
                    
                    for rel in rels_root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                        target = rel.attrib.get('Target')
                        if target and 'drawing' in target and target.endswith('.xml'):
                            # Handle relative paths correctly
                            if target.startswith('../drawings/'):
                                drawing_path = f"xl/drawings/{target[12:]}"  # Remove '../drawings/'
                            elif target.startswith('drawings/'):
                                drawing_path = f"xl/drawings/{target[9:]}"   # Remove 'drawings/'
                            elif target.startswith('../'):
                                drawing_path = f"xl/{target[3:]}"
                            elif not target.startswith('xl/'):
                                drawing_path = f"xl/drawings/{target}"
                            else:
                                drawing_path = target
                            drawing_to_sheet[drawing_path] = sheet_name
                except Exception as e:
                    print(f"Error parsing sheet relationships for {sheet_name}: {e}")
    
    # Find all drawing files - 扩展搜索范围
    drawing_files = [f for f in namelist if f.startswith('xl/drawings/') and f.endswith('.xml')]
    
    # 也搜索可能的图片文件，包括chart相关的
    potential_image_files = [f for f in namelist if any(ext in f.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.emf', '.wmf'])]
    
    for drawing_file in drawing_files:
        sheet_name = drawing_to_sheet.get(drawing_file, 'Unknown')
        
        try:
            # Parse drawing XML
            drawing_xml = z.read(drawing_file)
            droot = ET.fromstring(drawing_xml)
            
            # Get drawing relationship file
            drawing_basename = os.path.basename(drawing_file)
            drawing_rels_path = f"xl/drawings/_rels/{drawing_basename}.rels"
            
            if drawing_rels_path not in namelist:
                continue
                
            # Parse drawing relationships
            rels_xml = z.read(drawing_rels_path)
            rels_root = ET.fromstring(rels_xml)
            
            # Build mapping of rId to image paths
            rid_to_image = {}
            for rel in rels_root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                rid = rel.attrib.get('Id')
                target = rel.attrib.get('Target')
                rel_type = rel.attrib.get('Type', '')
                
                # 扩展image类型检查 - 不仅仅检查'image'字符串
                if rid and target and ('image' in rel_type.lower() or any(ext in target.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.emf', '.wmf'])):
                    # Convert relative path to full zip path
                    if not target.startswith('/'):
                        image_path = f"xl/drawings/{target}"
                    else:
                        image_path = target.lstrip('/')
                    rid_to_image[rid] = image_path
            
            
            # Find all anchors (image positions) - 支持所有锚点类型
            anchors = []
            anchors.extend(droot.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}oneCellAnchor'))
            anchors.extend(droot.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}twoCellAnchor'))
            anchors.extend(droot.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}absoluteAnchor'))
            
            anchor_type_counts = {}
            
            for i, anchor in enumerate(anchors):
                anchor_type = anchor.tag.split('}')[-1]  # 获取锚点类型
                anchor_type_counts[anchor_type] = anchor_type_counts.get(anchor_type, 0) + 1
                
                # 获取位置信息 - 改进的坐标处理逻辑
                row_idx, col_idx = None, None
                
                # 处理不同类型的锚点
                if anchor_type in ['oneCellAnchor', 'twoCellAnchor']:
                    from_elem = anchor.find('.//{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}from')
                    if from_elem is not None:
                        row_elem = from_elem.find('{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}row')
                        col_elem = from_elem.find('{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}col')
                        
                        if row_elem is not None and row_elem.text is not None:
                            # Excel 内部坐标是 0-based，但用户看到的是 1-based
                            # 保持与 Excel 用户界面一致的坐标系统
                            row_idx = int(row_elem.text) + 1  # 转换为 1-based 行号
                        if col_elem is not None and col_elem.text is not None:
                            col_idx = int(col_elem.text) + 1  # 转换为 1-based 列号
                        
                        
                elif anchor_type == 'absoluteAnchor':
                    # absoluteAnchor 没有单元格坐标，使用绝对位置进行智能估算
                    pos_elem = anchor.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}pos')
                    if pos_elem is not None:
                        x = int(pos_elem.attrib.get('x', '0'))
                        y = int(pos_elem.attrib.get('y', '0'))
                        
                        # 将绝对位置转换为大概的单元格位置
                        # EMU (English Metric Units) 转换：1 EMU = 1/914400 英寸
                        # 假设标准列宽约65像素，行高约20像素，1像素约9525 EMU
                        estimated_col = max(1, int(x / (9525 * 65)) + 1)  # 估算列号
                        estimated_row = max(1, int(y / (9525 * 20)) + 1)  # 估算行号
                        
                        # 限制在合理范围内
                        estimated_col = min(estimated_col, 50)  # 最大50列
                        estimated_row = min(estimated_row, 200)  # 最大200行
                        
                        row_idx, col_idx = estimated_row, estimated_col
                    else:
                        row_idx, col_idx = 1, 1  # 默认放在左上角
                else:
                    row_idx, col_idx = -4, -4  # 使用 -4 标识未知类型
                
                # Find the blip element that references the image - 扩展搜索
                blip_elems = anchor.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
                
                for blip in blip_elems:
                    embed_rid = blip.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    
                    if embed_rid and embed_rid in rid_to_image:
                        image_zip_path = rid_to_image[embed_rid]
                        
                        # Extract image to output directory
                        if image_zip_path in namelist:
                            try:
                                image_data = z.read(image_zip_path)
                                image_filename = os.path.basename(image_zip_path)
                                # Normalize path for Windows
                                output_path = os.path.normpath(os.path.join(output_dir, image_filename))
                                
                                # 修复：确保图片文件被正确写入，增强错误处理
                                try:
                                    # 确保输出目录存在
                                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                                    
                                    # 写入图片文件
                                    with open(output_path, 'wb') as img_file:
                                        img_file.write(image_data)
                                    
                                    # 验证文件是否成功写入
                                    if os.path.exists(output_path):
                                        actual_size = os.path.getsize(output_path)
                                        expected_size = len(image_data)
                                        
                                        if actual_size == expected_size and actual_size > 0:
                                            # 创建更详细的图片信息记录
                                            image_info = {
                                                'filename': image_filename,
                                                'path': output_path,
                                                'row': row_idx,
                                                'col': col_idx,
                                                'sheet_name': sheet_name,
                                                'drawing_file': drawing_file,
                                                'size_bytes': len(image_data),
                                                'anchor_type': anchor_type,
                                                'position_type': _classify_image_position(row_idx, col_idx, anchor_type)
                                            }
                                            
                                            # 添加绝对位置图片的额外信息
                                            if anchor_type == 'absoluteAnchor':
                                                pos_elem = anchor.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}pos')
                                                if pos_elem is not None:
                                                    image_info['absolute_x'] = pos_elem.attrib.get('x', '0')
                                                    image_info['absolute_y'] = pos_elem.attrib.get('y', '0')
                                            
                                            extracted_images.append(image_info)
                                        else:
                                            print(f"Warning: Image file size mismatch for {image_filename}: expected {expected_size}, got {actual_size}")
                                    else:
                                        print(f"Error: Image file not found after write: {output_path}")
                                        
                                except OSError as write_error:
                                    print(f"OS error writing image file {image_filename}: {write_error}")
                                except Exception as write_error:
                                    print(f"Unexpected error writing image file {image_filename}: {write_error}")
                                    
                            except Exception as e:
                                print(f"Failed to extract image {image_zip_path}: {e}")
                        else:
                            print(f"Warning: Image file NOT found in ZIP: {image_zip_path}")
                    else:
                        if embed_rid:
                            pass  # 图片引用不在关系映射中
                        else:
                            pass  # Blip元素缺少embed属性
                            
            # 输出锚点类型统计
                            
        except Exception as e:
            pass  # 处理drawing文件失败
            
    
    # 图片提取成功
    if len(extracted_images) > 0:
        print(f"Extracted {len(extracted_images)} images from Excel file")
    
    return extracted_images

def _classify_image_position(row_idx, col_idx, anchor_type):
    """分类图片位置类型"""
    if row_idx is None or col_idx is None:
        return "unknown_position"
    elif row_idx == -2 and col_idx == -2:
        return "absolute_position"
    elif row_idx == -3 and col_idx == -3:
        return "missing_position_info"
    elif row_idx == -4 and col_idx == -4:
        return "unknown_anchor_type"
    elif row_idx > 0 and col_idx > 0:
        return "cell_anchored"
    else:
        return "special_position"

def is_date_format(num_fmt_id, format_code=None):
    """判断numFmtId是否为日期格式
    
    Args:
        num_fmt_id: 数字格式ID
        format_code: 格式代码字符串（用于自定义格式）
    
    Returns:
        bool: 是否为日期格式
    """
    # Excel内置日期格式ID
    built_in_date_formats = {14, 15, 16, 17, 18, 19, 20, 21, 22}
    if num_fmt_id in built_in_date_formats:
        return True
    
    # 检查自定义日期格式（ID通常 >= 164）
    if format_code and num_fmt_id >= 164:
        return is_custom_date_format(format_code)
    
    return False

def is_custom_date_format(format_code):
    """判断自定义格式代码是否为日期格式"""
    if not format_code:
        return False
    
    # 日期格式通常包含这些符号
    date_indicators = [
        # 年份
        'yyyy', 'yy', 'y',
        # 月份  
        'mmmm', 'mmm', 'mm', 'm"月"', 'm',
        # 日期
        'dd', 'd"日"', 'd',
        # 时间
        'hh', 'h', 'mm', 'ss',
        # AM/PM
        'am/pm', 'a/p'
    ]
    
    format_lower = format_code.lower()
    
    # 检查是否包含日期相关的格式符号
    for indicator in date_indicators:
        if indicator.lower() in format_lower:
            return True
    
    return False

def parse_excel_styles(z, namelist):
    """解析Excel样式信息，返回日期格式的样式ID集合"""
    date_style_ids = set()
    
    if 'xl/styles.xml' in namelist:
        try:
            styles_xml = z.read('xl/styles.xml')
            styles_root = ET.fromstring(styles_xml)
            
            # 首先解析自定义数字格式，建立格式ID到格式代码的映射
            custom_formats = {}
            numfmts = styles_root.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}numFmts')
            if numfmts is not None:
                for numfmt in numfmts:
                    fmt_id = numfmt.attrib.get('numFmtId')
                    fmt_code = numfmt.attrib.get('formatCode')
                    if fmt_id and fmt_code:
                        custom_formats[int(fmt_id)] = fmt_code
            
            # 然后解析cellXfs获取样式到格式的映射
            cellxfs = styles_root.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}cellXfs')
            if cellxfs is not None:
                for idx, xf in enumerate(cellxfs):
                    num_fmt_id = xf.attrib.get('numFmtId')
                    if num_fmt_id:
                        fmt_id = int(num_fmt_id)
                        format_code = custom_formats.get(fmt_id)  # 获取自定义格式代码
                        
                        if is_date_format(fmt_id, format_code):
                            date_style_ids.add(idx)
        except Exception as e:
            pass  # Excel样式解析失败
    
    return date_style_ids

def parse_excel(path, images_by_original_position=None):
    """Parse Excel files (xlsx, xlsm, xls) - extract ALL rows and ALL columns
    
    Args:
        path: Excel file path
        images_by_original_position: Dictionary mapping original Excel coordinates to images
                                   Format: {"sheet_name_row_col": [image_objects]}
    
    Returns:
        Dictionary containing sheet data with coordinate mappings for image embedding
    """
    sheets = []
    file_ext = os.path.splitext(path)[1].lower()
    
    # If no images provided, use empty dictionary
    if images_by_original_position is None:
        images_by_original_position = {}
    
    # Check if it's a legacy xls file
    if file_ext == '.xls':
        # For legacy XLS files, we need different handling
        # Since they're not XML-based, we'll provide a fallback
        try:
            # Try to read as binary and provide basic info
            # Note: Full XLS parsing would require additional libraries like xlrd
            with open(path, 'rb') as f:
                file_size = len(f.read())
            
            return {
                'file_type': 'xls',
                'has_macros': True,  # XLS files can contain macros
                'sheets': [{
                    'sheet_name': '数据表',
                    'column_count': None,
                    'columns': [],
                    'sample_rows': [],
                    'note': 'XLS格式文件需要转换为XLSX格式以获得完整的结构化数据分析'
                }],
                'is_structured': False,
                'parsing_note': 'XLS文件解析受限，建议转换为XLSX格式'
            }
        except Exception as e:
            return {
                'file_type': 'xls',
                'has_macros': True,
                'sheets': None,
                'is_structured': False,
                'error': f'XLS文件读取失败: {str(e)}'
            }
    
    # For XLSX and XLSM files, use the existing XML-based parsing
    try:
        with zipfile.ZipFile(path, 'r') as z:
            namelist = z.namelist()
            # parse styles to identify date formats
            date_style_ids = parse_excel_styles(z, namelist)
            # parse sharedStrings
            shared = []
            if 'xl/sharedStrings.xml' in namelist:
                try:
                    data = z.read('xl/sharedStrings.xml')
                    sroot = ET.fromstring(data)
                    for si in sroot.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                        texts = []
                        for t in si.iter():
                            if isinstance(t.tag, str) and t.tag.split('}')[-1] == 't' and t.text:
                                texts.append(t.text)
                        shared.append(''.join(texts))
                except Exception:
                    shared = []
            # map sheet rIds to filenames using workbook.rels
            sheets_map = []
            try:
                wb_xml = z.read('xl/workbook.xml')
                rel_xml = z.read('xl/_rels/workbook.xml.rels')
                wbroot = ET.fromstring(wb_xml)
                relroot = ET.fromstring(rel_xml)
                id_to_target = {}
                for rel in relroot.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                    rid = rel.attrib.get('Id')
                    target = rel.attrib.get('Target')
                    if rid and target:
                        if not target.startswith('/'):
                            spath = 'xl/' + target
                        else:
                            spath = target.lstrip('/')
                        id_to_target[rid] = spath
                for sheet_elem in wbroot.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet'):
                    name = sheet_elem.attrib.get('name')
                    rid = sheet_elem.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                    if name and rid and rid in id_to_target:
                        sheets_map.append({'name': name, 'path': id_to_target[rid]})
            except Exception:
                sheets_map = []
            
            for s in sheets_map:
                sname = s.get('name')
                spath = s.get('path')
                all_rows = []  # Store ALL rows, not just sample
                header = []
                try:
                    if spath and spath in namelist:
                        data = z.read(spath)
                        sroot = ET.fromstring(data)
                        ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
                        
                        # Get all row elements and sort by row number to ensure correct order
                        rows_dict = {}
                        max_col = 0
                        
                        # First pass: collect all cell references and values
                        for r in sroot.findall('.//%srow' % ns):
                            row_num = int(r.attrib.get('r', '1')) - 1  # Convert to 0-based
                            row_vals = {}
                            
                            for c in r.findall('%sc' % ns):
                                # Get cell reference (like A1, B2, etc.)
                                cell_ref = c.attrib.get('r', '')
                                if cell_ref:
                                    # Convert cell reference to column index
                                    col_letters = ''.join([ch for ch in cell_ref if ch.isalpha()])
                                    col_idx = 0
                                    for i, ch in enumerate(reversed(col_letters)):
                                        col_idx += (ord(ch) - ord('A') + 1) * (26 ** i)
                                    col_idx -= 1  # Convert to 0-based
                                    max_col = max(max_col, col_idx)
                                    
                                    # Get cell value with improved processing
                                    ctype = c.attrib.get('t')
                                    v = c.find('%sv' % ns)
                                    val = None
                                    
                                    if v is not None and v.text is not None:
                                        if ctype == 's':  # Shared string
                                            try:
                                                idx = int(v.text)
                                                val = shared[idx] if idx < len(shared) else v.text
                                            except Exception:
                                                val = v.text
                                        else:
                                            val = v.text
                                            # Convert Excel date serial numbers based on cell style
                                            try:
                                                # Check if cell has date formatting style
                                                s_attr = c.attrib.get('s')  # Style ID
                                                if s_attr and int(s_attr) in date_style_ids:
                                                    # Cell is formatted as date, try conversion
                                                    if val and val.replace('.', '').isdigit():
                                                        serial_num = float(val)
                                                        if serial_num >= 1:  # Excel date serial numbers start from 1
                                                            # Excel epoch: 1899-12-30 (accounts for leap year bug)
                                                            excel_epoch = datetime(1899, 12, 30)
                                                            date_obj = excel_epoch + timedelta(days=int(serial_num))
                                                            val = f"{date_obj.year}-{date_obj.month:02d}-{date_obj.day:02d}"
                                            except (ValueError, OverflowError, TypeError):
                                                # If conversion fails, keep the original value
                                                pass
                                    else:
                                        # inlineStr
                                        is_el = c.find('%sis' % ns)
                                        if is_el is not None:
                                            t_el = is_el.find('%st' % ns)
                                            if t_el is not None and t_el.text is not None:
                                                val = t_el.text
                                    
                                    # Clean and normalize cell value to prevent markdown table issues
                                    if val is not None:
                                        # Use unified function to escape table-breaking characters
                                        val = escape_table_breaking_chars(val)
                                        
                                        # 修复：移除不必要的方括号转义，原始单元格文字不需要转义
                                        # val_str = val_str.replace('[', '\\[').replace(']', '\\]')
                                        # 保留其他可能冲突的Markdown字符的处理（如果需要）
                                        # val_str = val_str.replace('*', '\\*').replace('_', '\\_')
                                        # val_str = val_str.replace('`', '\\`').replace('#', '\\#')
                                        
                                        # Don't truncate content - keep full text
                                    
                                    row_vals[col_idx] = val
                            
                            rows_dict[row_num] = row_vals
                        
                        # 修复：改进空行空列过滤算法，先确保包含图片的行列被保留
                        if rows_dict:
                            max_row = max(rows_dict.keys())
                            
                            # 重新计算max_col，确保包含所有数据列
                            max_col = 0
                            for row_data in rows_dict.values():
                                if row_data:
                                    max_col = max(max_col, max(row_data.keys()) if row_data else 0)
                            
                            # 关键修复：在检测空行空列之前，先识别和保护所有图片位置
                            # Step 1: 收集该sheet的所有图片位置和扩展边界
                            images_positions_for_sheet = set()
                            image_protected_rows = set()
                            image_protected_cols = set()
                            
                            for pos_key in images_by_original_position.keys():
                                key_parts = pos_key.split('_')
                                if len(key_parts) >= 3 and key_parts[0] == sname:
                                    try:
                                        img_row = int(key_parts[1])
                                        img_col = int(key_parts[2])
                                        images_positions_for_sheet.add((img_row, img_col))
                                        
                                        # 扩展保护范围：保护图片周围的单元格
                                        for r in range(max(1, img_row-1), min(max_row+2, img_row+2)):
                                            image_protected_rows.add(r)
                                        for c in range(max(1, img_col-1), min(max_col+2, img_col+2)):
                                            image_protected_cols.add(c)
                                        
                                        # 更新边界以包含图片位置
                                        max_col = max(max_col, img_col+1)  # 稍微扩展边界
                                        
                                        # 记录调试信息但不输出
                                        images_positions_for_sheet.add((img_row, img_col))
                                    except ValueError:
                                        pass  # 跳过无效的位置格式
                            
                            # Step 2: 精准检测有内容的行列（包括文本和图片）
                            rows_with_content = set()  # 有内容的行
                            cols_with_content = set()  # 有内容的列
                            
                            # 首先强制包含所有图片保护的行列
                            rows_with_content.update(image_protected_rows)
                            cols_with_content.update(image_protected_cols)
                            
                            # 然后检查文本内容
                            for row_num in range(max_row + 1):
                                row_data = rows_dict.get(row_num, {})
                                for col_idx, val in row_data.items():
                                    if val is not None and str(val).strip():
                                        rows_with_content.add(row_num)
                                        cols_with_content.add(col_idx)
                            
                            # 最后确保所有原始图片位置都被强制标记为有内容
                            for pos_key in images_by_original_position.keys():
                                key_parts = pos_key.split('_')
                                if len(key_parts) >= 3 and key_parts[0] == sname:
                                    try:
                                        img_row = int(key_parts[1])
                                        img_col = int(key_parts[2])
                                        if img_row >= 1 and img_col >= 1:  # 只处理正常坐标
                                            rows_with_content.add(img_row)
                                            cols_with_content.add(img_col)
                                            # 同时保护周围的单元格
                                            if img_row > 1:
                                                rows_with_content.add(img_row - 1)
                                            if img_col > 1:
                                                cols_with_content.add(img_col - 1)
                                            # 图片位置已保护
                                    except ValueError:
                                        continue
                            
                            # 第二步：建立坐标映射系统和构建过滤后的数据
                            # 按顺序排列有内容的行列
                            sorted_content_rows = sorted(rows_with_content)
                            sorted_content_cols = sorted(cols_with_content)
                            
                            # 建立坐标映射表：原始坐标 -> 过滤后坐标
                            original_to_filtered_row = {}  # 行映射
                            original_to_filtered_col = {}  # 列映射
                            filtered_to_original_row = {}  # 反向行映射
                            filtered_to_original_col = {}  # 反向列映射
                            
                            # 构建行映射
                            for filtered_row_idx, original_row_num in enumerate(sorted_content_rows):
                                original_to_filtered_row[original_row_num] = filtered_row_idx
                                filtered_to_original_row[filtered_row_idx] = original_row_num
                            
                            # 构建列映射
                            for filtered_col_idx, original_col_num in enumerate(sorted_content_cols):
                                original_to_filtered_col[original_col_num] = filtered_col_idx
                                filtered_to_original_col[filtered_col_idx] = original_col_num
                            
                            # 只有在有内容时才进行过滤
                            if sorted_content_rows and sorted_content_cols:
                                for row_idx, original_row_num in enumerate(sorted_content_rows):
                                    row_data = rows_dict.get(original_row_num, {})
                                    row_list = []
                                    
                                    # 只包含有内容的列
                                    for original_col_num in sorted_content_cols:
                                        val = row_data.get(original_col_num)
                                        if val is None or val == 'None':
                                            cell_value = ''
                                        else:
                                            cell_value = str(val).strip()
                                        row_list.append(cell_value)
                                    
                                    all_rows.append(row_list)
                                    
                                # 将坐标映射信息和转换后的图片位置保存以供后续使用
                                # 构建转换后的图片位置映射
                                transformed_images_by_position = {}
                                transform_debug_info = []
                                
                                # 再次检查所有图片的原始位置是否都在映射表中
                                missing_mappings = []
                                for pos_key in images_by_original_position.keys():
                                    key_parts = pos_key.split('_')
                                    if len(key_parts) >= 3 and key_parts[0] == sname:
                                        try:
                                            original_row = int(key_parts[1])
                                            original_col = int(key_parts[2])
                                            
                                            # 检查是否在映射表中
                                            if original_row not in original_to_filtered_row:
                                                missing_mappings.append(f"Row {original_row}")
                                                # 强制添加到映射表
                                                rows_with_content.add(original_row)
                                                sorted_content_rows = sorted(rows_with_content)
                                                # 重建行映射
                                                original_to_filtered_row.clear()
                                                filtered_to_original_row.clear()
                                                for filtered_row_idx, original_row_num in enumerate(sorted_content_rows):
                                                    original_to_filtered_row[original_row_num] = filtered_row_idx
                                                    filtered_to_original_row[filtered_row_idx] = original_row_num
                                                    
                                            if original_col not in original_to_filtered_col:
                                                missing_mappings.append(f"Col {original_col}")
                                                # 强制添加到映射表
                                                cols_with_content.add(original_col)
                                                sorted_content_cols = sorted(cols_with_content)
                                                # 重建列映射
                                                original_to_filtered_col.clear()
                                                filtered_to_original_col.clear()
                                                for filtered_col_idx, original_col_num in enumerate(sorted_content_cols):
                                                    original_to_filtered_col[original_col_num] = filtered_col_idx
                                                    filtered_to_original_col[filtered_col_idx] = original_col_num
                                                    
                                        except ValueError:
                                            continue
                                
                                if missing_mappings:
                                    print(f"DEBUG: Fixed missing mappings for {missing_mappings}")
                                
                                for pos_key in images_by_original_position.keys():
                                    key_parts = pos_key.split('_')
                                    if len(key_parts) >= 3 and key_parts[0] == sname:
                                        try:
                                            original_row = int(key_parts[1])
                                            original_col = int(key_parts[2])
                                            
                                            # 转换坐标到过滤后的表格位置
                                            if original_row in original_to_filtered_row and original_col in original_to_filtered_col:
                                                filtered_row = original_to_filtered_row[original_row]
                                                filtered_col = original_to_filtered_col[original_col]
                                                new_pos_key = f"{sname}_{filtered_row}_{filtered_col}"
                                                transformed_images_by_position[new_pos_key] = images_by_original_position[pos_key]
                                                
                                                # 记录转换详情
                                                for img in images_by_original_position[pos_key]:
                                                    transform_debug_info.append({
                                                        'filename': img['filename'],
                                                        'original_pos': pos_key,
                                                        'transformed_pos': new_pos_key,
                                                        'original_coords': f"({original_row},{original_col})",
                                                        'filtered_coords': f"({filtered_row},{filtered_col})"
                                                    })
                                                
                                                # 图片位置转换成功
                                            else:
                                                # 记录无法映射的图片
                                                for img in images_by_original_position[pos_key]:
                                                    transform_debug_info.append({
                                                        'filename': img['filename'],
                                                        'original_pos': pos_key,
                                                        'transformed_pos': 'UNMAPPABLE',
                                                        'original_coords': f"({original_row},{original_col})",
                                                        'filtered_coords': 'N/A',
                                                        'reason': f'Original row {original_row} or col {original_col} not in filtered coordinates'
                                                    })
                                                
                                                # 图片无法映射到过滤后的坐标
                                        except ValueError:
                                            pass
                                
                                
                                coordinate_mappings = {
                                    'original_to_filtered_row': original_to_filtered_row,
                                    'original_to_filtered_col': original_to_filtered_col,
                                    'filtered_to_original_row': filtered_to_original_row,
                                    'filtered_to_original_col': filtered_to_original_col,
                                    'sorted_content_rows': sorted_content_rows,
                                    'sorted_content_cols': sorted_content_cols,
                                    'transformed_images_by_position': transformed_images_by_position  # 新增：转换后的图片位置
                                }
                            else:
                                # 没有找到内容，创建空sheet
                                coordinate_mappings = None
                        
                        if all_rows:
                            header = all_rows[0] if all_rows else []
                            data_rows = all_rows[1:] if len(all_rows) > 1 else []
                        else:
                            header = []
                            data_rows = []
                        
                        sheets.append({
                            'sheet_name': sname, 
                            'column_count': len(header), 
                            'columns': header, 
                            'sample_rows': data_rows,  # Actually ALL rows now
                            'all_rows': all_rows,  # Complete data including headers
                            'coordinate_mappings': coordinate_mappings  # 新增：坐标映射信息
                        })
                    else:
                        sheets.append({'sheet_name': sname, 'column_count': None, 'columns': [], 'sample_rows': []})
                except Exception as e:
                    print(f"Error parsing sheet {sname}: {e}")
                    sheets.append({'sheet_name': sname, 'column_count': None, 'columns': [], 'sample_rows': []})
            # Detect file type and macro presence
            file_ext = os.path.splitext(path)[1].lower()
            has_macros = file_ext in ['.xlsm', '.xls']
            file_type = file_ext.lstrip('.')
            
            return {'file_type': file_type, 'has_macros': has_macros, 'sheets': sheets, 'is_structured': False}  # Changed to False for non-structured context
    except Exception as e:
        # Get file extension for error reporting
        file_ext = os.path.splitext(path)[1].lower()
        file_type = file_ext.lstrip('.')
        has_macros = file_ext in ['.xlsm', '.xls']
        return {'file_type': file_type, 'has_macros': has_macros, 'sheets': None, 'is_structured': False, 'error': str(e)}


def analyze_image_content(filename, image_path=None):
    """
    分析图片内容并生成简洁描述
    优先使用AI视觉模型，失败时回退到文件名
    修复：简化重试逻辑 - 失败后无条件重试一次，两次失败就放弃
    
    Args:
        filename: 图片文件名
        image_path: 图片文件路径
    
    Returns:
        str: AI分析的描述文本，或失败时返回标准格式
    """
    # 尝试使用Google Gemini API分析图片
    if image_path and os.path.exists(image_path):
        # 首先检查API配置
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.json')
        api_key = None
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    api_key = config.get('gemini_api_key')
            except Exception as e:
                print(f"配置文件读取失败: {e}")
                return f"![{filename}]"  # 返回标准markdown格式
        
        # 如果找到有效的API密钥，使用Gemini分析
        if api_key and api_key != 'your-gemini-api-key-here':
            # 检查图片格式是否支持
            ext = os.path.splitext(image_path)[1].lower()
            mime_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.webp': 'image/webp',
                '.heic': 'image/heic',
                '.heif': 'image/heif'
            }
            
            # 如果图片格式不支持，跳过AI分析
            if ext not in mime_types:
                print(f"图片格式不支持AI分析: {ext}，回退到文件名")
                return f"![{filename}]"  # 返回标准markdown格式
            
            mime_type = mime_types[ext]
            
            # 读取图片文件
            try:
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
            except Exception as e:
                print(f"图片文件读取失败: {e}")
                return f"![{filename}]"  # 返回标准markdown格式
            
            # 简化的重试逻辑：最多尝试2次
            for attempt in range(2):
                try:
                    # 设置代理环境变量（仅在当前进程中有效）
                    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10809"
                    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10899"
                    
                    from google import genai
                    from google.genai import types
                    
                    client = genai.Client(api_key=api_key)
                    
                    # 调用Gemini API
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[
                            types.Part.from_bytes(
                                data=image_bytes,
                                mime_type=mime_type,
                            ),
                            '详细描述图片内容，用中文回答，直接说明图片中包含什么，不要用"这是"、"这张图片"等开头。'
                        ],
                        config=types.GenerateContentConfig(
                            thinking_config=types.ThinkingConfig(thinking_budget=128)
                        )
                    )
                    
                    # 解析响应
                    description_text = None
                    
                    # 方法1：直接获取text属性
                    if hasattr(response, 'text') and response.text:
                        description_text = response.text
                    
                    # 方法2：检查candidates
                    elif hasattr(response, 'candidates') and response.candidates:
                        for candidate in response.candidates:
                            if hasattr(candidate, 'content') and candidate.content:
                                if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                    for part in candidate.content.parts:
                                        if hasattr(part, 'text') and part.text:
                                            description_text = part.text
                                            break
                                elif hasattr(candidate.content, 'text') and candidate.content.text:
                                    description_text = candidate.content.text
                                    break
                            if description_text:
                                break
                    
                    # 方法3：检查其他可能的字段
                    elif hasattr(response, 'content') and response.content:
                        if hasattr(response.content, 'text'):
                            description_text = response.content.text
                    
                    if description_text:
                        # 处理响应文本
                        description = description_text.strip()
                        description = description.replace('\n', ' ').replace('\r', ' ')
                        description = ' '.join(description.split())  # 只合并多余空格
                        
                        # 确保描述不为空
                        if description and len(description) > 0:
                            return description
                    
                    # 如果没有获取到有效响应，继续重试（如果还有机会）
                    
                except ImportError as e:
                    # 库导入失败，不可恢复错误，直接退出
                    return f"![{filename}]"  # 返回标准markdown格式
                    
                except Exception as e:
                    # 如果是第二次尝试，就不再重试了
                    if attempt == 1:
                        break
            
            # 两次尝试都失败了，放弃AI分析
    
    # 回退处理：返回标准格式
    if not image_path:
        pass  # 图片没有提供路径
    elif not os.path.exists(image_path):
        pass  # 图片路径不存在
    
    # 修复：回退到标准markdown图片格式，而不是纯文件名
    return f"![{filename}]"


def process_markdown_images(content, images_info=None):
    """
    处理Markdown内容中的图片引用
    AI可用时：使用Gemini API生成详细描述替换图片
    AI不可用时：保持传统markdown图片格式
    
    Args:
        content: Markdown内容
        images_info: 图片信息列表（可选）
    
    Returns:
        处理后的内容
    """
    if not images_info:
        images_info = []
    
    # 创建文件名到描述的映射
    image_descriptions = {}
    for img in images_info:
        filename = img.get('filename', '')
        image_path = img.get('path', None)
        # 使用AI分析函数，传入图片路径以便AI分析
        description = analyze_image_content(filename, image_path)
        image_descriptions[filename] = description
    
    # 匹配Markdown图片语法 ![alt](path)
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    
    def replace_image(match):
        image_path = match.group(2)
        
        # 提取文件名
        filename = os.path.basename(image_path)
        
        # 获取图片描述（使用简化的重试逻辑）
        if filename in image_descriptions:
            description = image_descriptions[filename]
        else:
            # 如果不在预处理的列表中，尝试构建完整路径分析
            full_path = None
            if images_info and len(images_info) > 0:
                # 尝试从第一个图片的路径推断图片目录
                sample_path = images_info[0].get('path', '')
                if sample_path:
                    img_dir = os.path.dirname(sample_path)
                    possible_path = os.path.join(img_dir, filename)
                    if os.path.exists(possible_path):
                        full_path = possible_path
            
            description = analyze_image_content(filename, full_path)
            image_descriptions[filename] = description
        
        # 直接使用AI描述，无需检查标记
        pure_description = description
        # 清理和格式化
        pure_description = pure_description.replace('\n', ' ').replace('\r', ' ').strip()
        pure_description = ' '.join(pure_description.split())
        
        if pure_description:
            return f"[{pure_description}]"
        else:
            return f"![{filename}]({image_path})"
    
    # 替换所有图片引用
    result = re.sub(pattern, replace_image, content)
    return result


def build_description(path):
    """Build description and generate intermediate artifacts for NON-STRUCTURED data only"""
    st = os.stat(path)
    meta = {
        "file_name": os.path.basename(path),
        "size": st.st_size,
        "modified_time": datetime.fromtimestamp(st.st_mtime).isoformat(),
        "detected_type": os.path.splitext(path)[1].lstrip('.').lower(),
    }
    ext = meta["detected_type"]
    intermediate_md = ''
    images = []
    body = {}
    
    # Parse NON-STRUCTURED file types only
    # NOTE: This script should only receive non-structured files from file_classifier.py
    if ext in ["md", "markdown"]:
        body = parse_markdown(path)
        intermediate_md = body.get('full_text', '')  # 统一使用body中的full_text
        
        # Extract and copy referenced images
        images_dir, base_name = create_images_directory(path, meta["file_name"])
        extracted_images = []
        
        # Find image references in markdown
        img_pattern = r'!\[[^\]]*\]\(([^)]+)\)'
        image_refs = re.findall(img_pattern, intermediate_md)
        
        if image_refs:
            
            for img_ref in image_refs:
                try:
                    # Handle relative paths from the original markdown file
                    if not os.path.isabs(img_ref):
                        src_img_path = os.path.join(os.path.dirname(path), img_ref)
                    else:
                        src_img_path = img_ref
                    
                    if os.path.exists(src_img_path):
                        img_filename = os.path.basename(src_img_path)
                        dest_path = os.path.join(images_dir, img_filename)
                        
                        # Copy image to intermediate artifacts
                        shutil.copy2(src_img_path, dest_path)
                        
                        extracted_images.append({
                            'filename': img_filename,
                            'path': dest_path,
                            'original_ref': img_ref,
                            'size_bytes': os.path.getsize(dest_path)
                        })
                except Exception as e:
                    print(f"Failed to copy image {img_ref}: {e}")
            
            # Update image references in intermediate markdown
            if extracted_images:
                for img in extracted_images:
                    old_ref = img['original_ref']
                    new_ref = f"../../images/{base_name}_images/{img['filename']}"
                    intermediate_md = intermediate_md.replace(f"]({old_ref})", f"]({new_ref})")
        
        images = extracted_images
        
    elif ext in ["txt"]:
        body = parse_txt(path)
        intermediate_md = body.get('full_text', '')
        
    elif ext in ["pdf"]:
        body = parse_pdf(path)
        intermediate_md = body.get('full_text', '')  # Full PDF text content
        
        # Extract images from PDF file
        images_dir, base_name = create_images_directory(path, meta["file_name"])
        extracted_images = []
        
        try:
            extracted_images = extract_images_from_pdf(path, images_dir)
            # PDF图片提取完成
        except Exception as e:
            print(f"Failed to extract images from PDF: {e}")
            extracted_images = []
        
        images = extracted_images
        
        # PDF图片信息只在YAML frontmatter中记录，不嵌入到markdown正文中
        # 添加PDF元数据信息到markdown正文
        if body.get('page_count'):
            intermediate_md += f"\n\n## PDF文档信息\n\n"
            intermediate_md += f"- 总页数: {body.get('page_count', 0)}\n"
            intermediate_md += f"- 文本长度: {body.get('text_length', 0)} 字符\n"
            intermediate_md += f"- 图片总数: {body.get('total_images', 0)}\n"
            if extracted_images:
                intermediate_md += f"- 图片已提取到: {base_name}_images/ 目录\n"
            
        
    elif ext in ["docx"]:
        body = parse_docx(path)
        intermediate_md = body.get('full_text', '')  # Full document text
        
        # Extract images from DOCX file
        images_dir, base_name = create_images_directory(path, meta["file_name"])
        extracted_images = []
        
        try:
            with zipfile.ZipFile(path, 'r') as z:
                media_files = [n for n in z.namelist() if n.startswith('word/media/')]
                # 处理DOCX中的媒体文件
                for media_file in media_files:
                    try:
                        image_data = z.read(media_file)
                        image_filename = os.path.basename(media_file)
                        output_path = os.path.normpath(os.path.join(images_dir, image_filename))
                        
                        # 修复：增强DOCX图片写入错误处理
                        # 确保输出目录存在
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        
                        with open(output_path, 'wb') as img_file:
                            img_file.write(image_data)
                        
                        # 验证文件写入成功
                        if os.path.exists(output_path):
                            actual_size = os.path.getsize(output_path)
                            expected_size = len(image_data)
                            
                            if actual_size == expected_size and actual_size > 0:
                                extracted_images.append({
                                    'filename': image_filename,
                                    'path': output_path,
                                    'size_bytes': len(image_data)
                                })
                                # 图片提取成功
                            else:
                                print(f"Warning: DOCX image size mismatch for {image_filename}: expected {expected_size}, got {actual_size}")
                        else:
                            print(f"Error: DOCX image file not found after write: {output_path}")
                            
                    except Exception as e:
                        print(f"Failed to extract DOCX image {media_file}: {e}")
        except Exception as e:
            print(f"Failed to extract images from DOCX: {e}")
        
        images = extracted_images
        
        # Add image references to intermediate markdown
        if extracted_images:
            intermediate_md += "\n\n## 文档中的图片\n\n"
            for img in extracted_images:
                img_relative_path = f"{base_name}_images/{img['filename']}"
                # 使用标准markdown格式，AI处理将在通用阶段进行
                intermediate_md += f"![{img['filename']}]({img_relative_path})\n\n"
            
    elif ext in ["doc"]:
        body = parse_doc(path)
        intermediate_md = body.get('full_text', '')  # Full document text
        
        # Note: DOC file image extraction is more complex and would require additional libraries
        # For now, we add a placeholder indicating that images may be present but not extracted
        images = []
        if "image" in intermediate_md.lower() or "图" in intermediate_md:
            intermediate_md += "\n\n## 注意事项\n\n此DOC文件可能包含图片，但当前版本暂不支持DOC文件的图片自动提取。\n\n"
    
    elif ext in ["xlsx", "xlsm", "xls"]:
        # Handle Excel files that are classified as non-structured (contain images/complex formatting)
        # For non-structured Excel files, we extract images and provide full table content with embedded images
        
        # Create images directory under descriptions/intermediate_artifacts
        images_dir, base_name = create_images_directory(path, meta["file_name"])
        
        # Extract images from Excel file FIRST, before parsing sheets
        all_images = []
        try:
            with zipfile.ZipFile(path, 'r') as z:
                namelist = z.namelist()
                # Build sheets_map for image extraction
                sheets_map = []
                try:
                    wb_xml = z.read('xl/workbook.xml')
                    rel_xml = z.read('xl/_rels/workbook.xml.rels')
                    wbroot = ET.fromstring(wb_xml)
                    relroot = ET.fromstring(rel_xml)
                    id_to_target = {}
                    for rel in relroot.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                        rid = rel.attrib.get('Id')
                        target = rel.attrib.get('Target')
                        if rid and target:
                            if not target.startswith('/'):
                                spath = 'xl/' + target
                            else:
                                spath = target.lstrip('/')
                            id_to_target[rid] = spath
                    for sheet_elem in wbroot.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet'):
                        name = sheet_elem.attrib.get('name')
                        rid = sheet_elem.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                        if name and rid and rid in id_to_target:
                            sheets_map.append({'name': name, 'path': id_to_target[rid]})
                except Exception:
                    sheets_map = []
                
                all_images = extract_images_from_xlsx(z, namelist, images_dir, sheets_map)
                
                # Excel图片提取完成
        except Exception as e:
            print(f"Failed to extract images: {e}")
            all_images = []
        
        # Create a mapping of (sheet_name, row, col) -> images for that position
        # 修复：建立原始Excel坐标到图片的映射关系（稍后会转换为过滤后坐标）
        images_by_original_position = {}  # 使用原始Excel坐标
        images_debug_info = {}  # 用于调试的详细信息
        
        for img in all_images:
            row = img.get('row')
            col = img.get('col')
            sheet_name = img.get('sheet_name', 'Unknown')
            
            if row is not None and col is not None and row > 0 and col > 0:
                # 标准坐标映射（原始Excel坐标，已经是 1-based）
                pos_key = f"{sheet_name}_{row}_{col}"
                if pos_key not in images_by_original_position:
                    images_by_original_position[pos_key] = []
                images_by_original_position[pos_key].append(img)
                
                # 记录调试信息
                if sheet_name not in images_debug_info:
                    images_debug_info[sheet_name] = []
                images_debug_info[sheet_name].append({
                    'filename': img['filename'],
                    'original_row': row,
                    'original_col': col,
                    'original_pos_key': pos_key
                })
                # 图片位置映射完成
            else:
                debug_print(f"WARNING: Image {img.get('filename', 'unknown')} has invalid coordinates (Row={row}, Col={col})")
        
        # 解析Excel内容并生成markdown
        body = parse_excel(path, images_by_original_position)
        
        # Generate markdown with tables and embedded images
        parts = []
        embedded_images_count = 0  # 统计成功嵌入的图片数量
        unplaced_images = []  # 记录无法放置的图片
        
        for sheet_idx, s in enumerate(body.get('sheets', []) or []):
            sheet_name = s.get("sheet_name", "Unknown")
            parts.append(f'## Sheet: {sheet_name}')
            parts.append('')
            
            # 获取转换后的图片位置映射
            coordinate_mappings = s.get('coordinate_mappings')
            transformed_images_by_position = {}
            if coordinate_mappings and 'transformed_images_by_position' in coordinate_mappings:
                transformed_images_by_position = coordinate_mappings['transformed_images_by_position']
            
            # Use all_rows if available, otherwise sample_rows
            if 'all_rows' in s and s['all_rows']:
                all_sheet_rows = s['all_rows']
                
                # Create well-formatted table with proper structure, filtering empty rows
                if all_sheet_rows:
                    # 使用转换后的图片位置数据来预扫描图片坐标
                    max_image_row = 0
                    image_rows = set()
                    for pos_key in transformed_images_by_position.keys():
                        key_parts = pos_key.split('_')
                        if len(key_parts) >= 3 and key_parts[0] == sheet_name:
                            try:
                                # 注意：这里使用的已经是过滤后的坐标（表格行号）
                                filtered_row = int(key_parts[1])
                                image_rows.add(filtered_row)
                                max_image_row = max(max_image_row, filtered_row)
                            except ValueError:
                                pass
                    
                    # 图片行分析完成
                    
                    # 修复：使用过滤后的图片位置来扩展表格行数
                    required_rows = max(len(all_sheet_rows), max_image_row + 1)
                    if len(all_sheet_rows) < required_rows:
                        # 填充空行到所需长度
                        empty_row = [None] * len(all_sheet_rows[0]) if all_sheet_rows else []
                        while len(all_sheet_rows) < required_rows:
                            all_sheet_rows.append(empty_row[:])
                        print(f"DEBUG: Extended filtered sheet rows from {len(all_sheet_rows)} to {required_rows}")
                    
                    # 使用过滤后的坐标系统：直接处理all_sheet_rows（已经是过滤后的数据）
                    header_row = all_sheet_rows[0] if all_sheet_rows else []
                    
                    # 构建表格：收集所有需要显示的行
                    filtered_data_rows = []
                    excel_to_table_row_mapping = {}  # Excel行号 -> 表格行号的映射
                    
                    # 修复：改进空行检测和图片行处理逻辑
                    # 使用绝对坐标系统处理所有行（跳过第0行标题行）
                    for excel_row_idx in range(1, len(all_sheet_rows)):
                        row_data = all_sheet_rows[excel_row_idx]
                        
                        # 检查这一行是否需要保留
                        has_content = False
                        has_images = False
                        
                        # 检查文本内容
                        if row_data:
                            for cell_value in row_data:
                                if cell_value is not None and str(cell_value).strip():
                                    has_content = True
                                    break
                        
                        # 修复：检查是否有图片在这一行（使用原始坐标）
                        # 检查原始图片位置中是否有图片在当前行
                        for original_pos_key in images_by_original_position.keys():
                            key_parts = original_pos_key.split('_')
                            if len(key_parts) >= 3 and key_parts[0] == sheet_name:
                                try:
                                    img_original_row = int(key_parts[1])
                                    # excel_row_idx 是从1开始的过滤后行号，需要转换为原始行号
                                    # 当前的excel_row_idx实际上是在all_sheet_rows中的索引
                                    # 我们需要检查原始Excel行是否等于 excel_row_idx（因为all_sheet_rows是原始数据）
                                    if img_original_row == excel_row_idx:
                                        has_images = True
                                        has_content = True  # 有图片的行强制保留
                                        # 图片行已标记
                                        break
                                except ValueError:
                                    continue
                            if has_images:
                                break
                        
                        # 检查是否是相邻的结构行（图片行前后保留1行保持表格完整性）
                        is_structure_row = False
                        for other_row_idx in range(max(0, excel_row_idx - 1), min(len(all_sheet_rows), excel_row_idx + 2)):
                            for col_idx in range(len(row_data) if row_data else len(sorted_content_cols)):
                                pos_key = f"{sheet_name}_{other_row_idx}_{col_idx}"
                                if pos_key in transformed_images_by_position:
                                    is_structure_row = True
                                    break
                            if is_structure_row:
                                break
                        
                        # 保留条件：有内容、有图片、或是结构行
                        if has_content or has_images or is_structure_row:
                            table_row_idx = len(filtered_data_rows)
                            excel_to_table_row_mapping[excel_row_idx] = table_row_idx
                            filtered_data_rows.append((excel_row_idx, row_data))
                    
                    # 行过滤完成，继续处理表格
                    
                    # Clean and format header
                    clean_header = []
                    for col in header_row:
                        col_str = str(col) if col is not None else ''
                        # Clean header text for better readability using unified function
                        col_str = escape_table_breaking_chars(col_str)
                        if not col_str:
                            col_str = f'列{len(clean_header)+1}'  # Default column name
                        clean_header.append(col_str)
                    
                    # Don't calculate column widths - let markdown renderer handle it
                    
                    # Create simple header without forced alignment
                    parts.append('| ' + ' | '.join(clean_header) + ' |')
                    parts.append('| ' + ' | '.join(['---' for _ in clean_header]) + ' |')
                    
                    # Process each filtered data row with proper Excel row mapping
                    for table_row_idx, (excel_row_idx, row_data) in enumerate(filtered_data_rows):
                        processed_row = []
                        
                        for col_idx, cell_value in enumerate(row_data):
                            # Format cell content with proper cleaning (no truncation)
                            cell_content = str(cell_value) if cell_value is not None else ''
                            # Use unified function to escape table-breaking characters
                            cell_content = escape_table_breaking_chars(cell_content)
                            
                            # 修复：移除不必要的方括号转义
                            # cell_content = cell_content.replace('[', '\\[').replace(']', '\\]')
                            # 保留其他可能冲突的Markdown字符的处理（如果需要）
                            # cell_content = cell_content.replace('*', '\\*').replace('_', '\\_')
                            # cell_content = cell_content.replace('`', '\\`').replace('#', '\\#')
                            
                            # 修复：使用过滤后的坐标来查找图片
                            table_pos_key = f"{sheet_name}_{table_row_idx}_{col_idx}"
                            if table_pos_key in transformed_images_by_position:
                                # Add images to this cell with correct relative path
                                img_refs = []
                                for img in transformed_images_by_position[table_pos_key]:
                                    img_relative_path = f"{base_name}_images/{img['filename']}"
                                    # 分析图片内容
                                    img_desc = analyze_image_content(img['filename'], img.get('path'))
                                    
                                    # 修复：对于空单元格，直接插入AI描述作为单元格内容
                                    if img_desc and img_desc != img['filename']:
                                        # AI分析成功，使用纯文本描述
                                        pure_desc = escape_table_breaking_chars(img_desc)
                                        if pure_desc:
                                            img_refs.append(f"[{pure_desc}]")
                                        else:
                                            img_refs.append(f"[{img['filename']}]")
                                    else:
                                        # AI分析失败，使用传统格式
                                        img_refs.append(f"![{img['filename']}]({img_relative_path})")
                                    
                                    embedded_images_count += 1  # 统计嵌入的图片
                                
                                # 修复：确保图片内容被正确插入到单元格中
                                if img_refs:
                                    if cell_content and cell_content.strip():
                                        # 如果单元格有内容，追加图片描述
                                        cell_content += ' ' + ' '.join(img_refs)
                                    else:
                                        # 如果单元格为空，直接使用图片描述作为单元格内容
                                        cell_content = ' '.join(img_refs)
                            
                            # Don't truncate - keep full content
                            processed_row.append(cell_content)
                        
                        parts.append('| ' + ' | '.join(processed_row) + ' |')
                    
                parts.append('')
            else:
                # Fallback to original method
                cols = s.get('columns') or []
                sample_rows = s.get('sample_rows') or []
                
                if cols and sample_rows:
                    # Filter out empty rows from sample_rows and build row mapping
                    filtered_sample_rows = []
                    excel_to_table_row_mapping = {}  # Excel行号 -> 表格行号的映射
                    
                    for row_idx, r in enumerate(sample_rows):
                        # Excel中的真实行号：数据行从第2行开始（第1行是header），所以是row_idx + 1
                        # 但图片的row坐标可能是以0为基础的，需要检查多种可能的行号
                        possible_excel_rows = [row_idx + 1, row_idx, row_idx + 2]  # 尝试多种行号映射
                        
                        # Check if row has any meaningful content (text data or images)
                        has_content = False
                        found_excel_row = row_idx + 1  # 默认行号
                        
                        # Check for text content
                        for cell_value in r:
                            if cell_value is not None and str(cell_value).strip():
                                has_content = True
                                break
                        
                        # 修复：检查图片时使用正确的坐标映射
                        if not has_content:
                            # Excel中的真实行号：数据行从第2行开始（第1行是header），所以是row_idx + 1
                            excel_row_num = row_idx + 1
                            for col_idx in range(len(r)):
                                pos_key = f"{sheet_name}_{excel_row_num}_{col_idx}"
                                # 注意：这里仍然会检查原始位置，但实际上该fallback已经不需要
                                # 因为我们已经在上面对坐标进行了正确的过滤和映射
                                if pos_key in transformed_images_by_position:
                                    has_content = True
                                    found_excel_row = excel_row_num
                                    print(f"DEBUG: Found image at fallback position {pos_key}")
                                    break
                        
                        # Only keep rows with content and build mapping
                        if has_content:
                            table_row_idx = len(filtered_sample_rows)  # 在表格中的实际位置
                            excel_to_table_row_mapping[found_excel_row] = table_row_idx
                            filtered_sample_rows.append((found_excel_row, r))
                    
                    # Clean and format columns
                    clean_cols = []
                    for col in cols:
                        col_str = str(col) if col is not None else ''
                        # Use unified function for header text cleaning
                        col_str = escape_table_breaking_chars(col_str)
                        if not col_str:
                            col_str = f'列{len(clean_cols)+1}'
                        clean_cols.append(col_str)
                    
                    # Create simple header without forced alignment
                    parts.append('| ' + ' | '.join(clean_cols) + ' |')
                    parts.append('| ' + ' | '.join(['---' for _ in clean_cols]) + ' |')
                    
                    for excel_row_idx, r in filtered_sample_rows:
                        processed_row = []
                        for col_idx, cell_value in enumerate(r):
                            cell_content = str(cell_value) if cell_value is not None else ''
                            # Use unified function to escape table-breaking characters
                            cell_content = escape_table_breaking_chars(cell_content)
                            
                            # 修复：移除不必要的方括号转义
                            # cell_content = cell_content.replace('[', '\\[').replace(']', '\\]')
                            # 保留其他可能冲突的Markdown字符的处理（如果需要）
                            # cell_content = cell_content.replace('*', '\\*').replace('_', '\\_')
                            # cell_content = cell_content.replace('`', '\\`').replace('#', '\\#')
                            
                            # 修复：使用坐标映射查找图片 - 检查原始Excel坐标是否有图片 (fallback mode)
                            pos_key = f"{sheet_name}_{excel_row_idx}_{col_idx}"
                            if pos_key in transformed_images_by_position:
                                img_refs = []
                                for img in transformed_images_by_position[pos_key]:
                                    img_relative_path = f"{base_name}_images/{img['filename']}"
                                    # 分析图片内容
                                    img_desc = analyze_image_content(img['filename'], img.get('path'))
                                    
                                    # 直接使用描述，无需标记检查
                                    if img_desc and img_desc != img['filename']:
                                        # AI分析成功，使用纯文本描述
                                        pure_desc = escape_table_breaking_chars(img_desc)
                                        if pure_desc:
                                            img_refs.append(f"[{pure_desc}]")
                                        else:
                                            img_refs.append(f"[{img['filename']}]")
                                    else:
                                        # AI分析失败，使用传统格式
                                        img_refs.append(f"![{img['filename']}]({img_relative_path})")
                                        # fallback图片嵌入完成
                                
                                if img_refs:
                                    if cell_content:
                                        cell_content += ' ' + ' '.join(img_refs)
                                    else:
                                        cell_content = ' '.join(img_refs)
                            
                            # Don't truncate - keep full content
                            processed_row.append(cell_content)
                        
                        parts.append('| ' + ' | '.join(processed_row) + ' |')
                    parts.append('')
        
        # 图片嵌入处理完成
        
        # 添加图片摘要到markdown
        if all_images:
            parts.append('## Image Summary')
            parts.append('')
            parts.append(f"Total images extracted: {len(all_images)}")
            parts.append('')
            
            # 按sheet分组显示图片
            images_by_sheet = {}
            for img in all_images:
                sheet_name = img.get('sheet_name', 'Unknown')
                if sheet_name not in images_by_sheet:
                    images_by_sheet[sheet_name] = []
                images_by_sheet[sheet_name].append(img)
            
            for sheet_name, sheet_images in images_by_sheet.items():
                parts.append(f'### {sheet_name}')
                parts.append('')
                for img in sheet_images:
                    parts.append(f'- **{img["filename"]}** at Row {img.get("row", "?")} Col {img.get("col", "?")} ({img.get("size_bytes", 0)} bytes)')
                parts.append('')
        
        intermediate_md = '\n'.join(parts)
        images = all_images
        
    else:
        # Handle any other non-structured file types as plain text
        try:
            text = read_text_file(path)
            body = {"file_type": "text", "text_length": len(text), "is_structured": False}
            intermediate_md = text
        except Exception as e:
            body = {"file_type": "unknown", "error": str(e), "is_structured": False}
            
    # Save intermediate markdown artifact
    if intermediate_md and len(intermediate_md.strip()) > 0:
        # Generate output path for intermediate artifact
        base_name = os.path.splitext(meta["file_name"])[0]
        # Create intermediate_artifacts subdirectory under descriptions
        intermediate_dir = os.path.join(os.path.dirname(os.path.dirname(path)), "descriptions", "intermediate_artifacts")
        os.makedirs(intermediate_dir, exist_ok=True)
        intermediate_path = os.path.join(intermediate_dir, f"{base_name}_intermediate.md")
        
        # 处理Markdown中的图片引用
        # PDF文件跳过AI图片处理以提高性能，直接保持传统markdown格式
        # Excel文件已在表格生成过程中处理图片，不需要再次处理
        if ext == "pdf":
            processed_md = intermediate_md  # PDF图片直接嵌入，不做AI处理
        elif ext in ["xlsx", "xlsm", "xls"]:
            processed_md = intermediate_md  # Excel图片已在表格中处理
        else:
            # 其他文件类型：AI可用时生成描述，不可用时保持原格式  
            processed_md = process_markdown_images(intermediate_md, images)
        
        # 构建标准YAML frontmatter格式
        frontmatter_data = {
            'file_name': meta['file_name'],
            'file_type': body.get('file_type', meta['detected_type']),
            'size': meta['size'],  # 统一使用size而非file_size_bytes
            'modified_time': meta['modified_time'],
            'is_structured': body.get('is_structured', False),
            'extraction_method': 'document_parser'
        }
        
        # 构建中间产物信息（统一结构）
        intermediate_artifacts = {
            'intermediate_file_path': f"intermediate_artifacts/{base_name}_intermediate.md"
        }
        
        # 添加图片信息
        if images and len(images) > 0:
            intermediate_artifacts['images_count'] = len(images)
            intermediate_artifacts['images_directory'] = f"intermediate_artifacts/{base_name}_images"
        else:
            intermediate_artifacts['images_count'] = 0
            
        frontmatter_data['intermediate_artifacts'] = intermediate_artifacts
        
        with open(intermediate_path, 'w', encoding='utf-8') as f:
            # 写入标准YAML frontmatter
            import yaml
            f.write("---\n")
            f.write(yaml.dump(frontmatter_data, allow_unicode=True, sort_keys=False, default_flow_style=False))
            f.write("---\n\n")
            # 写入处理后的正文内容（图片已替换为描述）
            f.write(processed_md)
            
        print(f"Intermediate artifact saved to: {intermediate_path}")
        if images and len(images) > 0:
            print(f"Extracted {len(images)} images to original data source location: {os.path.dirname(images[0]['path'])}")
    
    # Note: This script now only generates intermediate artifacts
    # Final JSON descriptions will be handled by DataSourceFileAnalysisAgent
    return None

if __name__ == "__main__":
    import sys
    import io
    
    # 设置输出编码，保持与其他脚本一致
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass
    
    p = argparse.ArgumentParser()
    p.add_argument("path", help="file path to parse")
    p.add_argument("--debug", action="store_true", help="enable detailed debug output")
    args = p.parse_args()
    path = args.path
    
    # 设置调试模式
    if args.debug:
        DEBUG_OUTPUT = True
        debug_print("Debug mode enabled")
    
    if not os.path.exists(path):
        print(f"Error: File not found - {path}")
        sys.exit(1)
    
    try:
        # Generate intermediate artifacts only
        build_description(path)
        print("Intermediate artifact generation completed.")
    except Exception as e:
        print(f"Error processing {path}: {e}")
        sys.exit(1)