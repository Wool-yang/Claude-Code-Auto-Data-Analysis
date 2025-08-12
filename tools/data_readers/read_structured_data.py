import argparse
from pathlib import Path
import pandas as pd
import math
import json
import chardet
from charset_normalizer import from_bytes
import ftfy
import codecs

def try_read_csv(path, nrows=None):
    import unicodedata
    seps = [',', '\t', ';', '|']
    # read first bytes and full raw
    with open(path, 'rb') as fh:
        raw_head = fh.readline(32768)
        fh.seek(0)
        raw_all = fh.read()
    # BOM-based quick detection
    bom_encoding = None
    try:
        if raw_all.startswith(codecs.BOM_UTF8):
            bom_encoding = 'utf-8-sig'
        elif raw_all.startswith(codecs.BOM_UTF16_LE) or raw_all.startswith(codecs.BOM_UTF16_BE):
            bom_encoding = 'utf-16'
    except Exception:
        bom_encoding = None
    # detector results using full content
    try:
        ch_full = chardet.detect(raw_all)
    except Exception:
        ch_full = {'encoding': None, 'confidence': 0}
    try:
        cn_matches_full = from_bytes(raw_all)
        try:
            cn_best_full = cn_matches_full.best()
            cn_best_enc = getattr(cn_best_full, 'encoding', None)
            cn_conf = getattr(cn_best_full, 'confidence', None) if hasattr(cn_best_full, 'confidence') else None
        except Exception:
            cn_best_full = None
            cn_best_enc = None
            cn_conf = None
    except Exception:
        cn_matches_full = None
        cn_best_full = None
        cn_best_enc = None
        cn_conf = None
    # build candidate list
    common = ['utf-8-sig', 'utf-8', 'gb18030', 'gbk', 'cp936', 'cp1252', 'latin1']
    candidates = []
    if bom_encoding:
        candidates.append(bom_encoding)
    if cn_best_enc:
        candidates.append(cn_best_enc)
    if ch_full.get('encoding'):
        candidates.append(ch_full.get('encoding'))
    for c in common:
        if c not in candidates:
            candidates.append(c)
    # normalize case
    candidates = [c.lower() for c in candidates if c]
    # scoring: prefer decodings with high printable ratio and CJK presence when applicable
    best_score = -1.0
    best_enc = None
    best_text = None
    for enc in candidates:
        try:
            text = raw_all.decode(enc, errors='replace')
        except Exception:
            continue
        if not text:
            continue
        total = len(text)
        if total == 0:
            continue
        replace_count = text.count('\ufffd')
        printable = sum(1 for ch in text if (ch.isprintable() or ch.isspace()))
        printable_ratio = printable / total
        cjk_count = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
        cjk_ratio = cjk_count / total
        # detector confidence boosts
        conf_boost = 0.0
        if enc == (ch_full.get('encoding') or '').lower():
            conf_boost += float(ch_full.get('confidence') or 0) * 0.5
        if enc == (cn_best_enc or '').lower():
            try:
                conf_boost += float(cn_conf or 0) * 0.5
            except Exception:
                conf_boost += 0.0
        score = printable_ratio - (replace_count / max(1, total)) + min(1.0, cjk_ratio * 2.0) + conf_boost
        if score > best_score:
            best_score = score
            best_enc = enc
            best_text = text
    # fallback
    if not best_enc:
        best_enc = 'utf-8'
        try:
            best_text = raw_all.decode(best_enc, errors='replace')
        except Exception:
            best_text = raw_all.decode('latin1', errors='replace')
    # detect separator from first non-empty line
    first_line = ''
    for ln in best_text.splitlines():
        if ln.strip():
            first_line = ln
            break
    detected_sep = ','
    if first_line:
        sep_counts = {sep: first_line.count(sep) for sep in seps}
        detected_sep = max(sep_counts, key=sep_counts.get)
        if sep_counts[detected_sep] == 0:
            detected_sep = ','
    # try parse CSV with chosen encoding and seps
    import io
    parse_errors = []
    df = None
    try:
        text = best_text
        try_seps = [detected_sep] + [s for s in seps if s != detected_sep]
        for sep in try_seps:
            try:
                df = pd.read_csv(io.StringIO(text), sep=sep, engine='python', nrows=nrows)
                break
            except Exception as e:
                parse_errors.append(str(e))
                df = None
        if df is None:
            # as last resort, let pandas sniff using bytes with python engine
            with open(path, 'rb') as fh:
                raw = fh.read()
            for enc in [best_enc, 'utf-8', 'gb18030', 'latin1']:
                try:
                    text = raw.decode(enc, errors='replace')
                    df = pd.read_csv(io.StringIO(text), sep=None, engine='python', nrows=nrows)
                    best_enc = enc
                    break
                except Exception:
                    df = None
            if df is None:
                raise ValueError('parse failed: ' + str(parse_errors))
    except Exception as e:
        raise ValueError(f"无法读取 CSV: {path}. decode/parse errors: {e}")
    # prepare columns: prefer reconstructed header from decoded first line
    header_line = first_line or ''
    header_cols = []
    if header_line:
        try:
            with open(path, 'rb') as fh:
                first = fh.readline(32768)
            forced = first.decode(best_enc, errors='replace')
            parts = forced.split(detected_sep)
        except Exception:
            parts = header_line.split(detected_sep)
        for part in parts:
            s = part.lstrip('\ufeff')
            s = unicodedata.normalize('NFKC', s)
            s = s.strip()
            if any(x in s for x in ['ï»¿', 'Ã', 'â', 'í', 'å', 'è', 'ç']):
                try:
                    recovered = s.encode('cp1252').decode('utf-8')
                    s = recovered
                except Exception:
                    try:
                        recovered = s.encode('latin1').decode('utf-8')
                        s = recovered
                    except Exception:
                        try:
                            recovered = s.encode('cp1252').decode('gbk', errors='ignore')
                            s = recovered
                        except Exception:
                            pass
            s = ''.join(ch for ch in s if (ch.isalnum() or ch.isspace() or ch in ['_', '-', '(', ')']))
            s = s.strip()
            header_cols.append(s if s else None)
    raw_cols = list(df.columns)
    if header_cols and len(header_cols) == len(raw_cols):
        df.columns = header_cols
    recovered_columns = header_cols if header_cols else raw_cols
    ftfy_fixed = [ftfy.fix_text(str(c)) if c is not None else None for c in recovered_columns]
    clean_columns = [ (c if c is not None and c.strip() else f'col_{i+1}') for i,c in enumerate(ftfy_fixed) ]
    df.columns = clean_columns
    has_header = not all([c is None for c in clean_columns])
    return {'df': df, 'encoding': best_enc, 'sep': detected_sep, 'has_header': has_header, 'raw_columns': raw_cols, 'recovered_columns': recovered_columns, 'ftfy_fixed_columns': ftfy_fixed, 'clean_columns': clean_columns, 'decoded_header_sample': header_line}


def try_read_excel(path, nrows=None):
    df = pd.read_excel(path, nrows=nrows)
    cols = list(df.columns)
    has_header = not all([str(c).startswith('Unnamed') for c in cols])
    return {'df': df, 'encoding': None, 'sep': None, 'has_header': has_header}


def read_any(path, nrows=None):
    p = Path(path)
    if p.suffix.lower() in ['.csv', '.txt']:
        return try_read_csv(p, nrows=nrows)
    if p.suffix.lower() in ['.xls', '.xlsx']:
        return try_read_excel(p, nrows=nrows)
    raise ValueError('不支持的文件类型: ' + str(p))


def uniform_sample_dataframe(df, sample_n):
    """
    对DataFrame进行均匀抽样
    
    Args:
        df: pandas DataFrame
        sample_n: 抽样数量
    
    Returns:
        抽样后的DataFrame
    """
    total_rows = len(df)
    if total_rows <= sample_n:
        return df
    
    # 计算均匀间隔
    step = total_rows / sample_n
    indices = []
    
    for i in range(sample_n):
        # 计算每个抽样点的位置，使用四舍五入确保均匀分布
        index = int(round(i * step))
        # 确保索引不超出范围
        if index >= total_rows:
            index = total_rows - 1
        indices.append(index)
    
    # 去重并排序，确保索引的唯一性和顺序
    indices = sorted(list(set(indices)))
    
    # 如果去重后数量不足，补充尾部数据
    if len(indices) < sample_n:
        remaining = sample_n - len(indices)
        # 从末尾开始向前取数据，避免与已有索引重复
        for i in range(remaining):
            candidate_index = total_rows - 1 - i
            if candidate_index not in indices and candidate_index >= 0:
                indices.append(candidate_index)
        indices = sorted(indices)
    
    return df.iloc[indices]


def gather_hard_info(file_path, read_result, sample_n, uniform_sampling=True):
    p = Path(file_path)
    df = read_result['df']
    row_count = len(df)
    columns = read_result.get('clean_columns') or list(df.columns)
    raw_columns = read_result.get('raw_columns') or list(df.columns)
    column_count = len(columns)
    
    # 根据参数选择抽样方式
    if uniform_sampling:
        sample_df = uniform_sample_dataframe(df, sample_n)
        sample_rows = sample_df.to_dict(orient='records')
        sampling_method = 'uniform'
    else:
        sample_rows = df.head(sample_n).to_dict(orient='records')
        sampling_method = 'head'
    
    info = {
        'file_name': p.name,
        'file_type': p.suffix.lstrip('.'),
        'size': p.stat().st_size if p.exists() else None,
        'row_count': row_count,
        'column_count': column_count,
        'columns': columns,
        'raw_columns': raw_columns,
        'sample_rows': sample_rows,
        'sampling_method': sampling_method,  # 新增字段记录抽样方式
        'encoding': read_result.get('encoding'),
        'delimiter': read_result.get('sep'),
        'has_header': read_result.get('has_header'),
        'decoded_header_sample': read_result.get('decoded_header_sample')
    }
    return info


def main():
    import sys, os, io
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument('--files', nargs='+', required=True)
    parser.add_argument('--sample_rows', type=int, default=10)
    parser.add_argument('--head_rows', type=int, default=None)
    parser.add_argument('--head_sampling', action='store_true', help='使用头部抽样而不是均匀抽样（默认为均匀抽样）')
    parser.add_argument('--emit_schema', action='store_true', help='输出CLAUDE.md标准schema格式（向后兼容）')
    parser.add_argument('--intermediate', action='store_true', help='输出中间分析结果供DataSourceFileAnalysisAgent使用')
    parser.add_argument('--temp_output', type=str, default=None)
    args = parser.parse_args()

    for f in args.files:
        try:
            res = read_any(f, nrows=args.head_rows)
        except Exception as e:
            out = json.dumps({'file': f, 'error': str(e)}, ensure_ascii=False)
            try:
                sys.stdout.buffer.write(out.encode('utf-8') + b"\n")
                sys.stdout.buffer.flush()
            except Exception:
                sys.stdout.write(out + "\n")
            continue
        info = gather_hard_info(f, res, args.sample_rows, uniform_sampling=not args.head_sampling)
        df = res.get('df')
        columns_meta = []
        try:
            for col in info.get('columns', []):
                try:
                    ser = df[col]
                except Exception:
                    ser = df.iloc[:, 0] if df.shape[1] > 0 else pd.Series([], dtype='object')
                col_type = 'unknown'
                try:
                    if pd.api.types.is_integer_dtype(ser):
                        col_type = 'integer'
                    elif pd.api.types.is_float_dtype(ser):
                        col_type = 'numeric'
                    elif pd.api.types.is_bool_dtype(ser):
                        col_type = 'boolean'
                    else:
                        try:
                            pd.to_datetime(ser.dropna(), errors='raise')
                            col_type = 'datetime'
                        except Exception:
                            nunique = ser.nunique(dropna=True)
                            if len(ser) > 0 and nunique < max(5, 0.05 * len(ser)) and nunique < 100:
                                col_type = 'categorical'
                            else:
                                col_type = 'text'
                except Exception:
                    col_type = 'unknown'
                try:
                    sample_vals = ser.head(5).where(pd.notnull(ser.head(5)), None).tolist()
                except Exception:
                    sample_vals = []
                columns_meta.append({'name': col, 'type': col_type, 'sample_values': sample_vals})
        except Exception:
            columns_meta = []

        # 生成中间分析结果 - 为DataSourceFileAnalysisAgent提供硬数据
        intermediate_result = {
            'analysis_type': 'structured_data',
            'file_info': {
                'file_name': info.get('file_name'),
                'file_type': info.get('file_type'),
                'file_size': info.get('size')
            },
            'data_structure': {
                'row_count': info.get('row_count'),
                'column_count': info.get('column_count'),
                'columns_analysis': columns_meta,
                'raw_columns': info.get('raw_columns', []),
                'clean_columns': info.get('clean_columns', [])
            },
            'parsing_metadata': {
                'encoding': info.get('encoding'),
                'delimiter': info.get('delimiter'),
                'has_header': info.get('has_header'),
                'decoded_header_sample': info.get('decoded_header_sample', '')
            },
            'sample_data': {
                'sample_rows': info.get('sample_rows', []),
                'sample_count': len(info.get('sample_rows', [])),
                'sampling_method': info.get('sampling_method', 'uniform')  # 记录抽样方式
            },
            'processing_notes': {
                'ftfy_fixed_columns': info.get('ftfy_fixed_columns', []),
                'recovered_columns': info.get('recovered_columns', [])
            }
        }

        # 保留原有的schema输出选项用于向后兼容
        wrapper = {
            'file_name': info.get('file_name'),
            'file_type': info.get('file_type'),
            'is_structured': True,  # 由read_structured_data.py处理的都是结构化数据
            'size': info.get('size'),
            'description': '',
            'structure': {
                'row_count': info.get('row_count'),
                'column_count': info.get('column_count'),
                'columns': columns_meta
            },
            'metadata': {
                'encoding': info.get('encoding'),
                'delimiter': info.get('delimiter'),
                'has_header': info.get('has_header')
            },
            'tags': []
        }

        if args.emit_schema:
            out = json.dumps(wrapper, ensure_ascii=False, indent=2)
        elif args.intermediate:
            out = json.dumps(intermediate_result, ensure_ascii=False, indent=2)
        else:
            out = json.dumps(info, ensure_ascii=False, indent=2)

        try:
            sys.stdout.buffer.write(out.encode('utf-8', errors='replace') + b"\n")
            sys.stdout.buffer.flush()
        except Exception:
            try:
                sys.stdout.write(out + "\n")
                sys.stdout.flush()
            except Exception:
                pass

        if args.temp_output:
            try:
                p = Path(args.temp_output)
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, 'w', encoding='utf-8') as fh:
                    fh.write(out)
            except Exception:
                pass

if __name__ == '__main__':
    main()
