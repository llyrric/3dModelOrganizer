import os
import sys
import io
import time
import uuid
import hashlib
import zipfile
import argparse
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import trimesh
import cv2

# Set stdout to UTF-8 for clean console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
THUMBS_DIR = os.path.join(WORKSPACE_DIR, "previews")
TEMP_BASE = os.path.join(WORKSPACE_DIR, "scratch")
SEVEN_ZIP = r"C:\Program Files\7-Zip\7z.exe"
TARGET_SIZE = 400
JPEG_QUALITY = 80
DEFAULT_WORKERS = 8

os.makedirs(THUMBS_DIR, exist_ok=True)
os.makedirs(TEMP_BASE, exist_ok=True)

def render_mesh_to_thumb(mesh, out_path, size=TARGET_SIZE):
    """
    Renders an upright, front-facing 3D clay miniature thumbnail.
    Automatically:
    1. Detects and corrects the UP axis (Z-up vs Y-up vs X-up).
    2. Detects the base plate to ensure the miniature is right-side up.
    3. Evaluates geometric detail across quadrants to pick the front-facing 3/4 hero angle.
    4. Applies backface culling, two-point studio lighting, and painter's algorithm.
    """
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

        # Backface culling: normals facing camera have normals_cam[:, 2] < 0
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
        order = np.argsort(-face_z)  # Draw furthest first

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

def discover_render_tasks(target_folder):
    """
    Scans target_folder for archives (.zip, .7z, .rar) and loose STLs.
    Returns a list of task dicts: {'type', 'path', 'inner_path', 'hash', 'out_path'}
    """
    tasks = []
    print(f"Scanning target folder: {target_folder}")

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
                except Exception as e:
                    print(f"Warning reading zip {f}: {e}")

            elif ext in ['.7z', '.rar']:
                try:
                    proc = subprocess.run([SEVEN_ZIP, 'l', '-slt', full_p], capture_output=True, text=True, timeout=25)
                    lines = proc.stdout.splitlines()
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
                        tasks.append({
                            'type': '7z_stl',
                            'arch_path': full_p,
                            'inner_path': s,
                            'hash': h,
                            'out_path': os.path.join(THUMBS_DIR, f"{h}.jpg"),
                            'display_name': f"{os.path.basename(full_p)} ➔ {os.path.basename(s)}"
                        })
                except Exception as e:
                    print(f"Warning reading 7z/rar {f}: {e}")

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

    return tasks

def render_task_worker(task):
    """Worker function for concurrent rendering"""
    t_type = task['type']
    out_path = task['out_path']
    success = False

    try:
        if t_type == 'zip_stl':
            arch_p = task['arch_path']
            inner_p = task['inner_path']
            with zipfile.ZipFile(arch_p, 'r') as z:
                stl_data = z.read(inner_p)
                mesh = trimesh.load(io.BytesIO(stl_data), file_type='stl')
                if hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                    success = render_mesh_to_thumb(mesh, out_path)

        elif t_type == 'loose_stl':
            stl_p = task['stl_path']
            with open(stl_p, 'rb') as fp:
                mesh = trimesh.load(fp, file_type='stl')
                if hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                    success = render_mesh_to_thumb(mesh, out_path)

        elif t_type == '7z_stl':
            arch_p = task['arch_path']
            inner_p = task['inner_path']
            worker_scratch = os.path.join(TEMP_BASE, f"w_{uuid.uuid4().hex[:6]}")
            os.makedirs(worker_scratch, exist_ok=True)
            s_base = os.path.basename(inner_p)
            try:
                cmd = [SEVEN_ZIP, 'e', f'-o{worker_scratch}', '-p-', '-y', arch_p, inner_p]
                subprocess.run(cmd, capture_output=True, timeout=30)
                temp_f = os.path.join(worker_scratch, s_base)
                if os.path.exists(temp_f):
                    with open(temp_f, 'rb') as fp:
                        mesh = trimesh.load(fp, file_type='stl')
                        if hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
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

def run_batch_refix(target_folder, workers=DEFAULT_WORKERS, limit=None, force=True, dry_run=False):
    t_start = time.time()
    all_tasks = discover_render_tasks(target_folder)
    print(f"Total candidate STLs discovered: {len(all_tasks)}")

    if not force:
        tasks_to_run = [t for t in all_tasks if not os.path.exists(t['out_path'])]
        print(f"Skipping already-existing thumbnails. Remaining to process: {len(tasks_to_run)}")
    else:
        tasks_to_run = all_tasks

    if limit and limit > 0:
        tasks_to_run = tasks_to_run[:limit]
        print(f"Applying limit of {limit} tasks.")

    if dry_run:
        print("\n--- DRY RUN PREVIEW (First 15 items) ---")
        for t in tasks_to_run[:15]:
            print(f"  [{t['type']}] {t['display_name']} -> {t['hash']}.jpg (exists={os.path.exists(t['out_path'])})")
        print(f"--- Dry run complete. {len(tasks_to_run)} tasks would be executed. ---")
        return

    if not tasks_to_run:
        print("No tasks to run.")
        return

    print(f"\nStarting parallel rendering using {workers} worker processes...")
    completed_count = 0
    success_count = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(render_task_worker, task): task for task in tasks_to_run}
        for future in as_completed(futures):
            name, h, ok = future.result()
            completed_count += 1
            if ok:
                success_count += 1
            if completed_count % 10 == 0 or completed_count == len(tasks_to_run):
                rate = completed_count / max(0.001, time.time() - t_start)
                print(f"Progress: [{completed_count}/{len(tasks_to_run)}] ({success_count} success) - {rate:.1f} items/sec")

    elapsed = time.time() - t_start
    print(f"\nBatch re-render complete!")
    print(f"Successfully rendered: {success_count} / {len(tasks_to_run)}")
    print(f"Total time: {elapsed:.2f} seconds ({len(tasks_to_run) / max(0.001, elapsed):.1f} items/second)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch re-render 3D STLs with fixed geometry and shading")
    parser.add_argument("--folder", type=str, default=r"X:\3d files\3d files\smaller scale\10mm Alans",
                        help="Target folder to recursively process")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Number of worker processes")
    parser.add_argument("--limit", type=int, default=None, help="Max number of items to process for test run")
    parser.add_argument("--no-force", action="store_true", help="Do not overwrite existing thumbnails")
    parser.add_argument("--dry-run", action="store_true", help="Scan and list tasks without rendering")

    args = parser.parse_args()
    run_batch_refix(
        target_folder=args.folder,
        workers=args.workers,
        limit=args.limit,
        force=not args.no_force,
        dry_run=args.dry_run
    )
