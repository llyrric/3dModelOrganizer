import os
import sys
import io
import json
import zipfile
import subprocess
import hashlib
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import trimesh
import cv2

BASE_DIR = os.environ.get("STL_LIBRARY_ROOT", r"X:\3d files\3d files")
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
THUMBS_DIR = os.path.join(WORKSPACE_DIR, "previews")
JS_OUT = os.path.join(WORKSPACE_DIR, "library_data.js")
TEMP_BASE = os.path.join(WORKSPACE_DIR, "scratch")
SEVEN_ZIP = r"C:\Program Files\7-Zip\7z.exe"
TARGET_SIZE = 400
JPEG_QUALITY = 80
NUM_WORKERS = 8  # Balanced for Ryzen 7 5800X 8 cores / 16 threads

os.makedirs(THUMBS_DIR, exist_ok=True)
os.makedirs(TEMP_BASE, exist_ok=True)

def render_mesh_to_thumb(mesh, out_path, size=TARGET_SIZE):
    try:
        # 1. Upright alignment (Z is vertical UP; rotate if Y or X is the tall axis)
        ext = mesh.extents
        if ext[1] > ext[2] * 1.35 and ext[1] > ext[0] * 1.2:
            R_up = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
        elif ext[0] > ext[2] * 1.35 and ext[0] > ext[1] * 1.2:
            R_up = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]])
        else:
            R_up = np.eye(3)

        verts = mesh.vertices @ R_up.T
        norms = mesh.face_normals @ R_up.T
        faces = mesh.faces

        # 2. Check base / right-side up (bases typically have downward-pointing normals at the bottom)
        z_min, z_max = verts[:, 2].min(), verts[:, 2].max()
        z_thresh_bot = z_min + 0.20 * (z_max - z_min)
        z_thresh_top = z_max - 0.20 * (z_max - z_min)
        f_centers_z = verts[faces].mean(axis=1)[:, 2]
        bot_down_faces = (f_centers_z < z_thresh_bot) & (norms[:, 2] < -0.7)
        top_down_faces = (f_centers_z > z_thresh_top) & (norms[:, 2] > 0.7)
        if top_down_faces.sum() > bot_down_faces.sum() * 2 and top_down_faces.sum() > 20:
            R_flip = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]])
            verts = verts @ R_flip.T
            norms = norms @ R_flip.T

        # 3. Smart front angle selection (eye-level elevation + 3/4 hero view)
        elevation = np.radians(16)
        z_mid = (verts[:, 2].min() + verts[:, 2].max()) / 2.0
        f_upper = f_centers_z > z_mid
        best_angle = 135
        best_score = -1e9

        for a in [45, 135, 225, 315]:
            az = np.radians(a)
            cam_dir = np.array([np.cos(elevation) * np.sin(az), -np.cos(elevation) * np.cos(az), np.sin(elevation)])
            cam_dir /= np.linalg.norm(cam_dir)
            fwd = -cam_dir
            w_up = np.array([0.0, 0.0, 1.0])
            r = np.cross(fwd, w_up); r /= np.linalg.norm(r)
            u = np.cross(r, fwd); u /= np.linalg.norm(u)
            R_c = np.vstack([r, u, fwd])
            n_c = norms @ R_c.T
            vis = (n_c[:, 2] < 0) & f_upper
            if vis.sum() > 0:
                score = np.std(n_c[vis], axis=0).sum() * 1000 + vis.sum() * 0.05
                if score > best_score:
                    best_score = score
                    best_angle = a

        # 4. Set up Camera Matrix for the selected front angle
        az = np.radians(best_angle)
        cam_dir = np.array([np.cos(elevation) * np.sin(az), -np.cos(elevation) * np.cos(az), np.sin(elevation)])
        cam_dir /= np.linalg.norm(cam_dir)
        forward = -cam_dir
        world_up = np.array([0.0, 0.0, 1.0])
        right = np.cross(forward, world_up); right /= np.linalg.norm(right)
        up = np.cross(right, forward); up /= np.linalg.norm(up)
        R_cam = np.vstack([right, up, forward])

        vertices_cam = verts @ R_cam.T
        normals_cam = norms @ R_cam.T

        visible = normals_cam[:, 2] < 0
        if not np.any(visible):
            visible = np.ones(len(faces), dtype=bool)

        front_faces = faces[visible]
        front_normals = normals_cam[visible]

        # Two-point studio lighting: Key light + Fill light
        key_light = np.array([0.45, 0.55, -0.7])
        key_light /= np.linalg.norm(key_light)
        fill_light = np.array([-0.5, 0.3, -0.6])
        fill_light /= np.linalg.norm(fill_light)

        dot_key = np.clip(-(front_normals @ key_light), 0.0, 1.0)
        dot_fill = np.clip(-(front_normals @ fill_light), 0.0, 1.0)
        intensity = np.clip(0.20 + 0.65 * dot_key + 0.25 * dot_fill, 0.15, 1.0)

        # 2D projection
        pts_2d = np.column_stack([vertices_cam[:, 0], -vertices_cam[:, 1]])
        p_min = pts_2d.min(axis=0)
        p_max = pts_2d.max(axis=0)
        dim = max(p_max[0] - p_min[0], p_max[1] - p_min[1])
        if dim <= 0:
            return False

        scale = (size * 0.86) / dim
        center = (p_min + p_max) / 2.0
        v_proj = ((pts_2d - center) * scale + (size / 2.0)).astype(np.int32)

        face_z = vertices_cam[front_faces].mean(axis=1)[:, 2]
        order = np.argsort(-face_z)

        img = np.full((size, size, 3), (20, 26, 38), dtype=np.uint8)
        for idx in order:
            pts = v_proj[front_faces[idx]]
            shade = int(intensity[idx] * 215 + 35)
            color = (int(shade * 0.86), int(shade * 0.93), shade)
            cv2.fillPoly(img, [pts], color)

        cv2.imwrite(out_path, img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        return True
    except Exception:
        return False

def process_loose_image(img_path):
    h = hashlib.md5(img_path.encode('utf-8')).hexdigest()[:12]
    out_path = os.path.join(THUMBS_DIR, f"{h}.jpg")
    if os.path.exists(out_path):
        return f"./previews/{h}.jpg"
    try:
        img = cv2.imread(img_path)
        if img is None:
            return None
        h_im, w_im = img.shape[:2]
        scale = TARGET_SIZE / max(h_im, w_im)
        resized = cv2.resize(img, (int(w_im * scale), int(h_im * scale)))
        canvas = np.full((TARGET_SIZE, TARGET_SIZE, 3), (16, 20, 30), dtype=np.uint8)
        y_off = (TARGET_SIZE - resized.shape[0]) // 2
        x_off = (TARGET_SIZE - resized.shape[1]) // 2
        canvas[y_off:y_off+resized.shape[0], x_off:x_off+resized.shape[1]] = resized
        cv2.imwrite(out_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        return f"./previews/{h}.jpg"
    except Exception:
        return None

def process_loose_stl(stl_path):
    h = hashlib.md5(stl_path.encode('utf-8')).hexdigest()[:12]
    out_path = os.path.join(THUMBS_DIR, f"{h}.jpg")
    if os.path.exists(out_path):
        return f"./previews/{h}.jpg"
    try:
        with open(stl_path, 'rb') as fp:
            mesh = trimesh.load(fp, file_type='stl')
            if hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                if render_mesh_to_thumb(mesh, out_path):
                    return f"./previews/{h}.jpg"
    except Exception:
        pass
    return None

def process_zip_archive(arch_path):
    arch_name = os.path.basename(arch_path)
    results = []
    pack_thumb = None

    try:
        with zipfile.ZipFile(arch_path, 'r') as z:
            names = z.namelist()
            # 1. Images
            imgs = [n for n in names if n.lower().endswith(('.jpg', '.png', '.jpeg')) and not '__macosx' in n.lower()]
            for im in imgs:
                im_base = os.path.basename(im)
                if not im_base: continue
                item_key = f"{arch_path}::{im}"
                h = hashlib.md5(item_key.encode('utf-8')).hexdigest()[:12]
                out_path = os.path.join(THUMBS_DIR, f"{h}.jpg")
                if not os.path.exists(out_path):
                    try:
                        img_data = z.read(im)
                        nparr = np.frombuffer(img_data, np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if img is not None:
                            h_im, w_im = img.shape[:2]
                            scale = TARGET_SIZE / max(h_im, w_im)
                            resized = cv2.resize(img, (int(w_im * scale), int(h_im * scale)))
                            canvas = np.full((TARGET_SIZE, TARGET_SIZE, 3), (16, 20, 30), dtype=np.uint8)
                            y_off = (TARGET_SIZE - resized.shape[0]) // 2
                            x_off = (TARGET_SIZE - resized.shape[1]) // 2
                            canvas[y_off:y_off+resized.shape[0], x_off:x_off+resized.shape[1]] = resized
                            cv2.imwrite(out_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                    except Exception:
                        pass
                if os.path.exists(out_path):
                    url = f"./previews/{h}.jpg"
                    if not pack_thumb: pack_thumb = url
                    results.append({"name": f"{arch_name} ➔ {im_base}", "thumb": url, "parent": arch_name})

            # 2. STLs
            raw_stls = [n for n in names if n.lower().endswith('.stl') and not '__macosx' in n.lower() and not n.startswith('._')]
            clean_stls = [n for n in raw_stls if not 'supported' in n.lower() or 'unsupported' in n.lower()]
            stls_to_render = clean_stls if clean_stls else raw_stls

            for s in stls_to_render:
                s_base = os.path.basename(s)
                if not s_base: continue
                item_key = f"{arch_path}::{s}"
                h = hashlib.md5(item_key.encode('utf-8')).hexdigest()[:12]
                out_path = os.path.join(THUMBS_DIR, f"{h}.jpg")
                if not os.path.exists(out_path):
                    try:
                        stl_data = z.read(s)
                        mesh = trimesh.load(io.BytesIO(stl_data), file_type='stl')
                        if hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                            render_mesh_to_thumb(mesh, out_path)
                    except Exception:
                        pass
                if os.path.exists(out_path):
                    url = f"./previews/{h}.jpg"
                    if not pack_thumb: pack_thumb = url
                    results.append({"name": f"{arch_name} ➔ {s_base}", "thumb": url, "parent": arch_name})

    except Exception:
        pass

    parent_entry = {"name": arch_name, "thumb": pack_thumb, "parent": arch_name}
    return parent_entry, results

def process_7z_archive(arch_path, worker_scratch=TEMP_BASE):
    arch_name = os.path.basename(arch_path)
    results = []
    pack_thumb = None

    try:
        proc = subprocess.run([SEVEN_ZIP, 'l', '-slt', arch_path], capture_output=True, text=True, timeout=30)
        lines = proc.stdout.splitlines()
        files = []
        curr = {}
        for l in lines:
            if l.startswith("Path = ") and not l.endswith(arch_path):
                curr['path'] = l[7:].strip()
            elif l.startswith("Size = "):
                curr['size'] = int(l[7:].strip()) if l[7:].strip().isdigit() else 0
                files.append(curr)
                curr = {}

        # 1. Images
        img_files = [f['path'] for f in files if f.get('path', '').lower().endswith(('.jpg', '.png', '.jpeg')) and not '__macosx' in f.get('path', '').lower()]
        for im in img_files:
            im_base = os.path.basename(im)
            if not im_base: continue
            item_key = f"{arch_path}::{im}"
            h = hashlib.md5(item_key.encode('utf-8')).hexdigest()[:12]
            out_path = os.path.join(THUMBS_DIR, f"{h}.jpg")
            if not os.path.exists(out_path):
                try:
                    ext_cmd = [SEVEN_ZIP, 'e', f'-o{worker_scratch}', '-p-', '-y', arch_path, im]
                    subprocess.run(ext_cmd, capture_output=True, timeout=25)
                    temp_f = os.path.join(worker_scratch, im_base)
                    if os.path.exists(temp_f):
                        img = cv2.imread(temp_f)
                        try: os.remove(temp_f)
                        except: pass
                        if img is not None:
                            h_im, w_im = img.shape[:2]
                            scale = TARGET_SIZE / max(h_im, w_im)
                            resized = cv2.resize(img, (int(w_im * scale), int(h_im * scale)))
                            canvas = np.full((TARGET_SIZE, TARGET_SIZE, 3), (16, 20, 30), dtype=np.uint8)
                            y_off = (TARGET_SIZE - resized.shape[0]) // 2
                            x_off = (TARGET_SIZE - resized.shape[1]) // 2
                            canvas[y_off:y_off+resized.shape[0], x_off:x_off+resized.shape[1]] = resized
                            cv2.imwrite(out_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                except Exception:
                    pass
            if os.path.exists(out_path):
                url = f"./previews/{h}.jpg"
                if not pack_thumb: pack_thumb = url
                results.append({"name": f"{arch_name} ➔ {im_base}", "thumb": url, "parent": arch_name})

        # 2. STLs
        raw_stls = [f['path'] for f in files if f.get('path', '').lower().endswith('.stl') and not '__macosx' in f.get('path', '').lower()]
        clean_stls = [s for s in raw_stls if not 'supported' in s.lower() or 'unsupported' in s.lower()]
        stls_to_render = clean_stls if clean_stls else raw_stls

        for s in stls_to_render:
            s_base = os.path.basename(s)
            if not s_base: continue
            item_key = f"{arch_path}::{s}"
            h = hashlib.md5(item_key.encode('utf-8')).hexdigest()[:12]
            out_path = os.path.join(THUMBS_DIR, f"{h}.jpg")
            if not os.path.exists(out_path):
                try:
                    ext_cmd = [SEVEN_ZIP, 'e', f'-o{worker_scratch}', '-p-', '-y', arch_path, s]
                    subprocess.run(ext_cmd, capture_output=True, timeout=25)
                    temp_f = os.path.join(worker_scratch, s_base)
                    if os.path.exists(temp_f):
                        try:
                            with open(temp_f, 'rb') as fp:
                                mesh = trimesh.load(fp, file_type='stl')
                                if hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                                    render_mesh_to_thumb(mesh, out_path)
                        finally:
                            try: os.remove(temp_f)
                            except: pass
                except Exception:
                    pass
            if os.path.exists(out_path):
                url = f"./previews/{h}.jpg"
                if not pack_thumb: pack_thumb = url
                results.append({"name": f"{arch_name} ➔ {s_base}", "thumb": url, "parent": arch_name})

    except Exception:
        pass

    parent_entry = {"name": arch_name, "thumb": pack_thumb, "parent": arch_name}
    return parent_entry, results

def process_single_creator(args):
    cat, creator, creator_path = args
    worker_id = uuid.uuid4().hex[:8]
    worker_scratch = os.path.join(TEMP_BASE, f"w_{worker_id}")
    os.makedirs(worker_scratch, exist_ok=True)

    archives = []
    loose_stls = []
    loose_imgs = []
    other_files = []

    try:
        for root, _, files in os.walk(creator_path):
            is_scaffolding = 'supported' in os.path.basename(root).lower() and not 'unsupported' in os.path.basename(root).lower()
            for f in files:
                if f.lower() == 'thumbs.db' or f.startswith('._'):
                    continue
                full_f = os.path.join(root, f)
                ext = os.path.splitext(f)[1].lower()
                if ext in ['.zip', '.rar', '.7z']:
                    archives.append(full_f)
                elif ext in ['.stl', '.obj']:
                    if not is_scaffolding:
                        loose_stls.append(full_f)
                    else:
                        other_files.append(full_f)
                elif ext in ['.jpg', '.png', '.jpeg']:
                    loose_imgs.append(full_f)
                else:
                    other_files.append(full_f)

        items_list = []
        thumbnails_showcase = []

        # 1. Process loose images
        for img_p in loose_imgs:
            url = process_loose_image(img_p)
            base = os.path.basename(img_p)
            items_list.append({"name": base, "thumb": url})
            if url:
                thumbnails_showcase.append({"Name": base, "Thumb": url})

        # 2. Process loose STLs
        for stl_p in loose_stls:
            url = process_loose_stl(stl_p)
            base = os.path.basename(stl_p)
            items_list.append({"name": base, "thumb": url})
            if url:
                thumbnails_showcase.append({"Name": base, "Thumb": url})

        # 3. Process archives
        for arch_p in archives:
            ext = os.path.splitext(arch_p)[1].lower()
            if ext == '.zip':
                parent_entry, sub_items = process_zip_archive(arch_p)
            else:
                parent_entry, sub_items = process_7z_archive(arch_p, worker_scratch)

            items_list.append({"name": parent_entry['name'], "thumb": parent_entry['thumb']})
            if parent_entry['thumb']:
                thumbnails_showcase.append({"Name": parent_entry['name'], "Thumb": parent_entry['thumb']})

            for sub in sub_items:
                items_list.append({"name": sub['name'], "thumb": sub['thumb']})
                if sub['thumb']:
                    thumbnails_showcase.append({"Name": sub['name'], "Thumb": sub['thumb']})

        # 4. Other files
        for oth_p in other_files:
            base = os.path.basename(oth_p)
            items_list.append({"name": base, "thumb": None})

        valid_previews = [it for it in items_list if it.get('thumb')]

        entry = {
            "Category": cat,
            "Creator": creator,
            "TotalFiles": len(items_list),
            "Archives": len(archives),
            "STLs": len(loose_stls),
            "PreviewsCount": len(valid_previews),
            "Thumbnails": thumbnails_showcase,
            "Items": items_list,
            "Samples": [it['name'] for it in items_list[:50]]
        }
        return entry
    finally:
        # Cleanup worker scratch folder
        try:
            for f in os.listdir(worker_scratch):
                try: os.remove(os.path.join(worker_scratch, f))
                except: pass
            os.rmdir(worker_scratch)
        except Exception:
            pass

def run_deep_library_generation():
    print(f"Starting Multi-Core Deep STL Extraction & Rendering with {NUM_WORKERS} Parallel Workers...")
    catalog = []
    completed_cats = set()

    # Load existing completed catalog
    if os.path.exists(JS_OUT):
        try:
            with open(JS_OUT, 'r', encoding='utf-8') as f:
                content = f.read()
            prefix = "const libraryData = "
            if content.startswith(prefix):
                json_str = content[len(prefix):].rstrip(';')
                catalog = json.loads(json_str)
                completed_cats = set(item['Category'] for item in catalog)
                print(f"Resuming: Loaded {len(catalog)} existing collections across {len(completed_cats)} completed categories.")
        except Exception as e:
            print(f"Warning: Could not read existing {JS_OUT}: {e}")
            catalog = []
            completed_cats = set()

    categories = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
    categories.sort()

    total_rendered_items = sum(len([it for it in entry.get('Items', []) if it.get('thumb')]) for entry in catalog)
    start_time = time.time()

    for cat_idx, cat in enumerate(categories):
        if cat in completed_cats:
            print(f"[{cat_idx+1}/{len(categories)}] Category already completed: {cat} (Skipping)")
            continue

        cat_path = os.path.join(BASE_DIR, cat)
        try:
            creators = [c for c in os.listdir(cat_path) if os.path.isdir(os.path.join(cat_path, c))]
            creators.sort()
        except Exception as e:
            print(f"Error reading category {cat}: {e}")
            continue

        print(f"[{cat_idx+1}/{len(categories)}] Processing category: {cat} ({len(creators)} collections in parallel across {NUM_WORKERS} workers)...")
        tasks = [(cat, creator, os.path.join(cat_path, creator)) for creator in creators]

        with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
            future_to_task = {executor.submit(process_single_creator, t): t for t in tasks}
            for future in as_completed(future_to_task):
                try:
                    result_entry = future.result()
                    if result_entry:
                        catalog.append(result_entry)
                        total_rendered_items += result_entry.get('PreviewsCount', 0)
                except Exception as e:
                    task = future_to_task[future]
                    print(f"Error processing {task[1]}: {e}")

        # Save incremental progress to library_data.js after each category
        with open(JS_OUT, 'w', encoding='utf-8') as f:
            f.write("const libraryData = " + json.dumps(catalog, ensure_ascii=False) + ";")
        print(f"  Saved progress for {cat}: Total collections saved: {len(catalog)} | Total previews rendered: {total_rendered_items}")

    print(f"Deep Rendering Complete in {time.time() - start_time:.1f}s! Total Previews: {total_rendered_items}")

if __name__ == "__main__":
    run_deep_library_generation()
