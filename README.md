# 🎭 AutoAnim - Automated Mixamo Animation Pipeline

Complete automation for downloading Mixamo animations and combining them with your avatar.

## ✨ Features

- 📤 Upload avatar GLB
- 🔄 Auto-convert GLB ↔ FBX
- 🎬 Auto-download 7 animations from Mixamo
- 📦 Combine avatar + all animations into single GLB
- 💾 Export individual animation GLBs
- 🎨 Beautiful modern UI

## 📋 Requirements

- **Python 3.8+**
- **Node.js 18+**
- **Blender** (must be in PATH)
- **Mixamo account**

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Node.js dependencies (root)
npm install

# Frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Start Backend

```bash
python server.py
```

Server runs on `http://localhost:5000`

### 3. Start Frontend

```bash
cd frontend
npm run dev
```

Frontend runs on `http://localhost:5173`

### 4. Use the Pipeline

1. Open `http://localhost:5173`
2. Upload your avatar GLB file
3. Get Mixamo token:
   - Go to [mixamo.com](https://mixamo.com) and login
   - Press `F12` → Console
   - Type: `localStorage.access_token`
   - Copy the token value
4. Paste token in UI
5. Click "Start Pipeline"
6. Wait 5-10 minutes
7. Download combined GLB with all animations!

## 📁 Folder Structure

```
AutoAnim/
├── server.py                    # Flask backend
├── combine-animations.mjs       # GLB combiner script
├── autodownloadanim.py         # Mixamo downloader
├── glb-to-fbx.py               # GLB → FBX converter
├── fbx-to-glb.py               # FBX → GLB converter
├── frontend/                    # React UI
│   ├── src/
│   │   ├── App.tsx
│   │   └── App.css
│   └── package.json
├── uploads/                     # Uploaded avatars
├── fbx_animations/             # Downloaded FBX animations
├── animations/                  # Converted GLB animations
└── output/                      # Final combined GLB
```

## 🎬 Animation List

The pipeline downloads these 7 animations:

1. **Idle** - Standing idle
2. **Talking** - Asking A Question With One Hand
3. **Angry** - Angry Forward Gesture
4. **Sad** - Standing in a Sad Disposition
5. **Surprised** - Being Surprised And Looking Right
6. **Disappointed** - Disappointed Awe-Shucks
7. **Thoughtfullheadshake** - Shaking Head No Thoughtfully

Edit `autodownloadanim.py` to customize the animation list.

## 🔧 Pipeline Steps

1. **Upload** - Avatar GLB uploaded to `uploads/`
2. **GLB→FBX** - Convert avatar for Mixamo compatibility
3. **Mixamo** - Auto-download animations to `fbx_animations/`
4. **FBX→GLB** - Convert animations to GLB in `animations/`
5. **Combine** - Merge avatar + animations into `output/avatar_with_animations.glb`
6. **Done** - Download combined file or individual animations

## 📦 Output Files

- **Combined GLB**: `output/avatar_with_animations.glb` - Avatar with all 7 animations embedded
- **Individual GLBs**: `animations/*.glb` - Each animation as separate file
- **FBX Originals**: `fbx_animations/*.fbx` - Original Mixamo downloads

## 🎯 Use Cases

- Game development (Unity, Unreal, Godot)
- Web 3D (Three.js, Babylon.js)
- VR/AR applications
- Animation prototyping
- Character rigging workflows

## 🐛 Troubleshooting

**Token expired**: Get a fresh token from Mixamo (they expire quickly)

**Blender not found**: Add Blender to your system PATH

**Conversion fails**: Ensure avatar has proper armature/skeleton

**Missing animations**: Check `fbx_animations/` folder for FBX files

## 📝 License

MIT

## 🙏 Credits

- Mixamo for animations
- Three.js for GLB processing
- Blender for format conversion
