# Mixamo Animation Pipeline

Automated pipeline to convert avatars and download animations from Mixamo.

## Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies
```bash
cd frontend
npm install
```

## Usage

### Step 1: Start the Backend Server
```bash
python server.py
```
Server will run on `http://localhost:5000`

### Step 2: Start the Frontend
```bash
cd frontend
npm run dev
```
Frontend will run on `http://localhost:5173`

### Step 3: Use the UI

1. **Upload your avatar GLB file**
2. **Get Mixamo token:**
   - Go to [mixamo.com](https://mixamo.com)
   - Login
   - Press F12 → Console tab
   - Type: `localStorage.access_token`
   - Copy the token value
3. **Paste the token** in the UI
4. **Click "Start Pipeline"**

The system will:
- Convert GLB → FBX
- Upload to Mixamo
- Download all animations (defined in `autodownloadanim.py`)
- Convert animations to GLB
- Show download links

## Animation List

Edit the `ANIMATIONS` dictionary in `autodownloadanim.py` to customize which animations to download:

```python
ANIMATIONS = {
    "Idle": "Standing idle",
    "Talking": "Asking A Question With One Hand",
    "Angry": "Angry Forward Gesture",
    # Add more...
}
```

## Requirements

- Python 3.8+
- Blender (must be in PATH)
- Node.js 18+
- Mixamo account

## Folder Structure

```
AutoAnim/
├── server.py              # Flask backend
├── autodownloadanim.py    # Mixamo downloader
├── glb-to-fbx.py         # GLB → FBX converter
├── fbx-to-glb.py         # FBX → GLB converter
├── requirements.txt       # Python deps
├── frontend/             # React UI
│   ├── src/
│   │   ├── App.tsx
│   │   └── App.css
│   └── package.json
├── uploads/              # Uploaded avatars
└── animations/           # Downloaded animations
```
