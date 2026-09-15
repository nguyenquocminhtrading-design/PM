import os
import re
import pandas as pd
import openpyxl
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings

warnings.filterwarnings("ignore")

# Define target folder and result folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
RESULT_DIR = os.path.join(BASE_DIR, "result")

os.makedirs(RESULT_DIR, exist_ok=True)

def map_ticker(filepath):
    up_path = filepath.upper()

    if "DCBF" in up_path or "VFMVFB" in up_path or "VFB" in up_path:
        return "DCBF"
    elif "DCIP" in up_path:
        return "DCIP"
    elif "DCDE" in up_path:
        return "DCDE"
    elif "DIAMOND" in up_path or "FUEVFVND" in up_path:
        return "Diamond"
    elif any(x in up_path for x in ["DCDS", "VFMVF1", "VF1", "VFMVF4", "VF4", "DCBC"]):
        return "DCDS"
    else:
        return "OTHER"

def extract_nav_from_file(filepath):
    filename = os.path.basename(filepath)
    ticker = map_ticker(filepath)
    if ticker == "OTHER":
        return None

    date_str = None
    nav = None

    try:
        xl = pd.ExcelFile(filepath)
    except Exception:
        return None

    # Strategy 1: Check Sheet 'Gia tri tai san rong' or 'GiaTrịTaiSanRong_...'
    for sheet in xl.sheet_names:
        if "Gia" in sheet or "NAV" in sheet:
            try:
                df = xl.parse(sheet)
                for col in df.columns:
                    c_str = str(col)
                    if any(kw in c_str for kw in ["trên 1 đơn vị quỹ", "trên một đơn vị quỹ", "NAV per unit"]):
                        for val in df[col]:
                            try:
                                v = float(val)
                                if v > 100:
                                    nav = v
                                    break
                            except Exception:
                                pass
                    if nav: break
            except Exception:
                pass
        if nav: break

    # Strategy 2: Check Sheet 1 (PLXXIV tuan / PL XXIV ngay / PL26 / Kỳ báo cáo)
    if not nav and len(xl.sheet_names) > 0:
        try:
            df1 = xl.parse(xl.sheet_names[0])

            # Try to find 'Kỳ báo cáo' column or row with NAV per unit
            target_col_idx = None
            for r in range(min(15, len(df1))):
                for c in range(df1.shape[1]):
                    cell_val = str(df1.iloc[r, c])
                    if any(kw in cell_val for kw in ["Kỳ báo cáo", "Kỳ báo cáo", "This period", "kỳ báo cáo"]):
                        target_col_idx = c
                        m_date = re.search(r"(\d{2})[/.-](\d{2})[/.-](\d{4})", cell_val)
                        if m_date:
                            d, m_m, y = m_date.groups()
                            date_str = f"{y}-{m_m}-{d}"
                        break
                if target_col_idx is not None: break

            # Search for NAV cell in rows
            for r in range(len(df1)):
                row_vals = df1.iloc[r].tolist()
                row_txt = " ".join(str(v) for v in row_vals)

                if any(kw in row_txt for kw in ["trên một đơn vị quỹ", "trên 1 đơn vị quỹ", "per Fund Certificate", "NAV per unit"]):
                    # Look for numerical values in row
                    for v in row_vals:
                        try:
                            fv = float(v)
                            # Exclude item code numbers like 4067.1 or 1.3 or 2.3
                            if fv > 100 and fv != 4067.1:
                                nav = fv
                                break
                        except Exception:
                            pass
                    if nav: break
        except Exception:
            pass

    # Extract date from filename if not found in sheet
    if not date_str:
        m = re.search(r"(\d{2})(\d{2})(\d{4})", filename)
        if m:
            d, m_m, y = m.groups()
            if 1 <= int(d) <= 31 and 1 <= int(m_m) <= 12 and 2010 <= int(y) <= 2030:
                date_str = f"{y}-{m_m}-{d}"

    if date_str and nav is not None:
        return {"Date": date_str, "Ticker": ticker, "NAV": nav, "File": filename}
    return None

def process_all_files():
    all_files = []
    for root, dirs, filenames in os.walk(DOWNLOADS_DIR):
        for f in filenames:
            if f.endswith(".xlsx") and not f.startswith("~$"):
                all_files.append(os.path.join(root, f))

    print(f"Scanning {len(all_files)} Excel files...")
    results = []

    # Parallel process across CPU cores
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(extract_nav_from_file, f) for f in all_files]
        count = 0
        for future in as_completed(futures):
            count += 1
            if count % 2000 == 0 or count == len(all_files):
                print(f"Processed {count}/{len(all_files)} files...")
            res = future.result()
            if res:
                results.append(res)

    print(f"Successfully extracted {len(results)} NAV records.")
    
    if not results:
        print("No NAV records found!")
        return

    df_raw = pd.DataFrame(results)
    
    # Drop duplicates by Date & Ticker, keep first valid NAV
    df_clean = df_raw.drop_duplicates(subset=["Date", "Ticker"], keep="first")
    
    # Pivot matrix: Index = Date, Columns = Ticker
    df_pivot = df_clean.pivot(index="Date", columns="Ticker", values="NAV")
    df_pivot.sort_index(inplace=True)

    # Save combined nav matrix
    out_path = os.path.join(RESULT_DIR, "nav_combined.csv")
    df_pivot.to_csv(out_path)
    print(f"Saved combined NAV matrix to {out_path}")
    print(df_pivot.tail(10))

if __name__ == "__main__":
    process_all_files()
