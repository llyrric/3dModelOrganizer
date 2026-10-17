import os
import sys
import json
import shutil
import time
import datetime
from pathlib import Path

BASE_DIR = os.environ.get("STL_LIBRARY_ROOT", r"X:\3d files\3d files")
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
JS_OUT = os.path.join(WORKSPACE_DIR, "library_data.js")
METADATA_PATH = os.path.join(WORKSPACE_DIR, "library_metadata.json")
HISTORY_LOG = os.path.join(WORKSPACE_DIR, "moves_history.json")

_library_cache = None
_library_mtime = 0

def load_library_data(force_reload=False):
    """Loads and caches libraryData from library_data.js."""
    global _library_cache, _library_mtime
    if not os.path.exists(JS_OUT):
        return []

    mtime = os.path.getmtime(JS_OUT)
    if not force_reload and _library_cache is not None and mtime == _library_mtime:
        return _library_cache

    with open(JS_OUT, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if content.startswith("const libraryData = "):
        content = content[len("const libraryData = "):]
    if content.endswith(";"):
        content = content[:-1]

    try:
        _library_cache = json.loads(content)
        _library_mtime = mtime
    except Exception as e:
        print(f"[ERROR] Failed to parse library_data.js: {e}", file=sys.stderr)
        if _library_cache is not None:
            return _library_cache
        return []

    return _library_cache

def save_library_data(data):
    """Atomically saves libraryData back to library_data.js with a backup."""
    global _library_cache, _library_mtime
    _library_cache = data

    # Create temporary file
    temp_path = JS_OUT + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write("const libraryData = " + json.dumps(data, ensure_ascii=False) + ";")

    # Atomic rename (on Windows, use replace)
    os.replace(temp_path, JS_OUT)
    _library_mtime = os.path.getmtime(JS_OUT)

def load_metadata():
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_metadata(metadata):
    temp_path = METADATA_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, METADATA_PATH)

def log_move_history(record):
    history = []
    if os.path.exists(HISTORY_LOG):
        try:
            with open(HISTORY_LOG, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    history.append(record)
    with open(HISTORY_LOG, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def get_library_structure():
    """
    Returns a dictionary of all categories and their creator folders,
    combining folders discovered on disk in BASE_DIR with libraryData entries.
    """
    categories_set = set()
    folders_by_cat = {}

    # 1. From disk
    if os.path.exists(BASE_DIR):
        try:
            for cat in os.listdir(BASE_DIR):
                cat_path = os.path.join(BASE_DIR, cat)
                if os.path.isdir(cat_path):
                    categories_set.add(cat)
                    if cat not in folders_by_cat:
                        folders_by_cat[cat] = set()
                    try:
                        for creator in os.listdir(cat_path):
                            if os.path.isdir(os.path.join(cat_path, creator)):
                                folders_by_cat[cat].add(creator)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[WARN] Error scanning disk structure: {e}")

    # 2. From libraryData
    lib_data = load_library_data()
    for col in lib_data:
        cat = col.get("Category", "")
        creator = col.get("Creator", "")
        if cat:
            categories_set.add(cat)
            if cat not in folders_by_cat:
                folders_by_cat[cat] = set()
            if creator:
                folders_by_cat[cat].add(creator)

    # Convert sets to sorted lists
    sorted_categories = sorted(list(categories_set), key=lambda s: s.lower())
    result_folders = {}
    for cat in sorted_categories:
        result_folders[cat] = sorted(list(folders_by_cat.get(cat, set())), key=lambda s: s.lower())

    return {
        "categories": sorted_categories,
        "foldersByCategory": result_folders
    }

def clean_file_display_name(raw_name):
    """
    Extracts the base physical archive/file name if the name is an extracted model path.
    e.g. 'Archive.zip ➔ Model.stl' -> ('Archive.zip', 'Model.stl')
    """
    if " ➔ " in raw_name:
        parts = raw_name.split(" ➔ ")
        return parts[0].strip(), parts[1].strip()
    return raw_name.strip(), None

def find_file_on_disk(source_cat, source_creator, file_name, inner_model=None):
    """
    Locates the file on disk inside BASE_DIR / source_cat / source_creator.
    Handles nested subdirectories and resolves ambiguities if multiple matches exist.
    """
    disk_file_name, detected_inner = clean_file_display_name(file_name)
    if not inner_model and detected_inner:
        inner_model = detected_inner

    creator_path = os.path.join(BASE_DIR, source_cat, source_creator)
    if not os.path.exists(creator_path):
        # Fallback: check if source_cat alone contains it, or search categories
        return None, disk_file_name, []

    # 1. Direct match at root of creator folder
    direct_path = os.path.join(creator_path, disk_file_name)
    if os.path.exists(direct_path):
        return direct_path, disk_file_name, []

    # 2. Search recursively in creator folder
    matches = []
    for root, _, files in os.walk(creator_path):
        for f in files:
            if f.lower() == disk_file_name.lower():
                matches.append(os.path.join(root, f))

    if not matches:
        return None, disk_file_name, []

    if len(matches) == 1:
        return matches[0], disk_file_name, []

    # Ambiguity resolution using inner model if available
    if inner_model:
        for m in matches:
            ext = os.path.splitext(m)[1].lower()
            if ext == '.zip':
                try:
                    import zipfile
                    with zipfile.ZipFile(m, 'r') as zf:
                        if any(inner_model.lower() in name.lower() for name in zf.namelist()):
                            return m, disk_file_name, matches
                except Exception:
                    pass

    return matches[0], disk_file_name, matches

def find_companion_files(main_file_path):
    """
    Finds split archive parts and preview files sharing the same base stem in the same folder.
    e.g., model.z01, model.z02, model.jpg, model.png
    """
    folder = os.path.dirname(main_file_path)
    base_name = os.path.basename(main_file_path)
    stem, ext = os.path.splitext(base_name)
    stem_lower = stem.lower()
    ext_lower = ext.lower()

    companions = []
    try:
        for f in os.listdir(folder):
            if f.lower() == base_name.lower():
                continue
            f_stem, f_ext = os.path.splitext(f)
            f_stem_lower = f_stem.lower()
            f_ext_lower = f_ext.lower()

            # Split zip (.z01, .z02, etc.)
            if ext_lower == '.zip' and (f_stem_lower == stem_lower or f_stem_lower.startswith(stem_lower)):
                if f_ext_lower.startswith('.z') and f_ext_lower[2:].isdigit():
                    companions.append(os.path.join(folder, f))

            # Split 7z (.7z.001, .7z.002, etc.)
            if '.7z.' in f.lower() and stem_lower in f_stem_lower:
                companions.append(os.path.join(folder, f))

            # Split rar (.part1.rar, .part2.rar)
            if ext_lower == '.rar' and ('.part' in f_stem_lower) and (stem_lower.split('.part')[0] in f_stem_lower):
                companions.append(os.path.join(folder, f))

            # Companion preview image with matching stem
            if f_ext_lower in ['.jpg', '.jpeg', '.png', '.webp'] and f_stem_lower == stem_lower:
                companions.append(os.path.join(folder, f))

    except Exception:
        pass

    return companions

def move_file(source_cat, source_creator, file_display_name, dest_cat, dest_creator,
              new_file_name=None, move_companions=True, conflict_action="rename"):
    """
    Safely moves a file on disk and updates library_data.js and library_metadata.json.
    """
    source_cat = source_cat.strip()
    source_creator = source_creator.strip()
    dest_cat = dest_cat.strip()
    dest_creator = dest_creator.strip()

    if not dest_cat or not dest_creator:
        raise ValueError("Destination Category and Folder/Creator must be provided.")

    disk_file_name, inner_model = clean_file_display_name(file_display_name)
    target_file_name = new_file_name.strip() if new_file_name and new_file_name.strip() else disk_file_name

    # 1. Locate file on disk
    source_path, _, candidate_matches = find_file_on_disk(source_cat, source_creator, file_display_name, inner_model)
    if not source_path or not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file '{disk_file_name}' not found under '{source_cat}/{source_creator}'.")

    # 2. Companion files
    companion_paths = []
    if move_companions:
        companion_paths = find_companion_files(source_path)

    # 3. Destination folder setup
    dest_folder = os.path.join(BASE_DIR, dest_cat, dest_creator)
    os.makedirs(dest_folder, exist_ok=True)

    dest_path = os.path.join(dest_folder, target_file_name)

    # 4. Handle collisions
    if os.path.exists(dest_path) and os.path.abspath(dest_path).lower() != os.path.abspath(source_path).lower():
        if conflict_action == "overwrite":
            pass
        elif conflict_action == "rename":
            stem, ext = os.path.splitext(target_file_name)
            counter = 1
            while os.path.exists(dest_path):
                target_file_name = f"{stem}_{counter}{ext}"
                dest_path = os.path.join(dest_folder, target_file_name)
                counter += 1
        else:
            raise FileExistsError(f"Destination file already exists: {dest_path}")

    # 5. Move main file on disk
    moved_files = []
    shutil.move(source_path, dest_path)
    moved_files.append({"from": source_path, "to": dest_path})

    # Move companions
    moved_companions = []
    for comp in companion_paths:
        comp_name = os.path.basename(comp)
        comp_dest = os.path.join(dest_folder, comp_name)
        if os.path.exists(comp):
            shutil.move(comp, comp_dest)
            moved_companions.append({"from": comp, "to": comp_dest})
            moved_files.append({"from": comp, "to": comp_dest})

    # 6. Update library_data.js
    lib_data = load_library_data(force_reload=True)

    # Find source collection
    src_col = next((c for c in lib_data if c.get("Category") == source_cat and c.get("Creator") == source_creator), None)
    # Find or create dest collection
    dest_col = next((c for c in lib_data if c.get("Category") == dest_cat and c.get("Creator") == dest_creator), None)
    if dest_col is None:
        dest_col = {
            "Category": dest_cat,
            "Creator": dest_creator,
            "TotalFiles": 0,
            "Archives": 0,
            "STLs": 0,
            "PreviewsCount": 0,
            "Thumbnails": [],
            "Items": [],
            "Samples": []
        }
        lib_data.append(dest_col)

    # Identify items in source collection that correspond to disk_file_name
    moved_items = []
    moved_thumbnails = []
    moved_samples = []

    if src_col:
        # Items
        remaining_items = []
        for it in src_col.get("Items", []):
            it_name = it.get("name", "")
            if it_name == disk_file_name or it_name.startswith(disk_file_name + " ➔"):
                # If renamed, adjust name
                if target_file_name != disk_file_name:
                    if it_name == disk_file_name:
                        it["name"] = target_file_name
                    else:
                        it["name"] = target_file_name + " ➔ " + it_name.split(" ➔ ", 1)[1]
                moved_items.append(it)
            else:
                remaining_items.append(it)
        src_col["Items"] = remaining_items

        # Thumbnails
        remaining_thumbs = []
        for th in src_col.get("Thumbnails", []):
            th_name = th.get("Name", "")
            if th_name == disk_file_name or th_name.startswith(disk_file_name + " ➔"):
                if target_file_name != disk_file_name:
                    if th_name == disk_file_name:
                        th["Name"] = target_file_name
                    else:
                        th["Name"] = target_file_name + " ➔ " + th_name.split(" ➔ ", 1)[1]
                moved_thumbnails.append(th)
            else:
                remaining_thumbs.append(th)
        src_col["Thumbnails"] = remaining_thumbs

        # Samples
        remaining_samples = []
        for s in src_col.get("Samples", []):
            if s == disk_file_name or s.startswith(disk_file_name + " ➔"):
                if target_file_name != disk_file_name:
                    if s == disk_file_name:
                        s = target_file_name
                    else:
                        s = target_file_name + " ➔ " + s.split(" ➔ ", 1)[1]
                moved_samples.append(s)
            else:
                remaining_samples.append(s)
        src_col["Samples"] = remaining_samples

        # Recalculate source stats
        src_col["TotalFiles"] = len(src_col["Items"]) if src_col.get("Items") else len(src_col.get("Samples", []))
        src_col["Archives"] = sum(1 for it in src_col.get("Items", []) if it["name"].lower().endswith(('.zip', '.rar', '.7z')) and " ➔ " not in it["name"])
        src_col["STLs"] = sum(1 for it in src_col.get("Items", []) if it["name"].lower().endswith(('.stl', '.obj')) and " ➔ " not in it["name"])
        src_col["PreviewsCount"] = len(src_col.get("Thumbnails", []))

    # Add to destination collection
    dest_col.setdefault("Items", []).extend(moved_items)
    dest_col.setdefault("Thumbnails", []).extend(moved_thumbnails)
    dest_col.setdefault("Samples", []).extend(moved_samples)

    # Recalculate destination stats
    dest_col["TotalFiles"] = len(dest_col["Items"]) if dest_col.get("Items") else len(dest_col.get("Samples", []))
    dest_col["Archives"] = sum(1 for it in dest_col.get("Items", []) if it["name"].lower().endswith(('.zip', '.rar', '.7z')) and " ➔ " not in it["name"])
    dest_col["STLs"] = sum(1 for it in dest_col.get("Items", []) if it["name"].lower().endswith(('.stl', '.obj')) and " ➔ " not in it["name"])
    dest_col["PreviewsCount"] = len(dest_col.get("Thumbnails", []))

    # Save library data
    save_library_data(lib_data)

    # 7. Update metadata if present
    meta = load_metadata()
    if disk_file_name in meta:
        meta_entry = meta.pop(disk_file_name)
        meta_entry["folder"] = dest_creator
        meta_entry["filename"] = target_file_name
        meta_entry["updatedAt"] = datetime.datetime.now().isoformat()
        meta[target_file_name] = meta_entry
        save_metadata(meta)

    # 8. Record in history
    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "type": "file_move",
        "sourceCategory": source_cat,
        "sourceCreator": source_creator,
        "sourceFileName": disk_file_name,
        "destCategory": dest_cat,
        "destCreator": dest_creator,
        "destFileName": target_file_name,
        "movedFiles": moved_files,
        "sourcePath": source_path,
        "destPath": dest_path
    }
    log_move_history(record)

    return {
        "success": True,
        "message": f"Successfully moved '{disk_file_name}' to '{dest_cat} / {dest_creator}'",
        "source": {"category": source_cat, "creator": source_creator, "file": disk_file_name},
        "destination": {"category": dest_cat, "creator": dest_creator, "file": target_file_name},
        "movedFiles": moved_files,
        "companionCount": len(moved_companions),
        "sourceRemainingFiles": src_col["TotalFiles"] if src_col else 0,
        "destTotalFiles": dest_col["TotalFiles"]
    }

def move_collection(source_cat, creator, dest_cat, dest_creator=None):
    """
    Moves an entire creator/collection folder from one category to another.
    """
    source_cat = source_cat.strip()
    creator = creator.strip()
    dest_cat = dest_cat.strip()
    target_creator = dest_creator.strip() if dest_creator and dest_creator.strip() else creator

    src_dir = os.path.join(BASE_DIR, source_cat, creator)
    if not os.path.exists(src_dir):
        raise FileNotFoundError(f"Source collection folder does not exist: {src_dir}")

    dest_parent = os.path.join(BASE_DIR, dest_cat)
    os.makedirs(dest_parent, exist_ok=True)
    dest_dir = os.path.join(dest_parent, target_creator)

    if os.path.exists(dest_dir):
        # Merge contents
        for item in os.listdir(src_dir):
            s_item = os.path.join(src_dir, item)
            d_item = os.path.join(dest_dir, item)
            if os.path.exists(d_item):
                if os.path.isdir(s_item):
                    shutil.copytree(s_item, d_item, dirs_exist_ok=True)
                    shutil.rmtree(s_item)
                else:
                    shutil.move(s_item, d_item)
            else:
                shutil.move(s_item, d_item)
        try:
            os.rmdir(src_dir)
        except Exception:
            pass
    else:
        shutil.move(src_dir, dest_dir)

    # Update library_data.js
    lib_data = load_library_data(force_reload=True)
    for col in lib_data:
        if col.get("Category") == source_cat and col.get("Creator") == creator:
            col["Category"] = dest_cat
            col["Creator"] = target_creator

    save_library_data(lib_data)

    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "type": "collection_move",
        "sourceCategory": source_cat,
        "sourceCreator": creator,
        "destCategory": dest_cat,
        "destCreator": target_creator,
        "sourceDir": src_dir,
        "destDir": dest_dir
    }
    log_move_history(record)

    return {
        "success": True,
        "message": f"Successfully moved collection '{creator}' to category '{dest_cat}'",
        "source": {"category": source_cat, "creator": creator},
        "destination": {"category": dest_cat, "creator": target_creator}
    }

def undo_last_move():
    """
    Reverses the most recent move operation recorded in moves_history.json.
    """
    if not os.path.exists(HISTORY_LOG):
        return {"success": False, "message": "No move history found."}

    with open(HISTORY_LOG, "r", encoding="utf-8") as f:
        history = json.load(f)

    if not history:
        return {"success": False, "message": "History is empty."}

    last_record = history.pop()

    if last_record.get("type") == "file_move":
        # Reverse each file move
        reversed_files = []
        for item in reversed(last_record.get("movedFiles", [])):
            cur_path = item["to"]
            orig_path = item["from"]
            if os.path.exists(cur_path):
                os.makedirs(os.path.dirname(orig_path), exist_ok=True)
                shutil.move(cur_path, orig_path)
                reversed_files.append(orig_path)

        # Update library_data.js back
        # Simply call move_file in reverse direction or re-update collections
        src_cat = last_record["destCategory"]
        src_creator = last_record["destCreator"]
        dest_cat = last_record["sourceCategory"]
        dest_creator = last_record["sourceCreator"]
        file_name = last_record["destFileName"]
        orig_file_name = last_record["sourceFileName"]

        # Update library_data.js in-memory
        lib_data = load_library_data(force_reload=True)
        cur_col = next((c for c in lib_data if c.get("Category") == src_cat and c.get("Creator") == src_creator), None)
        dest_col = next((c for c in lib_data if c.get("Category") == dest_cat and c.get("Creator") == dest_creator), None)

        if cur_col and dest_col is not None:
            items_to_move = [it for it in cur_col.get("Items", []) if it["name"] == file_name or it["name"].startswith(file_name + " ➔")]
            cur_col["Items"] = [it for it in cur_col.get("Items", []) if it not in items_to_move]
            for it in items_to_move:
                if orig_file_name != file_name:
                    if it["name"] == file_name:
                        it["name"] = orig_file_name
                    else:
                        it["name"] = orig_file_name + " ➔ " + it["name"].split(" ➔ ", 1)[1]
                dest_col.setdefault("Items", []).append(it)

            # Recalculate
            for col in [cur_col, dest_col]:
                col["TotalFiles"] = len(col.get("Items", []))
                col["Archives"] = sum(1 for it in col.get("Items", []) if it["name"].lower().endswith(('.zip', '.rar', '.7z')) and " ➔ " not in it["name"])
                col["STLs"] = sum(1 for it in col.get("Items", []) if it["name"].lower().endswith(('.stl', '.obj')) and " ➔ " not in it["name"])

            save_library_data(lib_data)

        # Save remaining history
        with open(HISTORY_LOG, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        return {
            "success": True,
            "message": f"Undid move of '{orig_file_name}' back to '{dest_cat} / {dest_creator}'",
            "reversedFiles": reversed_files
        }

    return {"success": False, "message": "Unknown move record type."}
