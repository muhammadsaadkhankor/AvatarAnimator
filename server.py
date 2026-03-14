#!/usr/bin/env python3
import subprocess
import threading
import queue
from pathlib import Path
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE            = Path(__file__).parent
MODELS_DIR      = BASE / "Animation_mapper" / "public" / "models"
ANIMS_DIR       = BASE / "Animation_mapper" / "public" / "animations"
FBX_TMP         = BASE / "fbx_animations"

for d in [MODELS_DIR, ANIMS_DIR, FBX_TMP]:
    d.mkdir(parents=True, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

_q: queue.Queue = queue.Queue()

def emit(msg: str):
    _q.put(msg)

# ── SSE stream ────────────────────────────────────────────────────────────────
@app.route('/api/progress')
def progress():
    def stream():
        while True:
            msg = _q.get()
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
        return jsonify({'error': 'Only .glb files allowed'}), 400
    dest = MODELS_DIR / 'avatar.glb'
    f.save(dest)
    return jsonify({'success': True})

# ── Run a subprocess and stream every line to SSE ────────────────────────────
def run_streaming(cmd, timeout=900) -> tuple[int, str]:
    """Run cmd, emit each output line live, return (returncode, full_output)."""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,   # merge stderr into stdout
        text=True,
        bufsize=1,
    )
    lines = []
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                lines.append(line)
                emit(f"LOG:{line}")
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1, "\n".join(lines)
    return proc.returncode, "\n".join(lines)

# ── Full pipeline ─────────────────────────────────────────────────────────────
@app.route('/api/pipeline', methods=['POST'])
def run_pipeline():
    data  = request.json or {}
    token = data.get('token', '').strip()

    if not (MODELS_DIR / 'avatar.glb').exists():
        return jsonify({'error': 'Upload avatar first'}), 400
    if not token:
        return jsonify({'error': 'Mixamo token required'}), 400

    def run():
        # ── Step 1: GLB → FBX ────────────────────────────────────────────────
        emit("STEP:Step 1/3 — Converting GLB to FBX...")
        avatar_glb = MODELS_DIR / 'avatar.glb'
        avatar_fbx = MODELS_DIR / 'avatar.fbx'

        rc, out = run_streaming(
            ['blender', '--background', '--python',
             str(BASE / 'glb-to-fbx.py'), '--', str(avatar_glb)],
            timeout=180
        )
        if not avatar_fbx.exists():
            emit(f"ERROR:GLB→FBX failed (code {rc})\n{out[-400:]}")
            return
        emit("STEP:✅ GLB→FBX done")

        # ── Step 2: Mixamo download ───────────────────────────────────────────
        emit("STEP:Step 2/3 — Downloading animations from Mixamo...")

        # Clear old FBX files so we don't mistake them for new downloads
        for old in FBX_TMP.glob('*.fbx'):
            old.unlink()

        cmd = ['python3', str(BASE / 'autodownloadanim.py'),
               '--token', token, '--fbx', str(avatar_fbx),
               '--output', str(FBX_TMP)]

        rc, out = run_streaming(cmd, timeout=900)

        fbx_files = list(FBX_TMP.glob('*.fbx'))
        if not fbx_files:
            emit(f"ERROR:No FBX files downloaded (exit code {rc})\nSee log above for details.")
            return
        emit(f"STEP:✅ Downloaded {len(fbx_files)} FBX animations")

        # ── Step 3: FBX → GLB ────────────────────────────────────────────────
        emit("STEP:Step 3/3 — Converting FBX → GLB...")

        # Clear old GLB animations
        for old in ANIMS_DIR.glob('*.glb'):
            old.unlink()

        rc, out = run_streaming(
            ['blender', '--background', '--python',
             str(BASE / 'fbx-to-glb.py'), '--', str(FBX_TMP), '--out', str(ANIMS_DIR)],
            timeout=600
        )
        glb_files = list(ANIMS_DIR.glob('*.glb'))
        if not glb_files:
            emit(f"ERROR:FBX→GLB conversion failed (code {rc})\n{out[-400:]}")
            return

        emit(f"DONE:{len(glb_files)} animations ready")

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'success': True})


if __name__ == '__main__':
    print("🚀 AutoAnim server → http://localhost:5000")
    app.run(debug=False, port=5000, threaded=True)
