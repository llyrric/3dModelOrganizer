import os
import sys
import json
import zipfile
import subprocess
import hashlib
import tempfile
import numpy as np
import trimesh
import cv2

BASE_DIR = os.environ.get("STL_LIBRARY_ROOT", r"X:\3d files\3d files")
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
THUMBS_DIR = os.path.join(WORKSPACE_DIR, "previews")
JS_OUT = os.path.join(WORKSPACE_DIR, "library_data.js")
TEMP_DIR = os.path.join(WORKSPACE_DIR, "scratch")
SEVEN_ZIP = r"C:\Program Files\7-Zip\7z.exe"
os.makedirs(THUMBS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

def render_mesh_to_thumb(mesh, out_path, size=320):
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

        cv2.imwrite(out_path, img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return True
    except Exception:
        return False

def get_thumbnail_for_archive(arch_path):
    hash_val = hashlib.md5(arch_path.encode('utf-8')).hexdigest()[:12]
    out_path = os.path.join(THUMBS_DIR, f"{hash_val}.jpg")
    if os.path.exists(out_path):
        return f"./previews/{hash_val}.jpg"

    ext = os.path.splitext(arch_path)[1].lower()

    # 1. Standard ZIP via native zipfile
    if ext == '.zip':
        try:
            with zipfile.ZipFile(arch_path, 'r') as z:
                names = z.namelist()
                imgs = [n for n in names if n.lower().endswith(('.jpg', '.png', '.jpeg')) and not '__macosx' in n.lower()]
                if imgs:
                    best_img = imgs[0]
                    for im in imgs:
                        if any(k in im.lower() for k in ['render', 'preview', 'cover', 'product', 'featured', 'box', '1.jpg', 'pic']):
                            best_img = im
                            break
                    img_data = z.read(best_img)
                    nparr = np.frombuffer(img_data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if img is not None:
                        h, w = img.shape[:2]
                        scale = 320 / max(h, w)
                        resized = cv2.resize(img, (int(w * scale), int(h * scale)))
                        canvas = np.full((320, 320, 3), (16, 20, 30), dtype=np.uint8)
                        y_off = (320 - resized.shape[0]) // 2
                        x_off = (320 - resized.shape[1]) // 2
                        canvas[y_off:y_off+resized.shape[0], x_off:x_off+resized.shape[1]] = resized
                        cv2.imwrite(out_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        return f"./previews/{hash_val}.jpg"

                # If no image, render STL
                stls = [n for n in names if n.lower().endswith('.stl') and not 'unsupported' in n.lower() and not '__macosx' in n.lower()]
                if not stls:
                    stls = [n for n in names if n.lower().endswith('.stl') and not '__macosx' in n.lower()]
                if stls:
                    best_stl = max(stls, key=lambda s: z.getinfo(s).file_size)
                    stl_data = z.read(best_stl)
                    mesh = trimesh.load(io.BytesIO(stl_data), file_type='stl')
                    if hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                        if render_mesh_to_thumb(mesh, out_path):
                            return f"./previews/{hash_val}.jpg"
        except Exception:
            pass

    # 2. RAR and 7Z archives via 7-Zip CLI (Extract to temp disk to support solid blocks)
    elif ext in ['.rar', '.7z'] and os.path.exists(SEVEN_ZIP):
        try:
            cmd = [SEVEN_ZIP, 'l', '-slt', '-p-', '-y', arch_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, errors='ignore', timeout=25)
            lines = proc.stdout.splitlines()

            files = []
            curr_file = {}
            for l in lines:
                if l.startswith("Path = ") and not l.endswith(arch_path):
                    curr_file['path'] = l[7:].strip()
                elif l.startswith("Size = "):
                    curr_file['size'] = int(l[7:].strip()) if l[7:].strip().isdigit() else 0
                    files.append(curr_file)
                    curr_file = {}

            # Check for image inside RAR/7Z
            img_files = [f for f in files if f.get('path', '').lower().endswith(('.jpg', '.png', '.jpeg')) and not '__macosx' in f.get('path', '').lower()]
            if img_files:
                target_img = img_files[0]['path']
                for im in img_files:
                    p = im['path'].lower()
                    if any(k in p for k in ['render', 'preview', 'cover', 'product', '1.jpg', 'pic']):
                        target_img = im['path']
                        break
                # Extract image to temp folder
                ext_cmd = [SEVEN_ZIP, 'e', f'-o{TEMP_DIR}', '-p-', '-y', arch_path, target_img]
                subprocess.run(ext_cmd, capture_output=True, timeout=25)
                temp_extracted = os.path.join(TEMP_DIR, os.path.basename(target_img))
                if os.path.exists(temp_extracted):
                    img = cv2.imread(temp_extracted)
                    try: os.remove(temp_extracted)
                    except: pass
                    if img is not None:
                        h, w = img.shape[:2]
                        scale = 320 / max(h, w)
                        resized = cv2.resize(img, (int(w * scale), int(h * scale)))
                        canvas = np.full((320, 320, 3), (16, 20, 30), dtype=np.uint8)
                        y_off = (320 - resized.shape[0]) // 2
                        x_off = (320 - resized.shape[1]) // 2
                        canvas[y_off:y_off+resized.shape[0], x_off:x_off+resized.shape[1]] = resized
                        cv2.imwrite(out_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        return f"./previews/{hash_val}.jpg"

            # Check for STL to render in RAR/7Z
            stl_files = [f for f in files if f.get('path', '').lower().endswith('.stl') and not 'unsupported' in f.get('path', '').lower() and not '__macosx' in f.get('path', '').lower()]
            if not stl_files:
                stl_files = [f for f in files if f.get('path', '').lower().endswith('.stl') and not '__macosx' in f.get('path', '').lower()]
            if stl_files:
                best_stl = max(stl_files, key=lambda s: s.get('size', 0))['path']
                ext_cmd = [SEVEN_ZIP, 'e', f'-o{TEMP_DIR}', '-p-', '-y', arch_path, best_stl]
                subprocess.run(ext_cmd, capture_output=True, timeout=25)
                temp_extracted = os.path.join(TEMP_DIR, os.path.basename(best_stl))
                if os.path.exists(temp_extracted):
                    try:
                        mesh = trimesh.load(temp_extracted, file_type='stl')
                    finally:
                        try: os.remove(temp_extracted)
                        except: pass
                    if hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                        if render_mesh_to_thumb(mesh, out_path):
                            return f"./previews/{hash_val}.jpg"
        except Exception:
            pass

    return None

def update_entire_library():
    catalog = []
    categories = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
    categories.sort()

    for cat in categories:
        cat_path = os.path.join(BASE_DIR, cat)
        creators = [c for c in os.listdir(cat_path) if os.path.isdir(os.path.join(cat_path, c))]
        creators.sort()

        for creator in creators:
            creator_path = os.path.join(cat_path, creator)
            all_files = []
            archives = []
            loose_stls = []
            loose_imgs = []

            for root, _, files in os.walk(creator_path):
                for f in files:
                    if f.lower() == 'thumbs.db':
                        continue
                    full_f = os.path.join(root, f)
                    all_files.append(f)
                    ext = os.path.splitext(f)[1].lower()
                    if ext in ['.zip', '.rar', '.7z']:
                        archives.append(full_f)
                    elif ext in ['.stl', '.obj']:
                        loose_stls.append(full_f)
                    elif ext in ['.jpg', '.png', '.jpeg']:
                        loose_imgs.append(full_f)

            thumbs = []
            # 1. Loose preview images
            for img_path in loose_imgs:
                h = hashlib.md5(img_path.encode('utf-8')).hexdigest()[:12]
                thumb_file = f"{h}.jpg"
                full_thumb = os.path.join(THUMBS_DIR, thumb_file)
                if os.path.exists(full_thumb):
                    thumbs.append({"Name": os.path.basename(img_path), "Thumb": f"./previews/{thumb_file}"})

            # 2. Archive previews (extract image or render STL for EVERY archive in collection)
            for arch in archives:
                t_url = get_thumbnail_for_archive(arch)
                if t_url:
                    thumbs.append({"Name": os.path.basename(arch), "Thumb": t_url})

            # Pair each file directly with its thumbnail
            thumb_map = {t['Name']: t['Thumb'] for t in thumbs}
            items_list = []
            for fname in all_files:
                items_list.append({
                    "name": fname,
                    "thumb": thumb_map.get(fname, None)
                })

            catalog.append({
                "Category": cat,
                "Creator": creator,
                "TotalFiles": len(all_files),
                "Archives": len(archives),
                "STLs": len(loose_stls),
                "PreviewsCount": len(thumbs),
                "Thumbnails": thumbs,
                "Items": items_list,
                "Samples": all_files
            })

    with open(JS_OUT, 'w', encoding='utf-8') as f:
        f.write("const libraryData = " + json.dumps(catalog, ensure_ascii=False) + ";")
    print(f"Updated all {len(catalog)} collections with comprehensive thumbnails in {JS_OUT}!")

if __name__ == "__main__":
    update_entire_library()
