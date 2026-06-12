#!/usr/bin/env python
"""
Extract weekly report data from Excel to JSON.
Usage: python extract_data.py <excel_file.xlsx> [output.json]

Reads the Anta retail weekly report Excel format and extracts
all data tables into extracted_data.json for build_dashboard.py.
"""
import json, sys, os

def find_row(sheet, keyword, col=1):
    """Find row number containing keyword in given column."""
    for row in range(1, 250):
        cell = sheet.cell(row=row, column=col).value
        if cell and keyword in str(cell):
            return row
    return 0

def cv(sheet, row, col):
    """Get cell value safely."""
    cell = sheet.cell(row=row, column=col)
    if not cell or cell.value is None:
        return None
    v = str(cell.value)
    if v in ('#DIV/0!', '/', 'DIV/0'):
        return None
    try:
        return float(v) if '.' in v else int(v)
    except:
        return cell.value

def extract(excel_path):
    import openpyxl
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheets = wb.sheetnames
    
    # Find main data sheet (contains 'KPI' in column A around row 7)
    ws_main = None
    for sname in sheets:
        ws = wb[sname]
        for r in range(1, 20):
            cell = ws.cell(row=r, column=1).value
            if cell and 'KPI' in str(cell):
                ws_main = ws
                break
        if ws_main:
            break
    
    if not ws_main:
        # Fallback: find sheet with most data
        for sname in sheets:
            ws = wb[sname]
            if ws.max_row > 50:
                ws_main = ws
                break
    
    if not ws_main:
        raise ValueError("Cannot find main data sheet (KPI row not found)")
    
    # Find seasonal sheet (contains '产品季')
    ws_seas = None
    for sname in sheets:
        ws = wb[sname]
        if find_row(ws, '产品季', 4):
            ws_seas = ws
            break
    
    # Find member sheet (contains '工号')
    ws_member = None
    for sname in sheets:
        ws = wb[sname]
        if find_row(ws, '工号', 1):
            ws_member = ws
            break
    
    result = {}
    
    # --- r7_kpi: main KPI table (row with 'KPI')
    kpi_row = find_row(ws_main, 'KPI') or 7
    r7 = {}
    for c in [4,5,6,7,8,10,12,14,17,20,22,24,28,33,35,36,37,39]:
        r7[str(c)] = cv(ws_main, kpi_row, c)
    result['r7_kpi'] = r7
    
    # --- r15_price: price/avg ticket (row with '件单价')
    price_row = find_row(ws_main, '件单价') or kpi_row + 8
    r15 = {}
    for c in [4,6,8,10,12,14,16,18,20,22,24,28,30,32]:
        r15[str(c)] = cv(ws_main, price_row, c)
    result['r15_price'] = r15
    
    # --- daily: daily breakdown (14 rows after KPI row)
    daily_start = kpi_row + 14
    day_cols = [4,6,8,10,12,14,16,18]
    day_names = ['周一','周二','周三','周四','周五','周六','周日']
    daily = {}
    for r_offset, dk in enumerate(['21','22','23','24','27','28','29','30']):
        daily[dk] = {'data': {}}
        for i, dc in enumerate(day_cols):
            col_key = str(dc + r_offset)  # This is approximate
            # Actually, the daily data is organized by rows, not columns
            # Need to understand the actual Excel structure better
            pass
    # TODO: Need actual Excel file to determine exact cell mappings
    result['daily'] = daily
    
    # --- category: category data
    cate_start = find_row(ws_main, '吊牌价') or 35
    cate = {}
    for r_offset in range(25):
        row = cate_start + r_offset
        label = cv(ws_main, row, 1)
        if label:
            cate[str(row)] = {'label': str(label), 'data': {}}
            for c in [4,6,8,10,12,14,16,18]:
                v = cv(ws_main, row, c)
                if v is not None:
                    cate[str(row)]['data'][str(c)] = v
    result['category'] = cate
    
    # Placeholder for other sections
    result['top_goods'] = {}
    result['seasonal'] = {}
    result['member'] = {}
    result['sub_ps'] = {}
    result['shoe_series'] = {}
    
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_data.py <excel_file.xlsx> [output.json]")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'extracted_data.json'
    
    if not os.path.exists(excel_path):
        print(f"Error: {excel_path} not found")
        sys.exit(1)
    
    print(f"Extracting from {excel_path}...")
    data = extract(excel_path)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Data extracted to {output_path}")
    print("NOTE: This script is a scaffold. The daily/top_goods/seasonal "
          "sections need the actual Excel structure to be fully implemented.")
    print("See build_dashboard.py for the expected JSON structure.")

if __name__ == '__main__':
    main()
