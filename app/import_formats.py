"""Bounded, strict parsing for user-supplied tabular records. Never executes formulas."""
import base64
import binascii
import csv
import io
import json
from pathlib import PurePath
from zipfile import ZipFile, BadZipFile
from openpyxl import load_workbook

MAX_BYTES = 1_000_000
MAX_ROWS = 10_000

def unique_object(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError('Duplicate JSON field: '+k)
        obj[k] = v
    return obj

def normalize(row, headers, line):
    if set(row) != set(headers):
        raise ValueError(f'Row {line}: fields must match: '+', '.join(headers))
    result = {}
    for k in headers:
        v = row[k]
        if v is None and k in ('latency_ms','detail'):
            v = ''
        if k == 'latency_ms' and type(v) is int:
            v = str(v)
        if not isinstance(v, str):
            raise ValueError(f'Row {line}: {k} must be text (latency_ms may be an integer). Format timestamps as ISO 8601 text with timezone.')
        if len(v)>4096:
            raise ValueError(f'Row {line}: {k} exceeds 4096 characters.')
        result[k] = v
    return result

def parse_upload(filename, encoded, headers):
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError('Invalid file encoding.') from None
    if not raw or len(raw)>MAX_BYTES:
        raise ValueError('Choose a nonempty file of at most 1 MB.')
    ext = PurePath(filename).suffix.lower()
    records = []
    def append(row, line):
        if len(records)>=MAX_ROWS:
            raise ValueError('Maximum 10,000 rows per import.')
        records.append((line, normalize(row, headers, line)))
    def check_headers(h):
        if not h or any(not isinstance(x,str) for x in h) or len(h)!=len(set(h)) or set(h)!=set(headers):
            raise ValueError('Headers must match: '+', '.join(headers))
    try:
        if ext == '.csv':
            reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')), strict=True)
            check_headers(reader.fieldnames)
            for row in reader:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError(f'CSV line {reader.line_num}: wrong number of fields.')
                if any(v.strip() for v in row.values()):
                    append(row, reader.line_num)
        elif ext == '.json':
            rows = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_object)
            if not isinstance(rows,list):
                raise ValueError('JSON must contain an array of record objects.')
            for i,row in enumerate(rows,1):
                if not isinstance(row,dict):
                    raise ValueError(f'Row {i}: expected an object.')
                append(row,i)
        elif ext == '.xlsx':
            # Bound expansion before openpyxl parses the archive; reject macro/embedded files.
            with ZipFile(io.BytesIO(raw)) as archive:
                entries=archive.infolist()
                if len(entries)>250 or sum(x.file_size for x in entries)>16_000_000:
                    raise ValueError('Excel workbook expands beyond the supported size.')
                if any('vbaproject' in x.filename.lower() or '/embeddings/' in x.filename.lower() for x in entries):
                    raise ValueError('Macro or embedded-object workbooks are not supported.')
            workbook=load_workbook(io.BytesIO(raw),read_only=True,data_only=False,keep_links=False)
            try:
                if len(workbook.worksheets)!=1:
                    raise ValueError('Use an Excel workbook containing exactly one worksheet.')
                sheet=workbook.worksheets[0]
                if sheet.max_column and sheet.max_column>len(headers) or sheet.max_row and sheet.max_row>MAX_ROWS+1:
                    raise ValueError('Excel worksheet dimensions exceed the supported limits.')
                it=sheet.iter_rows(max_col=len(headers)+1,max_row=min(sheet.max_row or MAX_ROWS+2,MAX_ROWS+2))
                first=next(it,())
                h=[c.value for c in first]
                while h and h[-1] is None:h.pop()
                check_headers(h)
                for line,cells in enumerate(it,2):
                    if any(getattr(c,'data_type',None) in ('f','e') for c in cells):
                        raise ValueError(f'Row {line}: formulas and Excel error cells are not supported. Paste values instead.')
                    values=[c.value for c in cells]
                    if not any(v is not None and v!='' for v in values):continue
                    if any(v is not None for v in values[len(h):]):
                        raise ValueError(f'Row {line}: unexpected extra column.')
                    append(dict(zip(h,values)),line)
            finally:workbook.close()
        else:
            raise ValueError('Supported file extensions: .csv, .xlsx, .json.')
    except (UnicodeDecodeError,csv.Error,BadZipFile,RecursionError) as exc:
        raise ValueError('Malformed or unsupported file.') from exc
    except ValueError:raise
    except Exception as exc:
        if ext=='.xlsx':raise ValueError('Unable to read this Excel workbook.') from exc
        raise
    if not records:raise ValueError('File has no data rows.')
    return records
