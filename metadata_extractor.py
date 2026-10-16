import base64
import datetime
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

# Force utf-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_DB_PATH = os.path.join(WORKSPACE_DIR, "library_metadata.json")
USAGE_LOG_PATH = os.path.join(WORKSPACE_DIR, "api_usage.json")
SCRATCH_IMG_DIR = os.path.join(WORKSPACE_DIR, "scratch", "extracted_renders")
os.makedirs(SCRATCH_IMG_DIR, exist_ok=True)

# Load API key safely from environment variable or local .env file (do not hardcode)
VISION_API_KEY = os.environ.get("GOOGLE_VISION_API_KEY", "")
if not VISION_API_KEY:
    _env_path = os.path.join(WORKSPACE_DIR, ".env")
    if os.path.exists(_env_path):
        try:
            with open(_env_path, "r", encoding="utf-8") as _f:
                for _line in _f:
                    if _line.strip().startswith("GOOGLE_VISION_API_KEY="):
                        VISION_API_KEY = _line.strip().split("=", 1)[1].strip("'\"")
                        break
        except Exception:
            pass

# Safety limits: Never exceed Google's 1,000 free monthly quota!
MAX_MONTHLY_CALLS = 900
MAX_CALLS_THIS_RUN = 30 

MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]
MONTH_ABBR = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"]

# --- Usage Metering & Safety ---
def get_api_usage():
    if os.path.exists(USAGE_LOG_PATH):
        try:
            with open(USAGE_LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"current_month": datetime.date.today().strftime("%Y-%m"), "month_calls": 0, "total_calls": 0}

def can_make_api_call(run_count):
    if run_count >= MAX_CALLS_THIS_RUN:
        return False, f"Reached run limit of {MAX_CALLS_THIS_RUN} API calls."
    usage = get_api_usage()
    curr_m = datetime.date.today().strftime("%Y-%m")
    month_calls = usage.get("month_calls", 0) if usage.get("current_month") == curr_m else 0
    if month_calls >= MAX_MONTHLY_CALLS:
        return False, f"Monthly safety ceiling reached ({month_calls}/{MAX_MONTHLY_CALLS})."
    return True, None

def record_api_call():
    usage = get_api_usage()
    curr_m = datetime.date.today().strftime("%Y-%m")
    if usage.get("current_month") != curr_m:
        usage["current_month"] = curr_m
        usage["month_calls"] = 0
    usage["month_calls"] = usage.get("month_calls", 0) + 1
    usage["total_calls"] = usage.get("total_calls", 0) + 1
    with open(USAGE_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(usage, f, indent=2)

# --- Metadata DB (Persistent Cache) ---
def load_metadata_db():
    if os.path.exists(METADATA_DB_PATH):
        try:
            with open(METADATA_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_metadata_db(db):
    with open(METADATA_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

# --- Tier 1: Fast Regex on Filename ---
def parse_date_from_filename(filename):
    lower = filename.lower()
    
    # YYYY-MM or YYYY_MM or YYYYMM (e.g. 2021-04, 202405)
    m = re.search(r'\b(20\d\d)[-_ ]?(0[1-9]|1[0-2])\b', lower)
    if m:
        yr = int(m.group(1))
        mo = int(m.group(2))
        return f"{yr}-{mo:02d}", yr, MONTH_NAMES[mo-1].capitalize(), "filename_iso"

    # MM.YY or MM_YY (e.g. 09.20, 12_2023)
    m = re.search(r'\b(0[1-9]|1[0-2])[\._](20\d\d|\d\d)\b', lower)
    if m:
        mo = int(m.group(1))
        yr = int(m.group(2))
        if yr < 100:
            yr += 2000
        return f"{yr}-{mo:02d}", yr, MONTH_NAMES[mo-1].capitalize(), "filename_mmyy"

    # YY-MM (e.g. 19-05, 20-04, 21-11)
    m = re.search(r'\b(19|20|21|22|23|24|25)[-_](0[1-9]|1[0-2])\b', lower)
    if m:
        yr = 2000 + int(m.group(1))
        mo = int(m.group(2))
        return f"{yr}-{mo:02d}", yr, MONTH_NAMES[mo-1].capitalize(), "filename_yymm"

    # Month name + Year (e.g. "January 2020", "May 2024")
    for i, m_name in enumerate(MONTH_NAMES, 1):
        m = re.search(rf'\b{m_name}\b[^\d]*(\b20\d\d\b)', lower)
        if m:
            yr = int(m.group(1))
            return f"{yr}-{i:02d}", yr, m_name.capitalize(), "filename_monthname"

    # Month abbr + Year (e.g. "Jan 2020", "Nov 2023")
    for i, m_abbr in enumerate(MONTH_ABBR, 1):
        m = re.search(rf'\b{m_abbr}\b[^\d]*(\b20\d\d\b)', lower)
        if m:
            yr = int(m.group(1))
            return f"{yr}-{i:02d}", yr, MONTH_NAMES[i-1].capitalize(), "filename_monthabbr"

    return None, None, None, None

# --- Tier 2: Internal Archive Inspection ---
def inspect_archive_contents(filepath):
    if not os.path.exists(SEVEN_ZIP):
        return None, []
        
    cmd = [SEVEN_ZIP, "l", filepath]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace", timeout=20)
        if proc.returncode != 0:
            return None, []
    except Exception:
        return None, []

    lines = proc.stdout.splitlines()
    dates = []
    render_candidates = []
    
    date_regex = re.compile(r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+([D\.\w]+)\s+(\d+)\s+(\d+)?\s+(.*)$')
    for line in lines:
        m = date_regex.match(line.strip())
        if m:
            dt_str, _, attr, size_str, _, fname = m.groups()
            if 'D' not in attr: # not a directory
                try:
                    dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d")
                    if 2018 <= dt.year <= 2026:
                        dates.append(dt)
                except:
                    pass
                ext = os.path.splitext(fname)[1].lower()
                size = int(size_str) if size_str.isdigit() else 0
                # Find promo images / renders (> 50KB to avoid tiny icons)
                if ext in ['.png', '.jpg', '.jpeg'] and size > 50000:
                    render_candidates.append((fname, size))

    if not dates:
        return None, render_candidates

    # Find dominant cluster and max packaging date
    ym_counts = Counter([f"{d.year}-{d.month:02d}" for d in dates])
    most_common_ym, count = ym_counts.most_common(1)[0]
    max_d = max(dates)
    max_ym = f"{max_d.year}-{max_d.month:02d}"

    # Sort renders by size (biggest is usually the main group poster)
    render_candidates.sort(key=lambda x: x[1], reverse=True)
    return {
        "most_common_ym": most_common_ym,
        "max_ym": max_ym,
        "confidence": count / len(dates)
    }, [r[0] for r in render_candidates[:3]]

# --- Extract a specific image from archive to scratch ---
def extract_single_image(archive_path, inner_image_path):
    out_dir = SCRATCH_IMG_DIR
    cmd = [SEVEN_ZIP, "e", archive_path, inner_image_path, f"-o{out_dir}", "-y"]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace", timeout=15)
        if proc.returncode == 0:
            extracted_name = os.path.basename(inner_image_path)
            local_path = os.path.join(out_dir, extracted_name)
            if os.path.exists(local_path):
                return local_path
    except Exception as e:
        pass
    return None

# --- Tier 3: Vision API on extracted promo render ---
def call_vision_api(image_path):
    try:
        with open(image_path, "rb") as f:
            b64_image = base64.b64encode(f.read()).decode("utf-8")
    except:
        return None

    import requests
    url = f"https://vision.googleapis.com/v1/images:annotate?key={VISION_API_KEY}"
    payload = {
        "requests": [
            {
                "image": {"content": b64_image},
                "features": [
                    {"type": "TEXT_DETECTION", "maxResults": 5},
                    {"type": "WEB_DETECTION", "maxResults": 10}
                ]
            }
        ]
    }
    try:
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
        record_api_call()
        if res.status_code == 200:
            return res.json().get("responses", [{}])[0]
    except Exception as e:
        print("Vision API error:", e)
    return None

def parse_vision_data(vision_res):
    if not vision_res:
        return None, None, None, None

    # 1. OCR text parse
    full_text = vision_res.get("fullTextAnnotation", {}).get("text", "")
    if full_text:
        # Search for Month + Year in text (e.g. "January 2024", "Jan 2021", "Oct 2023")
        for i, m_name in enumerate(MONTH_NAMES, 1):
            m = re.search(rf'\b{m_name}\b[^\d\n]*(\b20\d\d\b)', full_text, re.IGNORECASE)
            if m:
                yr = int(m.group(1))
                return f"{yr}-{i:02d}", yr, m_name.capitalize(), "vision_ocr_monthname"

        for i, m_abbr in enumerate(MONTH_ABBR, 1):
            m = re.search(rf'\b{m_abbr}\b[^\d\n]*(\b20\d\d\b)', full_text, re.IGNORECASE)
            if m:
                yr = int(m.group(1))
                return f"{yr}-{i:02d}", yr, MONTH_NAMES[i-1].capitalize(), "vision_ocr_monthabbr"

    # 2. Web matching pages (e.g. URL has date or year)
    web = vision_res.get("webDetection", {})
    matching_pages = web.get("pagesWithMatchingImages", [])
    for p in matching_pages:
        url = p.get("url", "")
        # Check URL for YYYY-MM or Month-YYYY
        m = re.search(r'(20\d\d)[-_/](0[1-9]|1[0-2])', url)
        if m:
            yr = int(m.group(1))
            mo = int(m.group(2))
            return f"{yr}-{mo:02d}", yr, MONTH_NAMES[mo-1].capitalize(), f"vision_web_url ({url})"

    return None, None, None, None

# --- Main Processor ---
def process_folder(folder_path, max_api_calls=10):
    folder_name = os.path.basename(folder_path)
    print(f"\n=======================================================")
    print(f" Processing: {folder_name} ({folder_path})")
    print(f"=======================================================")

    metadata_db = load_metadata_db()
    archive_exts = {'.zip', '.7z', '.rar', '.001', '.z01'}
    
    files = sorted([f for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in archive_exts])
    print(f"Found {len(files)} archive files.\n")

    api_calls_made = 0
    results = []

    for f in files:
        full_path = os.path.join(folder_path, f)
        
        # Check if already processed and cached
        if f in metadata_db:
            cached = metadata_db[f]
            results.append((f, cached.get("releaseDate"), cached.get("method"), "CACHED"))
            continue

        # Step 1: Filename regex
        rel_date, rel_yr, rel_mo, method = parse_date_from_filename(f)
        
        # Step 2: Internal archive check if step 1 was inconclusive
        internal_info = None
        images = []
        if not rel_date:
            internal_info, images = inspect_archive_contents(full_path)
            if internal_info and internal_info.get("confidence", 0) > 0.65:
                # Use internal packaging date
                rel_date = internal_info["most_common_ym"]
                parts = rel_date.split("-")
                rel_yr = int(parts[0])
                rel_mo = MONTH_NAMES[int(parts[1]) - 1].capitalize()
                method = f"internal_freeze_date ({internal_info['confidence']*100:.0f}%)"

        # Step 3: Vision API on promo render (if inconclusive and images exist)
        if (not rel_date or "freeze" in method) and images and api_calls_made < max_api_calls:
            can_call, reason = can_make_api_call(api_calls_made)
            if can_call:
                local_img = extract_single_image(full_path, images[0])
                if local_img:
                    print(f"  [Vision API] Inspecting render for: {f[:45]}...")
                    vision_res = call_vision_api(local_img)
                    api_calls_made += 1
                    v_date, v_yr, v_mo, v_method = parse_vision_data(vision_res)
                    if v_date:
                        rel_date = v_date
                        rel_yr = v_yr
                        rel_mo = v_mo
                        method = v_method
                    # Clean up extracted temp image
                    try:
                        os.remove(local_img)
                    except:
                        pass
            else:
                pass # Rate or quota limit reached, keep internal date

        entry = {
            "filename": f,
            "folder": folder_name,
            "releaseDate": rel_date or "UNKNOWN",
            "releaseYear": rel_yr,
            "releaseMonth": rel_mo,
            "method": method or "unresolved",
            "updatedAt": datetime.datetime.now().isoformat()
        }
        metadata_db[f] = entry
        results.append((f, rel_date or "UNKNOWN", method or "none", "PROCESSED"))

    save_metadata_db(metadata_db)

    # Print summary table
    print(f"\n{'Archive Filename':<52} | {'Release Date':<14} | {'Method / Source'}")
    print("-" * 110)
    for f, d, m, status in results[:25]:
        short_f = (f[:49] + "..") if len(f) > 51 else f
        print(f"{short_f:<52} | {d:<14} | {m}")
    if len(results) > 25:
        print(f"... and {len(results) - 25} more items.")

    print(f"\nFolder complete! API calls used this run: {api_calls_made}")
    return len(results), api_calls_made

if __name__ == "__main__":
    test_folders = [
        r"X:\3d files\3d files\fantasy\cast n play",
        r"X:\3d files\3d files\fantasy\archvillain",
        r"X:\3d files\3d files\fantasy\LOOT studios",
    ]
    total_files = 0
    total_calls = 0
    for folder in test_folders:
        if os.path.exists(folder):
            n_files, n_calls = process_folder(folder, max_api_calls=5)
            total_files += n_files
            total_calls += n_calls

    usage = get_api_usage()
    print(f"\n=======================================================")
    print(f" ALL DONE! Processed {total_files} archives.")
    print(f" Total API calls used: {total_calls}")
    print(f" Month API usage to date: {usage.get('month_calls')}/{MAX_MONTHLY_CALLS}")
    print(f" Metadata saved to: library_metadata.json")
    print(f"=======================================================\n")
