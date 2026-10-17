import os
import sys
import io
import time
import json
import uuid
import datetime
import hashlib
import zipfile
import argparse
import subprocess
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import numpy as np
import trimesh
import cv2

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = os.environ.get("STL_LIBRARY_ROOT", r"X:\3d files\3d files")
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
THUMBS_DIR = os.path.join(WORKSPACE_DIR, "previews")
TEMP_BASE = os.path.join(WORKSPACE_DIR, "scratch", "render_workers")
PROGRESS_JSON = os.path.join(WORKSPACE_DIR, "render_progress.json")
SEVEN_ZIP = r"C:\Program Files\7-Zip\7z.exe"
TARGET_SIZE = 400
JPEG_QUALITY = 82
DEFAULT_WORKERS = 8

os.makedirs(THUMBS_DIR, exist_ok=True)
os.makedirs(TEMP_BASE, exist_ok=True)

def render_mesh_to_thumb(mesh, out_path, size=TARGET_SIZE):
    """
    Renders an upright, front-facing 3D clay miniature thumbnail.
    Pipeline:
    1. Upright Normalization (tallest dimension -> vertical Z).
    2. Baseplate & Inversion Detection (planar flat surface area test; flips upside-down models).
    3. 3/4 Hero View Selection (evaluates geometric feature variance across 45, 135, 225, 315 deg).
    4. Two-Point Studio Lighting (Key + Fill) on signature dark navy background.
    5. Backface culling + depth-sorted painter's polygon rasterization.
    """
    try:
        # Handle Scene object if passed directly
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        if not hasattr(mesh, 'vertices') or not hasattr(mesh, 'faces'):
            return False
        if len(mesh.vertices) < 3 or len(mesh.faces) == 0:
            return False

        # 1. Upright alignment
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
        areas = mesh.area_faces

        # 2. Baseplate check using planar horizontal area (abs(norm_z) > 0.90)
        z_min, z_max = verts[:, 2].min(), verts[:, 2].max()
        z_range = z_max - z_min
        if z_range > 0:
            f_z = verts[faces].mean(axis=1)[:, 2]
            bot_flat = (f_z < z_min + 0.05 * z_range) & (norms[:, 2] < -0.90)
            top_flat = (f_z > z_max - 0.05 * z_range) & (norms[:, 2] > 0.90)
            bot_area = areas[bot_flat].sum()
            top_area = areas[top_flat].sum()

            # Only flip if top flat area is overwhelmingly larger than bottom flat area (e.g. inverted baseplate)
            if top_area > 30 and top_area > bot_area * 3:
                R_flip = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]])
                verts = verts @ R_flip.T
                norms = norms @ R_flip.T

        # 3. Smart front angle selection (eye-level elevation + 3/4 hero view)
        elevation = np.radians(16)
        z_mid = (verts[:, 2].min() + verts[:, 2].max()) / 2.0
        f_upper = verts[faces].mean(axis=1)[:, 2] > z_mid
        best_angle = 135
        best_score = -1e9

        for a in [45, 135, 225, 315]:
            az = np.radians(a)
            cam_dir = np.array([np.cos(elevation) * np.sin(az), -np.cos(elevation) * np.cos(az), np.sin(elevation)])
            cam_norm = np.linalg.norm(cam_dir)
            if cam_norm == 0:
                continue
            cam_dir /= cam_norm
            fwd = -cam_dir
            w_up = np.array([0.0, 0.0, 1.0])
            r = np.cross(fwd, w_up)
            r_norm = np.linalg.norm(r)
            if r_norm == 0:
                continue
            r /= r_norm
            u = np.cross(r, fwd)
            u_norm = np.linalg.norm(u)
            if u_norm == 0:
                continue
            u /= u_norm
            R_c = np.vstack([r, u, fwd])
            n_c = norms @ R_c.T
            vis = (n_c[:, 2] < 0) & f_upper
            if vis.sum() > 0:
                score = np.std(n_c[vis], axis=0).sum() * 1000 + vis.sum() * 0.05
                if score > best_score:
                    best_score = score
                    best_angle = a

        # 4. Camera Matrix for selected front angle
        az = np.radians(best_angle)
        cam_dir = np.array([np.cos(elevation) * np.sin(az), -np.cos(elevation) * np.cos(az), np.sin(elevation)])
        cam_dir /= np.linalg.norm(cam_dir)
        forward = -cam_dir
        world_up = np.array([0.0, 0.0, 1.0])
        right = np.cross(forward, world_up)
        right /= np.linalg.norm(right)
        up = np.cross(right, forward)
        up /= np.linalg.norm(up)
        R_cam = np.vstack([right, up, forward])

        vertices_cam = verts @ R_cam.T
        normals_cam = norms @ R_cam.T

        # Backface culling: front-facing normals have normals_cam[:, 2] < 0
        visible = normals_cam[:, 2] < 0
        if not np.any(visible):
            visible = np.ones(len(faces), dtype=bool)

        front_faces = faces[visible]
        front_normals = normals_cam[visible]

        # Two-point studio lighting (Key light + Fill light from front of camera)
        key_dir = np.array([0.45, 0.50, -0.74])
        key_dir /= np.linalg.norm(key_dir)
        fill_dir = np.array([-0.55, 0.30, -0.77])
        fill_dir /= np.linalg.norm(fill_dir)

        dot_key = np.clip(front_normals @ key_dir, 0.0, 1.0)
        dot_fill = np.clip(front_normals @ fill_dir, 0.0, 1.0)
        intensity = np.clip(0.25 + 0.55 * dot_key + 0.20 * dot_fill, 0.15, 1.0)

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
        order = np.argsort(-face_z)  # Draw furthest first

        # Dark navy studio background (20, 26, 38)
        img = np.full((size, size, 3), (20, 26, 38), dtype=np.uint8)
        for idx in order:
            pts = v_proj[front_faces[idx]]
            shade = int(intensity[idx] * 215 + 35)
            color = (int(shade * 0.88), int(shade * 0.94), shade)
            cv2.fillPoly(img, [pts], color)

        cv2.imwrite(out_path, img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        return True
    except Exception:
        return False

def inspect_7z_rar(full_p):
    found = []
    try:
        proc = subprocess.run([SEVEN_ZIP, 'l', '-slt', full_p], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
        raw_out = proc.stdout.decode('utf-8', errors='replace')
        lines = raw_out.splitlines()
        inners = []
        for l in lines:
            if l.startswith("Path = ") and not l.endswith(full_p):
                p_in = l[7:].strip()
                if p_in.lower().endswith('.stl') and not '__macosx' in p_in.lower():
                    inners.append(p_in)
        clean_stls = [s for s in inners if not 'supported' in s.lower() or 'unsupported' in s.lower()]
        chosen = clean_stls if clean_stls else inners
        for s in chosen:
            item_key = f"{full_p}::{s}"
            h = hashlib.md5(item_key.encode('utf-8')).hexdigest()[:12]
            found.append({
                'type': '7z_stl',
                'arch_path': full_p,
                'inner_path': s,
                'hash': h,
                'out_path': os.path.join(THUMBS_DIR, f"{h}.jpg"),
                'display_name': f"{os.path.basename(full_p)} ➔ {os.path.basename(s)}"
            })
    except Exception:
        pass
    return found

def discover_tasks_for_folder(target_folder):
    """Recursively discovers STL rendering tasks from archives and loose files with concurrent listing"""
    tasks = []
    seven_z_files = []
    
    for root, _, files in os.walk(target_folder):
        is_scaffolding = 'supported' in os.path.basename(root).lower() and not 'unsupported' in os.path.basename(root).lower()
        for f in files:
            if f.lower() == 'thumbs.db' or f.startswith('._'):
                continue
            full_p = os.path.join(root, f)
            ext = os.path.splitext(f)[1].lower()

            if ext == '.zip':
                try:
                    with zipfile.ZipFile(full_p, 'r') as z:
                        names = z.namelist()
                        raw_stls = [n for n in names if n.lower().endswith('.stl') and not '__macosx' in n.lower() and not n.startswith('._')]
                        clean_stls = [n for n in raw_stls if not 'supported' in n.lower() or 'unsupported' in n.lower()]
                        chosen = clean_stls if clean_stls else raw_stls
                        for s in chosen:
                            item_key = f"{full_p}::{s}"
                            h = hashlib.md5(item_key.encode('utf-8')).hexdigest()[:12]
                            tasks.append({
                                'type': 'zip_stl',
                                'arch_path': full_p,
                                'inner_path': s,
                                'hash': h,
                                'out_path': os.path.join(THUMBS_DIR, f"{h}.jpg"),
                                'display_name': f"{os.path.basename(full_p)} ➔ {os.path.basename(s)}"
                            })
                except Exception:
                    seven_z_files.append(full_p)

            elif ext in ['.7z', '.rar']:
                seven_z_files.append(full_p)

            elif ext == '.stl':
                if not is_scaffolding:
                    h = hashlib.md5(full_p.encode('utf-8')).hexdigest()[:12]
                    tasks.append({
                        'type': 'loose_stl',
                        'stl_path': full_p,
                        'hash': h,
                        'out_path': os.path.join(THUMBS_DIR, f"{h}.jpg"),
                        'display_name': os.path.basename(full_p)
                    })

    if seven_z_files:
        with ThreadPoolExecutor(max_workers=16) as t_pool:
            for res in t_pool.map(inspect_7z_rar, seven_z_files):
                tasks.extend(res)

    return tasks

def load_mesh_safely(source, is_path=False):
    try:
        if is_path:
            mesh = trimesh.load(source, file_type='stl')
        else:
            mesh = trimesh.load(io.BytesIO(source), file_type='stl')
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)
        return mesh
    except Exception:
        return None

def render_worker_task(task):
    """Individual worker process task execution"""
    t_type = task['type']
    out_path = task['out_path']
    success = False

    try:
        if t_type == 'zip_stl':
            arch_p = task['arch_path']
            inner_p = task['inner_path']
            try:
                with zipfile.ZipFile(arch_p, 'r') as z:
                    stl_data = z.read(inner_p)
                    mesh = load_mesh_safely(stl_data, is_path=False)
                    if mesh is not None and hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                        success = render_mesh_to_thumb(mesh, out_path)
            except Exception:
                # Fallback to 7-zip for multi-part or split zips (.z01)
                worker_scratch = os.path.join(TEMP_BASE, f"w_{uuid.uuid4().hex[:6]}")
                os.makedirs(worker_scratch, exist_ok=True)
                s_base = os.path.basename(inner_p.replace('\\', '/'))
                try:
                    cmd = [SEVEN_ZIP, 'e', f'-o{worker_scratch}', '-p-', '-y', arch_p, inner_p]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                    temp_f = os.path.join(worker_scratch, s_base)
                    if not os.path.exists(temp_f):
                        cands = [os.path.join(worker_scratch, x) for x in os.listdir(worker_scratch) if x.lower().endswith('.stl')]
                        if cands:
                            temp_f = cands[0]
                    if os.path.exists(temp_f):
                        mesh = load_mesh_safely(temp_f, is_path=True)
                        if mesh is not None and hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                            success = render_mesh_to_thumb(mesh, out_path)
                finally:
                    try:
                        if os.path.exists(worker_scratch):
                            for f in os.listdir(worker_scratch):
                                os.remove(os.path.join(worker_scratch, f))
                            os.rmdir(worker_scratch)
                    except Exception:
                        pass

        elif t_type == 'loose_stl':
            stl_p = task['stl_path']
            mesh = load_mesh_safely(stl_p, is_path=True)
            if mesh is not None and hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                success = render_mesh_to_thumb(mesh, out_path)

        elif t_type == '7z_stl':
            arch_p = task['arch_path']
            inner_p = task['inner_path']
            worker_scratch = os.path.join(TEMP_BASE, f"w_{uuid.uuid4().hex[:6]}")
            os.makedirs(worker_scratch, exist_ok=True)
            s_base = os.path.basename(inner_p.replace('\\', '/'))
            try:
                cmd = [SEVEN_ZIP, 'e', f'-o{worker_scratch}', '-p-', '-y', arch_p, inner_p]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                temp_f = os.path.join(worker_scratch, s_base)
                if not os.path.exists(temp_f):
                    cands = [os.path.join(worker_scratch, x) for x in os.listdir(worker_scratch) if x.lower().endswith('.stl')]
                    if cands:
                        temp_f = cands[0]
                if os.path.exists(temp_f):
                    mesh = load_mesh_safely(temp_f, is_path=True)
                    if mesh is not None and hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                        success = render_mesh_to_thumb(mesh, out_path)
            finally:
                try:
                    if os.path.exists(worker_scratch):
                        for f in os.listdir(worker_scratch):
                            os.remove(os.path.join(worker_scratch, f))
                        os.rmdir(worker_scratch)
                except Exception:
                    pass

    except Exception:
        success = False

    return task['display_name'], task['hash'], success

def update_progress_file(data):
    try:
        with open(PROGRESS_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except:
        pass

def render_category(cat_name, cat_path, workers=DEFAULT_WORKERS, force=True, outdated_only=False, global_stats=None):
    print(f"\n=======================================================")
    print(f" Category: {cat_name.upper()} ({cat_path})")
    print(f"=======================================================")
    
    t_start = time.time()
    tasks = discover_tasks_for_folder(cat_path)
    total_found = len(tasks)
    print(f"Discovered {total_found} candidate STLs in {cat_name}.")

    if outdated_only:
        cutoff = datetime.datetime(2026, 10, 15, 12, 0).timestamp()
        tasks = [t for t in tasks if not os.path.exists(t['out_path']) or os.path.getmtime(t['out_path']) < cutoff]
        print(f"Filtered to outdated/missing renders: {len(tasks)} remaining to process.")
    elif not force:
        tasks = [t for t in tasks if not os.path.exists(t['out_path'])]
        print(f"Skipping existing renders. {len(tasks)} remaining to process.")

    if not tasks:
        print(f"Category {cat_name} is already complete (or has no STL models).")
        return 0, 0

    print(f"Launching {workers} parallel worker processes...")
    completed = 0
    succeeded = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(render_worker_task, t): t for t in tasks}
        for future in as_completed(future_map):
            name, h, ok = future.result()
            completed += 1
            if ok:
                succeeded += 1
            rate = completed / max(0.001, time.time() - t_start)
            status_symbol = "✔" if ok else "✘"
            
            if completed % 15 == 0 or completed == len(tasks):
                short_name = (name[:50] + '..') if len(name) > 52 else name
                print(f"[{completed:>4}/{len(tasks)}] {status_symbol} {short_name:<52} | {rate:.1f} models/sec")
                
                # Update progress tracker file
                if global_stats:
                    g_done = global_stats['completed'] + completed
                    g_succ = global_stats['succeeded'] + succeeded
                    g_rate = g_done / max(0.001, time.time() - global_stats['start_time'])
                    update_progress_file({
                        "status": "running",
                        "current_category": cat_name,
                        "category_completed": completed,
                        "category_total": len(tasks),
                        "global_completed": g_done,
                        "global_succeeded": g_succ,
                        "global_models_per_sec": round(g_rate, 2),
                        "elapsed_seconds": round(time.time() - global_stats['start_time'], 1),
                        "last_updated": datetime.datetime.now().isoformat()
                    })

    elapsed = time.time() - t_start
    print(f"\nFinished Category {cat_name} in {elapsed:.1f}s ({succeeded}/{len(tasks)} success, {len(tasks)/max(0.001, elapsed):.1f} models/sec)")
    return completed, succeeded

def main():
    parser = argparse.ArgumentParser(description="Multi-Process High-Throughput 3D STL Renderer")
    parser.add_argument("--root", type=str, default=ROOT_DIR, help="Root library directory")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Worker processes count")
    parser.add_argument("--no-force", action="store_true", help="Skip existing renders")
    parser.add_argument("--outdated-only", action="store_true", help="Re-render only models with missing or pre-fix (old) thumbnails")
    parser.add_argument("--category", type=str, default=None, help="Process only a specific category")
    parser.add_argument("--categories", nargs="+", default=None, help="Process a list of specific categories")
    parser.add_argument("--start-category", type=str, default=None, help="Start processing from this category onwards")
    parser.add_argument("--init-completed", type=int, default=0, help="Initial completed model count for global stats")
    parser.add_argument("--init-succeeded", type=int, default=0, help="Initial succeeded model count for global stats")
    parser.add_argument("--init-elapsed", type=float, default=0.0, help="Initial elapsed seconds for global stats")
    args = parser.parse_args()

    mode_str = "RE-RENDER OUTDATED/MISSING" if args.outdated_only else ("SKIP EXISTING" if args.no_force else "OVERWRITE (Force)")
    print(f"=======================================================")
    print(f" 3D PRINTING LIBRARY PARALLEL RENDERER (8 WORKERS)")
    print(f" Root: {args.root}")
    print(f" Workers: {args.workers}")
    print(f" Overwrite Mode: {mode_str}")
    print(f"=======================================================\n")

    # Discover categories
    categories = []
    if args.category:
        cat_p = os.path.join(args.root, args.category) if not os.path.isabs(args.category) else args.category
        if os.path.exists(cat_p):
            categories.append((os.path.basename(cat_p), cat_p))
        else:
            print(f"Category folder not found: {cat_p}")
            return
    elif args.categories:
        for c in args.categories:
            cat_p = os.path.join(args.root, c) if not os.path.isabs(c) else c
            if os.path.exists(cat_p):
                categories.append((os.path.basename(cat_p), cat_p))
            else:
                print(f"Warning: Category folder not found: {cat_p}")
        if not categories:
            print("No valid categories specified.")
            return
    else:
        # Scan top-level folders in root
        for entry in sorted(os.listdir(args.root)):
            p = os.path.join(args.root, entry)
            if os.path.isdir(p):
                # Filter out utility/firmware folders
                if not "firmware" in entry.lower() and not "resin files" in entry.lower():
                    categories.append((entry, p))

    if args.start_category:
        match_idx = None
        for i, (c_name, _) in enumerate(categories):
            if c_name.lower() == args.start_category.lower():
                match_idx = i
                break
        if match_idx is not None:
            categories = categories[match_idx:]
            print(f"Resuming pipeline from category '{args.start_category}' ({len(categories)} categories queued).")
        else:
            print(f"Category '{args.start_category}' not found in category list.")
            return

    print(f"Queued {len(categories)} categories to process:")
    for c_name, _ in categories:
        print(f"  • {c_name}")

    global_stats = {
        'start_time': time.time() - args.init_elapsed,
        'completed': args.init_completed,
        'succeeded': args.init_succeeded
    }

    update_progress_file({
        "status": "started",
        "total_categories": len(categories),
        "workers": args.workers,
        "global_completed": args.init_completed,
        "global_succeeded": args.init_succeeded,
        "start_time": datetime.datetime.now().isoformat(),
        "last_updated": datetime.datetime.now().isoformat()
    })

    for cat_name, cat_path in categories:
        done, succ = render_category(
            cat_name=cat_name,
            cat_path=cat_path,
            workers=args.workers,
            force=not args.no_force,
            outdated_only=args.outdated_only,
            global_stats=global_stats
        )
        global_stats['completed'] += done
        global_stats['succeeded'] += succ

    total_time = time.time() - global_stats['start_time']
    print(f"\n=======================================================")
    print(f" ALL CATEGORIES COMPLETED!")
    print(f" Total Models Processed: {global_stats['completed']}")
    print(f" Total Succeeded: {global_stats['succeeded']}")
    print(f" Total Time: {total_time:.1f}s ({(total_time/3600):.2f} hours)")
    print(f" Average Speed: {global_stats['completed']/max(0.001, total_time):.1f} models/sec")
    print(f"=======================================================\n")

    update_progress_file({
        "status": "completed",
        "global_completed": global_stats['completed'],
        "global_succeeded": global_stats['succeeded'],
        "total_seconds": round(total_time, 1),
        "average_models_per_sec": round(global_stats['completed']/max(0.001, total_time), 2),
        "finished_at": datetime.datetime.now().isoformat()
    })

if __name__ == "__main__":
    main()
