#!/usr/bin/env python3
import os
import shutil
import subprocess
import threading
import queue
from pathlib import Path
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

BASE = Path(__file__).parent
COMBINER_PUBLIC = BASE / "glb-animation-combiner" / "public"
MODELS_DIR      = COMBINER_PUBLIC / "models"
ANIMS_DIR       = COMBINER_PUBLIC / "animations"
FBX_TMP         = BASE / "fbx_animations"

for d in [MODELS_DIR, ANIMS_DIR, FBX_TMP]:
    d.mkdir(parents=True, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# ── SSE progress queue (one pipeline at a time) ──────────────────────────────
_progress: queue.Queue = queue.Queue()

def emit(msg: str):
    _progress.put(msg)

@app.route('/api/progress')
def progress():
    def stream():
        while True:
            msg = _progress.get()
            yield f"data: {msg}\n\n"
            if msg.startswith("DONE") or msg.startswith("ERROR"):
                break
    return Response(stream(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ── Upload avatar ─────────────────────────────────────────────────────────────
@app.route('/api/upload-avatar', methods=['POST'])
def upload_avatar():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    f = request.files['file']
    if not f.filename.endswith('.glb'):
        return jsonify({'error': 'Only .glb allowed'}), 400
    dest = MODELS_DIR / 'avatar.glb'
    f.save(dest)
    return jsonify({'success': True, 'path': str(dest)})


# ── Full pipeline ─────────────────────────────────────────────────────────────
@app.route('/api/pipeline', methods=['POST'])
def run_pipeline():
    data = request.json or {}
    token        = data.get('token', '').strip()
    character_id = data.get('character_id', '').strip()

    avatar_glb = MODELS_DIR / 'avatar.glb'
    if not avatar_glb.exists():
        return jsonify({'error': 'Upload avatar first'}), 400
    if not token:
        return jsonify({'error': 'Mixamo token required'}), 400

    def run():
        try:
            # Step 1 — GLB → FBX
            emit("STEP:Converting GLB to FBX...")
            avatar_fbx = MODELS_DIR / 'avatar.fbx'
            r = subprocess.run(
                ['blender', '--background', '--python', str(BASE / 'glb-to-fbx.py'),
                 '--', str(avatar_glb)],
                capture_output=True, text=True, timeout=180
            )
            # glb-to-fbx.py outputs next to input, so it lands in MODELS_DIR
            if not avatar_fbx.exists():
                emit(f"ERROR:GLB→FBX failed\n{r.stderr[-500:]}")
                return

            # Step 2 — Mixamo download → FBX_TMP
            emit("STEP:Downloading animations from Mixamo (this takes a few minutes)...")
            cmd = ['python3', str(BASE / 'autodownloadanim.py'),
                   '--token', token,
                   '--fbx', str(avatar_fbx),
                   '--output', str(FBX_TMP)]
            if character_id:
                cmd = ['python3', str(BASE / 'autodownloadanim.py'),
                       '--token', token,
                       '--character-id', character_id,
                       '--output', str(FBX_TMP)]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

            fbx_files = list(FBX_TMP.glob('*.fbx'))
            if not fbx_files:
                emit(f"ERROR:No FBX downloaded\n{r.stdout[-800:]}")
                return

            emit(f"STEP:Downloaded {len(fbx_files)} animations. Converting FBX → GLB...")

            # Step 3 — FBX → GLB into public/animations/
            r = subprocess.run(
                ['blender', '--background', '--python', str(BASE / 'fbx-to-glb.py'),
                 '--', str(FBX_TMP), '--out', str(ANIMS_DIR)],
                capture_output=True, text=True, timeout=600
            )
            glb_files = list(ANIMS_DIR.glob('*.glb'))
            if not glb_files:
                emit(f"ERROR:FBX→GLB failed\n{r.stderr[-500:]}")
                return

            emit(f"DONE:{len(glb_files)} animations ready")

        except subprocess.TimeoutExpired as e:
            emit(f"ERROR:Timeout — {e}")
        except Exception as e:
            emit(f"ERROR:{e}")

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'success': True})


if __name__ == '__main__':
    print("🚀 AutoAnim server on http://localhost:5000")
    app.run(debug=False, port=5000, threaded=True)
