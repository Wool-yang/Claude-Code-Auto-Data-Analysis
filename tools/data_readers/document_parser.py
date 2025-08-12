import os
import sys
import json
import zipfile
import argparse
import re
from datetime import datetime
import chardet

def get_current_task_name():
    """Get current task name from project context or assume 测试任务 for now"""
    # For now, return the test task name, can be enhanced later
    return "测试任务"

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
        return result.get('encoding', 'utf-8')
    except Exception:
        return 'utf-8'

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
    
    # Sample first 1000 characters
    sample = text[:1000] if len(text) > 1000 else text
    return text, sample

def scan_sensitive(text):
    """Scan for sensitive data patterns"""
    findings = []
    # Email pattern
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if emails:
        findings.extend([{"type": "email", "value": email} for email in set(emails)])
    
    # API key patterns
    api_patterns = [
        (r'\b[A-Za-z0-9]{32,}\b', 'possible_api_key'),
        (r'\bsk-[A-Za-z0-9]{32,}\b', 'openai_api_key'),
        (r'\bAKIA[0-9A-Z]{16}\b', 'aws_access_key'),
    ]
    
    for pattern, key_type in api_patterns:
        matches = re.findall(pattern, text)
        if matches:
            findings.extend([{"type": key_type, "value": match} for match in set(matches)])
    
    return findings

def parse_markdown(path):
    """Parse markdown file"""
    text, sample = read_text_file(path)
    return {
        "file_type": "markdown",
        "text_sample": sample,
        "text_length": len(text),
        "sensitive_findings": scan_sensitive(text),
        "is_structured": False
    }

def parse_docx(path):
    """Parse DOCX file to extract full text content"""
    try:
        with zipfile.ZipFile(path, 'r') as z:
            # Extract main document text
            if 'word/document.xml' in z.namelist():
                doc_xml = z.read('word/document.xml')
                import xml.etree.ElementTree as ET
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
                    "tables": [],
                    "image_count": 0,
                    "has_macros": False,
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
                "tables": [],
                "image_count": 0,
                "has_macros": False,
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
        import string
        printable = set(string.printable)
        text = ''.join(filter(lambda x: x in printable, data.decode('latin1', errors='ignore')))
        
        return {
            "file_type": "doc",
            "full_text": text,
            "text_length": len(text),
            "tables": [],
            "image_count": 0,
            "has_macros": False,
            "is_structured": False,
            "extraction_method": "binary_fallback"
        }
    except Exception as e:
        return {"file_type": "doc", "error": str(e), "is_structured": False}

def parse_csv(path):
    """Parse CSV file to extract all rows and columns"""
    try:
        import csv
        import io
        
        # Detect encoding
        encoding = detect_encoding(path)
        
        with open(path, 'r', encoding=encoding, errors='replace') as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)
            
            # Detect CSV dialect
            try:
                dialect = csv.Sniffer().sniff(sample)
                delimiter = dialect.delimiter
            except:
                delimiter = ','  # fallback
            
            reader = csv.reader(f, delimiter=delimiter)
            rows = list(reader)
            
            if rows:
                columns = rows[0] if rows else []
                data_rows = rows[1:] if len(rows) > 1 else []
                
                return {
                    "file_type": "csv",
                    "columns": columns,
                    "rows": data_rows,
                    "row_count": len(rows),
                    "column_count": len(columns),
                    "delimiter": delimiter,
                    "encoding": encoding,
                    "is_structured": True
                }
            else:
                return {
                    "file_type": "csv",
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "column_count": 0,
                    "is_structured": True
                }
                
    except Exception as e:
        return {"file_type": "csv", "error": str(e), "is_structured": True}

def parse_xls(path):
    """Parse XLS file using xlrd if available"""
    try:
        # Try using openpyxl first (works for some xls files)
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=True)
            sheets = []
            
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    rows.append([str(cell) if cell is not None else '' for cell in row])
                
                if rows:
                    columns = rows[0]
                    data_rows = rows[1:] if len(rows) > 1 else []
                else:
                    columns = []
                    data_rows = []
                
                sheets.append({
                    'sheet_name': sheet_name,
                    'columns': columns,
                    'sample_rows': data_rows,  # All rows, not just sample
                    'row_count': len(rows),
                    'column_count': len(columns),
                    'images': []
                })
            
            return {'file_type': 'xls', 'has_macros': False, 'sheets': sheets, 'is_structured': True}
            
        except:
            # Try xlrd as fallback
            try:
                import xlrd
                wb = xlrd.open_workbook(path)
                sheets = []
                
                for sheet_idx, sheet_name in enumerate(wb.sheet_names()):
                    ws = wb.sheet_by_index(sheet_idx)
                    rows = []
                    
                    for row_idx in range(ws.nrows):
                        row = []
                        for col_idx in range(ws.ncols):
                            cell = ws.cell(row_idx, col_idx)
                            if cell.ctype == xlrd.XL_CELL_DATE:
                                try:
                                    import datetime
                                    cell_value = xlrd.xldate_as_datetime(cell.value, wb.datemode).isoformat()
                                except:
                                    cell_value = str(cell.value)
                            else:
                                cell_value = str(cell.value)
                            row.append(cell_value)
                        rows.append(row)
                    
                    if rows:
                        columns = rows[0]
                        data_rows = rows[1:] if len(rows) > 1 else []
                    else:
                        columns = []
                        data_rows = []
                    
                    sheets.append({
                        'sheet_name': sheet_name,
                        'columns': columns,
                        'sample_rows': data_rows,  # All rows
                        'row_count': len(rows),
                        'column_count': len(columns),
                        'images': []
                    })
                
                return {'file_type': 'xls', 'has_macros': False, 'sheets': sheets, 'is_structured': True}
                
            except ImportError:
                return {"file_type": "xls", "error": "xlrd library not available", "is_structured": True}
                
    except Exception as e:
        return {"file_type": "xls", "error": str(e), "is_structured": True}

def parse_txt(path):
    """Parse TXT file - extract full content"""
    try:
        text, sample = read_text_file(path)
        return {
            "file_type": "txt",
            "full_text": text,
            "text_sample": sample,
            "text_length": len(text),
            "sensitive_findings": scan_sensitive(text),
            "is_structured": False
        }
    except Exception as e:
        return {"file_type": "txt", "error": str(e), "is_structured": False}

def xlsx_has_vba(path):
    """Check if xlsx has VBA"""
    try:
        with zipfile.ZipFile(path, 'r') as z:
            return any(n.startswith("xl/vbaProject") for n in z.namelist())
    except Exception:
        return False

def extract_images_from_xlsx(z, namelist, output_dir, sheets_info=None):
    """Extract images from Excel file and save them to data source directory"""
    import xml.etree.ElementTree as ET
    extracted_images = []
    
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
    
    # Find all drawing files
    drawing_files = [f for f in namelist if f.startswith('xl/drawings/drawing') and f.endswith('.xml')]
    
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
                if rid and target and 'image' in rel.attrib.get('Type', ''):
                    # Convert relative path to full zip path
                    if not target.startswith('/'):
                        image_path = f"xl/drawings/{target}"
                    else:
                        image_path = target.lstrip('/')
                    rid_to_image[rid] = image_path
            
            # Find all anchors (image positions)
            anchors = []
            anchors.extend(droot.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}oneCellAnchor'))
            anchors.extend(droot.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}twoCellAnchor'))
            
            for i, anchor in enumerate(anchors):
                # Get position information
                from_elem = anchor.find('.//{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}from')
                row_idx, col_idx = None, None
                
                if from_elem is not None:
                    row_elem = from_elem.find('{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}row')
                    col_elem = from_elem.find('{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}col')
                    if row_elem is not None and row_elem.text:
                        row_idx = int(row_elem.text)
                    if col_elem is not None and col_elem.text:
                        col_idx = int(col_elem.text)
                
                # Find the blip element that references the image
                blip_elems = anchor.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
                for blip in blip_elems:
                    embed_rid = blip.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    if embed_rid and embed_rid in rid_to_image:
                        image_zip_path = rid_to_image[embed_rid]
                        
                        # Extract image to output directory (raw data source location)
                        if image_zip_path in namelist:
                            try:
                                image_data = z.read(image_zip_path)
                                image_filename = os.path.basename(image_zip_path)
                                # Normalize path for Windows
                                output_path = os.path.normpath(os.path.join(output_dir, image_filename))
                                
                                with open(output_path, 'wb') as img_file:
                                    img_file.write(image_data)
                                
                                extracted_images.append({
                                    'filename': image_filename,
                                    'path': output_path,
                                    'row': row_idx,
                                    'col': col_idx,
                                    'sheet_name': sheet_name,
                                    'drawing_file': drawing_file,
                                    'size_bytes': len(image_data)
                                })
                                
                            except Exception as e:
                                print(f"Failed to extract image {image_zip_path}: {e}")
                        
        except Exception as e:
            print(f"Error processing drawing file {drawing_file}: {e}")
            
    return extracted_images

def parse_xlsx(path, sample_rows=None, max_rows=None):
    """Parse XLSX file - extract ALL rows and ALL columns"""
    import xml.etree.ElementTree as ET
    vba = xlsx_has_vba(path)
    sheets = []
    try:
        with zipfile.ZipFile(path, 'r') as z:
            namelist = z.namelist()
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
                                    
                                    # Get cell value
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
                                    else:
                                        # inlineStr
                                        is_el = c.find('%sis' % ns)
                                        if is_el is not None:
                                            t_el = is_el.find('%st' % ns)
                                            if t_el is not None and t_el.text is not None:
                                                val = t_el.text
                                    
                                    row_vals[col_idx] = val
                            
                            rows_dict[row_num] = row_vals
                        
                        # Convert to ordered list of rows with all columns
                        if rows_dict:
                            max_row = max(rows_dict.keys())
                            for row_num in range(max_row + 1):
                                row_data = rows_dict.get(row_num, {})
                                # Create full row with all columns (fill missing with empty)
                                row_list = []
                                for col_idx in range(max_col + 1):
                                    val = row_data.get(col_idx)
                                    row_list.append(str(val) if val is not None else '')
                                all_rows.append(row_list)
                        
                        if all_rows:
                            header = all_rows[0] if all_rows else []
                            data_rows = all_rows[1:] if len(all_rows) > 1 else []
                        else:
                            header = []
                            data_rows = []
                        
                        sheets.append({
                            'sheet_name': sname, 
                            'row_count': len(all_rows), 
                            'column_count': len(header), 
                            'columns': header, 
                            'sample_rows': data_rows,  # Actually ALL rows now
                            'all_rows': all_rows,  # Complete data including headers
                            'images': []
                        })
                    else:
                        sheets.append({'sheet_name': sname, 'row_count': None, 'column_count': None, 'columns': [], 'sample_rows': [], 'images': []})
                except Exception as e:
                    print(f"Error parsing sheet {sname}: {e}")
                    sheets.append({'sheet_name': sname, 'row_count': None, 'column_count': None, 'columns': [], 'sample_rows': [], 'images': []})
            return {'file_type': 'xlsx', 'has_macros': vba, 'sheets': sheets, 'is_structured': True}
    except Exception as e:
        return {'file_type': 'xlsx', 'has_macros': vba, 'sheets': None, 'is_structured': True, 'error': str(e)}

def build_description(path):
    """Build description and generate intermediate artifacts"""
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
    
    # Parse different file types with full content extraction
    if ext in ["md", "markdown"]:
        txt, _ = read_text_file(path)
        body = parse_markdown(path)
        intermediate_md = txt  # Full markdown content
        
        # Extract and copy referenced images
        base_name = os.path.splitext(meta["file_name"])[0]
        current_task_name = get_current_task_name()
        extracted_images = []
        
        if current_task_name:
            # Find image references in markdown
            import re
            img_pattern = r'!\[[^\]]*\]\(([^)]+)\)'
            image_refs = re.findall(img_pattern, txt)
            
            if image_refs:
                # Create images directory under descriptions/intermediate_artifacts
                raw_data_dir = os.path.dirname(path)
                descriptions_dir = os.path.join(os.path.dirname(raw_data_dir), "descriptions")
                intermediate_artifacts_dir = os.path.join(descriptions_dir, "intermediate_artifacts")
                images_dir = os.path.join(intermediate_artifacts_dir, f"{base_name}_images")
                os.makedirs(images_dir, exist_ok=True)
                
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
                            import shutil
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
                        new_ref = f"{base_name}_images/{img['filename']}"
                        intermediate_md = intermediate_md.replace(f"]({old_ref})", f"]({new_ref})")
        
        images = extracted_images
        
    elif ext in ["txt"]:
        body = parse_txt(path)
        intermediate_md = body.get('full_text', '')
        
    elif ext in ["docx"]:
        body = parse_docx(path)
        intermediate_md = body.get('full_text', '')  # Full document text
        
        # Extract images from DOCX file
        base_name = os.path.splitext(meta["file_name"])[0]
        current_task_name = get_current_task_name()
        extracted_images = []
        
        if current_task_name:
            # Create images directory under descriptions/intermediate_artifacts
            raw_data_dir = os.path.dirname(path)
            descriptions_dir = os.path.join(os.path.dirname(raw_data_dir), "descriptions")
            intermediate_artifacts_dir = os.path.join(descriptions_dir, "intermediate_artifacts")
            images_dir = os.path.join(intermediate_artifacts_dir, f"{base_name}_images")
            os.makedirs(images_dir, exist_ok=True)
            
            try:
                with zipfile.ZipFile(path, 'r') as z:
                    media_files = [n for n in z.namelist() if n.startswith('word/media/')]
                    for media_file in media_files:
                        try:
                            image_data = z.read(media_file)
                            image_filename = os.path.basename(media_file)
                            output_path = os.path.normpath(os.path.join(images_dir, image_filename))
                            
                            with open(output_path, 'wb') as img_file:
                                img_file.write(image_data)
                            
                            extracted_images.append({
                                'filename': image_filename,
                                'path': output_path,
                                'size_bytes': len(image_data)
                            })
                        except Exception as e:
                            print(f"Failed to extract image {media_file}: {e}")
            except Exception as e:
                print(f"Failed to extract images from DOCX: {e}")
        
        images = extracted_images
        
        # Add image references to intermediate markdown
        if extracted_images:
            intermediate_md += "\n\n## 文档中的图片\n\n"
            for img in extracted_images:
                img_relative_path = f"{base_name}_images/{img['filename']}"
                intermediate_md += f"![{img['filename']}]({img_relative_path})\n\n"
            
    elif ext in ["doc"]:
        body = parse_doc(path)
        intermediate_md = body.get('full_text', '')  # Full document text
        
        # Note: DOC file image extraction is more complex and would require additional libraries
        # For now, we add a placeholder indicating that images may be present but not extracted
        images = []
        if "image" in intermediate_md.lower() or "图" in intermediate_md:
            intermediate_md += "\n\n## 注意事项\n\n此DOC文件可能包含图片，但当前版本暂不支持DOC文件的图片自动提取。\n\n"
        
    elif ext in ["csv"]:
        body = parse_csv(path)
        parts = []
        if body.get('columns') and body.get('rows'):
            parts.append('| ' + ' | '.join([str(c) for c in body['columns']]) + ' |')
            parts.append('| ' + ' | '.join(['---' for _ in body['columns']]) + ' |')
            # All rows for CSV
            for r in body['rows']:
                parts.append('| ' + ' | '.join([str(x) if x is not None else '' for x in r]) + ' |')
        intermediate_md = '\n'.join(parts)
        
    elif ext in ["xls"]:
        body = parse_xls(path)
        parts = []
        for s in body.get('sheets', []) or []:
            parts.append(f'## Sheet: {s.get("sheet_name", "Unknown")}')
            parts.append('')
            
            cols = s.get('columns') or []
            sample_rows = s.get('sample_rows') or []  # Actually all rows now
            
            if cols and sample_rows:
                # Create markdown table with ALL data
                parts.append('| ' + ' | '.join([str(c) for c in cols]) + ' |')
                parts.append('| ' + ' | '.join(['---' for _ in cols]) + ' |')
                
                for r in sample_rows:
                    parts.append('| ' + ' | '.join([str(x) if x is not None else '' for x in r]) + ' |')
                parts.append('')
        
        intermediate_md = '\n'.join(parts)
        
    elif ext in ["xlsx", "xlsm"]:
        body = parse_xlsx(path)
        parts = []
        all_images = []
        
        # Extract images to intermediate_artifacts directory
        base_name = os.path.splitext(meta["file_name"])[0]
        current_task_name = get_current_task_name()
        if current_task_name:
            # Create images directory under descriptions/intermediate_artifacts
            raw_data_dir = os.path.dirname(path)  # Where the original file is
            descriptions_dir = os.path.join(os.path.dirname(raw_data_dir), "descriptions")
            intermediate_artifacts_dir = os.path.join(descriptions_dir, "intermediate_artifacts")
            images_dir = os.path.join(intermediate_artifacts_dir, f"{base_name}_images")
            os.makedirs(images_dir, exist_ok=True)
            
            # Extract images from Excel file to dedicated images directory
            try:
                with zipfile.ZipFile(path, 'r') as z:
                    namelist = z.namelist()
                    # Build sheets_map for image extraction
                    sheets_map = []
                    try:
                        import xml.etree.ElementTree as ET
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
            except Exception as e:
                print(f"Failed to extract images: {e}")
                all_images = []
        
        # Create a mapping of (sheet_name, row, col) -> images for that position
        images_by_sheet_position = {}
        for img in all_images:
            row = img.get('row')
            col = img.get('col')
            sheet_name = img.get('sheet_name', 'Unknown')
            if row is not None and col is not None:
                # Create a key for the position within the sheet
                pos_key = f"{sheet_name}_{row}_{col}"
                if pos_key not in images_by_sheet_position:
                    images_by_sheet_position[pos_key] = []
                images_by_sheet_position[pos_key].append(img)
        
        for sheet_idx, s in enumerate(body.get('sheets', []) or []):
            sheet_name = s.get("sheet_name", "Unknown")
            parts.append(f'## Sheet: {sheet_name}')
            parts.append('')
            
            # Use all_rows if available, otherwise sample_rows
            if 'all_rows' in s and s['all_rows']:
                all_sheet_rows = s['all_rows']
                
                # Create table with images embedded in appropriate cells
                if all_sheet_rows:
                    header_row = all_sheet_rows[0]
                    data_rows = all_sheet_rows[1:] if len(all_sheet_rows) > 1 else []
                    
                    # Create header
                    parts.append('| ' + ' | '.join([str(c) for c in header_row]) + ' |')
                    parts.append('| ' + ' | '.join(['---' for _ in header_row]) + ' |')
                    
                    # Process each data row and embed images
                    for row_idx, row_data in enumerate(data_rows):
                        actual_row_idx = row_idx + 1  # +1 because we skip header
                        processed_row = []
                        
                        for col_idx, cell_value in enumerate(row_data):
                            cell_content = str(cell_value) if cell_value is not None else ''
                            
                            # Check if there's an image at this position for this specific sheet
                            pos_key = f"{sheet_name}_{actual_row_idx}_{col_idx}"
                            if pos_key in images_by_sheet_position:
                                # Add images to this cell with correct relative path
                                for img in images_by_sheet_position[pos_key]:
                                    # Calculate relative path from intermediate artifacts to images
                                    img_relative_path = f"{base_name}_images/{img['filename']}"
                                    cell_content += f" ![{img['filename']}]({img_relative_path})"
                            
                            processed_row.append(cell_content)
                        
                        parts.append('| ' + ' | '.join(processed_row) + ' |')
                    
                parts.append('')
            else:
                # Fallback to original method
                cols = s.get('columns') or []
                sample_rows = s.get('sample_rows') or []
                
                if cols and sample_rows:
                    parts.append('| ' + ' | '.join([str(c) for c in cols]) + ' |')
                    parts.append('| ' + ' | '.join(['---' for _ in cols]) + ' |')
                    
                    for row_idx, r in enumerate(sample_rows):
                        processed_row = []
                        for col_idx, cell_value in enumerate(r):
                            cell_content = str(cell_value) if cell_value is not None else ''
                            
                            # Check for images at this position for this specific sheet
                            pos_key = f"{sheet_name}_{row_idx + 1}_{col_idx}"  # +1 for header offset
                            if pos_key in images_by_sheet_position:
                                for img in images_by_sheet_position[pos_key]:
                                    # Calculate relative path from intermediate artifacts to images
                                    img_relative_path = f"{base_name}_images/{img['filename']}"
                                    cell_content += f" ![{img['filename']}]({img_relative_path})"
                            
                            processed_row.append(cell_content)
                        
                        parts.append('| ' + ' | '.join(processed_row) + ' |')
                    parts.append('')
        
        # Add summary of images at the end for reference
        if all_images:
            parts.append('## Image Summary')
            parts.append('')
            parts.append(f"Total images extracted: {len(all_images)}")
            parts.append('')
            
            # Group images by sheet for better organization
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
        try:
            text, sample = read_text_file(path)
            body = {"file_type": "text", "text_sample": sample, "text_length": len(text), "sensitive_findings": scan_sensitive(text), "is_structured": False}
            intermediate_md = text
        except Exception as e:
            body = {"file_type": "unknown", "error": str(e)}
            
    # Save intermediate markdown artifact
    if intermediate_md and len(intermediate_md.strip()) > 0:
        # Generate output path for intermediate artifact
        base_name = os.path.splitext(meta["file_name"])[0]
        current_task_name = get_current_task_name()
        if current_task_name:
            # Create intermediate_artifacts subdirectory under descriptions
            intermediate_dir = os.path.join(os.path.dirname(os.path.dirname(path)), "descriptions", "intermediate_artifacts")
            os.makedirs(intermediate_dir, exist_ok=True)
            intermediate_path = os.path.join(intermediate_dir, f"{base_name}_intermediate.md")
            
            # 构建标准YAML frontmatter格式
            frontmatter_data = {
                'file_name': meta['file_name'],
                'file_type': body.get('file_type', meta['detected_type']),
                'file_size_bytes': meta['size'],
                'modified_time': meta['modified_time'],
                'is_structured': body.get('is_structured', False),
                'extraction_method': 'document_parser'
            }
            
            # 添加可选字段
            if images and len(images) > 0:
                frontmatter_data['images_extracted'] = len(images)
                frontmatter_data['has_images'] = True
            else:
                frontmatter_data['has_images'] = False
                
            if body.get('row_count'):
                frontmatter_data['total_rows'] = body.get('row_count')
            
            # 如果有图片，添加图片信息
            if images:
                frontmatter_data['extracted_images'] = [
                    {
                        'filename': img['filename'],
                        'size_bytes': img['size_bytes']
                    } for img in images
                ]
            
            with open(intermediate_path, 'w', encoding='utf-8') as f:
                # 写入标准YAML frontmatter
                import yaml
                f.write("---\n")
                f.write(yaml.dump(frontmatter_data, allow_unicode=True, sort_keys=False, default_flow_style=False))
                f.write("---\n\n")
                # 写入正文内容
                f.write(intermediate_md)
                
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
    args = p.parse_args()
    path = args.path
    
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