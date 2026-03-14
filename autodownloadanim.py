#!/usr/bin/env python3
"""
Step 2: Upload FBX to Mixamo → Auto-download all animations as FBX
====================================================================

Usage:
  python step2_mixamo_download.py --fbx avatar.fbx --token YOUR_TOKEN
  python step2_mixamo_download.py --character-id CHAR_ID --token YOUR_TOKEN

The token comes from Mixamo website:
  1. Log into mixamo.com in Chrome
  2. Press F12 → Console tab
  3. Type:  localStorage.access_token
  4. Copy the value (without quotes)

Animations are saved to ./animations/ folder as .fbx files.
"""

import os
import sys
import time
import json
import argparse
import urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Missing package. Run:")
    print("   pip install requests")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
#  YOUR ANIMATION LIST — Edit this!
# ═══════════════════════════════════════════════════════════════════════════════
#  Format: "filename_without_extension": "Mixamo search query"
#  The search query should match what you'd type in Mixamo's search bar.

ANIMATIONS = {
    "Idle":                     "Standing idle",
    "Talking":                  "Asking A Question With One Hand",
    "Angry":                    "Angry Forward Gesture",
    "Sad":                      "Standing in a Sad Disposition",
    "Surprised":                "Being Surprised And Looking Right",
    "Disappointed":             "Disappointed Awe-Shucks",
    "Thoughtfullheadshake":     "Shaking Head No Thoughfully",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  EXPORT SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

FORMAT = "fbx7"       # FBX binary
SKIN   = "false"      # "false" = bones only (no mesh), "true" = with avatar mesh
FPS    = "30"
REDUCEKF = "0"        # 0 = no keyframe reduction

# Timing
DELAY_BETWEEN = 3     # seconds between downloads (avoid rate limit)
RETRY_WAIT    = 3     # seconds to wait on 429
MAX_RETRIES   = 15
MONITOR_TIMEOUT = 90  # seconds to wait for export


# ═══════════════════════════════════════════════════════════════════════════════
#  MIXAMO API — real endpoints from mixamo.com
# ═══════════════════════════════════════════════════════════════════════════════

API = "https://www.mixamo.com/api/v1"


def make_headers(token):
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-Api-Key": "mixamo2",
    }


def api_get(url, token, params=None, retries=MAX_RETRIES):
    """GET with retry on 429."""
    headers = make_headers(token)
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            if r.status_code == 429:
                wait = RETRY_WAIT * (attempt + 1)
                print(f"      ⏱️ Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code == 401:
                print("\n❌ Token expired! Get a new one:")
                print("   mixamo.com → F12 → Console → localStorage.access_token\n")
                sys.exit(1)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(RETRY_WAIT)
                continue
            raise
    raise RuntimeError(f"Failed after {retries} retries: GET {url}")


def api_post(url, token, body, retries=MAX_RETRIES):
    """POST with retry on 429."""
    headers = {**make_headers(token), "X-Requested-With": "XMLHttpRequest"}
    for attempt in range(retries):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=30)
            if r.status_code == 429:
                wait = RETRY_WAIT * (attempt + 1)
                print(f"      ⏱️ Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code == 401:
                print("\n❌ Token expired! Get a new one from mixamo.com console.\n")
                sys.exit(1)
            r.raise_for_status()
            return r.json() if r.text.strip() else {}
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(RETRY_WAIT)
                continue
            raise
    raise RuntimeError(f"Failed after {retries} retries: POST {url}")


def search_animations(query, token, char_id=None):
    """Search Mixamo animations using exact working URL format."""
    encoded = urllib.parse.quote(query)
    url = f"{API}/products?page=1&limit=96&order=&type=Motion%2CMotionPack&query={encoded}"
    if char_id:
        url += f"&character_id={char_id}"
    headers = make_headers(token)
    for attempt in range(MAX_RETRIES):
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 429:
            wait = RETRY_WAIT * (attempt + 1)
            print(f"      ⏱️ Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        if r.status_code == 401:
            print("\n❌ Token expired! Get a new one from mixamo.com console.\n")
            sys.exit(1)
        if r.status_code != 200:
            print(f"      ⚠️ Search returned {r.status_code}: {r.text[:200]}")
            return []
        return r.json().get("results", [])
    return []


# ═══════════════════════════════════════════════════════════════════════════════
#  UPLOAD CHARACTER
# ═══════════════════════════════════════════════════════════════════════════════

def upload_character(fbx_path, token):
    """Upload FBX to Mixamo, wait for auto-rig, return character_id."""
    fbx_path = Path(fbx_path)
    size_kb = fbx_path.stat().st_size / 1024
    print(f"\n📤 Uploading: {fbx_path.name} ({size_kb:.0f} KB)")

    # Request upload slot
    headers = make_headers(token)
    r = requests.post(f"{API}/characters",
                       headers=headers,
                       json={"filename": fbx_path.name, "type": "upload"},
                       timeout=30)
    r.raise_for_status()
    data = r.json()

    upload_url = data.get("upload_url") or data.get("url")
    char_id = data.get("character_id") or data.get("id") or data.get("uuid")

    # Upload the file
    if upload_url:
        print("   ⬆️  Uploading to cloud...")
        with open(fbx_path, "rb") as f:
            up = requests.put(upload_url, data=f.read(),
                              headers={"Content-Type": "application/octet-stream"},
                              timeout=120)
            if up.status_code not in (200, 201, 204):
                raise RuntimeError(f"Upload failed: {up.status_code}")

    if not char_id:
        raise RuntimeError(
            "Could not get character_id from Mixamo.\n"
            "Try uploading manually at mixamo.com, then use --character-id"
        )

    print(f"   ✅ Uploaded! character_id = {char_id}")

    # Wait for auto-rig
    print("   ⏳ Auto-rigging", end="", flush=True)
    for _ in range(60):
        try:
            data = api_get(f"{API}/characters/{char_id}", token)
            status = str(data.get("status", "")).lower()
            if status in ("completed", "rigged", "ready"):
                print(" ✅")
                return char_id
            if "error" in status or "fail" in status:
                raise RuntimeError(f"Rig failed: {data}")
        except Exception:
            pass
        time.sleep(3)
        print(".", end="", flush=True)

    raise TimeoutError("Auto-rig timed out after 3 minutes")


# ═══════════════════════════════════════════════════════════════════════════════
#  DOWNLOAD ONE ANIMATION
# ═══════════════════════════════════════════════════════════════════════════════

def download_one(anim_id, anim_name, char_id, token, out_path):
    """
    Full download flow for one animation:
      1. GET product details → gms_hash
      2. POST export request
      3. GET monitor → poll until download URL ready
      4. Download FBX file
    """

    # 1. Get animation details (gms_hash)
    data = api_get(f"{API}/products/{anim_id}",
                   token, params={"similar": 0, "character_id": char_id})

    gms_hash = data.get("details", {}).get("gms_hash")
    if not gms_hash:
        print("      ⚠️  No gms_hash, skipping")
        return False

    # Flatten params list → comma string (required by export API)
    if isinstance(gms_hash.get("params"), list):
        pvals = ",".join(str(p[1]) for p in gms_hash["params"])
        gms_hash = {**gms_hash, "params": pvals}

    # 2. Request export
    export_body = {
        "character_id": char_id,
        "gms_hash": [gms_hash],
        "preferences": {"format": FORMAT, "skin": SKIN, "fps": FPS, "reducekf": REDUCEKF},
        "product_name": anim_name,
        "type": "Motion",
    }
    api_post(f"{API}/animations/export", token, export_body)

    # 3. Monitor until ready
    download_url = None
    for _ in range(MONITOR_TIMEOUT):
        data = api_get(f"{API}/characters/{char_id}/monitor", token)
        status = data.get("status", "")

        if status == "completed" and data.get("job_result"):
            download_url = data["job_result"]
            break
        elif status == "processing":
            time.sleep(1)
            continue
        elif status == "failed":
            print(f"      ❌ Export failed: {data.get('message', '')}")
            return False
        else:
            time.sleep(1)

    if not download_url:
        print("      ❌ Export timed out")
        return False

    # 4. Download FBX
    print(f"      ⬇️  Downloading...", end=" ", flush=True)
    r = requests.get(download_url, stream=True, timeout=60)
    r.raise_for_status()

    with open(out_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    size_kb = out_path.stat().st_size / 1024
    print(f"✅ {size_kb:.0f} KB")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
#  BATCH DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════════

def batch_download(animations, char_id, token, output_dir, skip_existing=True):
    """Download all animations in the list."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(animations)
    success = 0
    skipped = 0
    failed_list = []

    print(f"\n{'═'*55}")
    print(f"  📦 Downloading {total} animations")
    print(f"  📁 Output: {output_dir.resolve()}")
    print(f"  ⚙️  Format: {FORMAT} | Skin: {SKIN} | FPS: {FPS}")
    print(f"{'═'*55}")

    for i, (filename, search_query) in enumerate(animations.items(), 1):
        out_file = output_dir / f"{filename}.fbx"

        # Skip if cached
        if skip_existing and out_file.exists() and out_file.stat().st_size > 100:
            print(f"\n[{i}/{total}] ⏭️  {filename} (already downloaded)")
            skipped += 1
            success += 1
            continue

        print(f"\n[{i}/{total}] 🔍 '{search_query}' → {filename}.fbx")

        # Search Mixamo using direct URL (bypasses api_get params issue)
        try:
            hits = search_animations(search_query, token, char_id)
        except Exception as e:
            print(f"      ❌ Search failed: {e}")
            failed_list.append(filename)
            continue

        if not hits:
            print(f"      ⚠️  No results for '{search_query}'")
            failed_list.append(filename)
            continue

        # Pick first non-pack result
        anim = None
        for h in hits:
            name = h.get("description", h.get("name", ""))
            if "," not in name:  # skip packs
                anim = h
                break
        if not anim:
            anim = hits[0]

        anim_id = anim.get("id", "")
        anim_name = anim.get("description", anim.get("name", "unknown"))
        print(f"      📋 Found: '{anim_name}'")

        # Download
        try:
            ok = download_one(anim_id, anim_name, char_id, token, out_file)
            if ok:
                success += 1
            else:
                failed_list.append(filename)
        except Exception as e:
            print(f"      ❌ Error: {e}")
            failed_list.append(filename)

        # Don't hammer the API
        time.sleep(DELAY_BETWEEN)

    # ── Summary ──
    print(f"\n{'═'*55}")
    print(f"  ✅ Downloaded: {success}/{total}")
    if skipped:
        print(f"  ⏭️  Skipped (cached): {skipped}")
    if failed_list:
        print(f"  ❌ Failed ({len(failed_list)}):")
        for f in failed_list:
            print(f"     - {f}")
    print(f"  📁 All files in: {output_dir.resolve()}")
    print(f"{'═'*55}\n")

    return success


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Mixamo Auto-Downloader: Upload FBX → Download animations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
HOW TO GET YOUR TOKEN:
  1. Chrome → mixamo.com → log in
  2. F12 → Console tab
  3. Type: localStorage.access_token
  4. Copy the value (without quotes)

EXAMPLES:
  python step2_mixamo_download.py --fbx avatar.fbx --token YOUR_TOKEN
  python step2_mixamo_download.py --character-id abc123 --token YOUR_TOKEN
  python step2_mixamo_download.py --fbx avatar.fbx --token YOUR_TOKEN --output ./anims/
        """,
    )
    parser.add_argument("--fbx", help="Avatar FBX file to upload to Mixamo")
    parser.add_argument("--character-id", help="Skip upload, reuse existing character ID")
    parser.add_argument("--token", default=os.environ.get("MIXAMO_TOKEN", ""),
                        help="Mixamo auth token (or env MIXAMO_TOKEN)")
    parser.add_argument("--output", default="./animations",
                        help="Output directory (default: ./animations)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Re-download even if files exist")

    args = parser.parse_args()

    # Validate
    if not args.token:
        print("""
┌───────────────────────────────────────────────────────────┐
│  ❌ No token provided!                                    │
│                                                           │
│  Get it from Chrome:                                      │
│    1. Go to mixamo.com → log in                           │
│    2. F12 → Console tab                                   │
│    3. Type: localStorage.access_token                     │
│    4. Copy the value                                      │
│                                                           │
│  Then run:                                                │
│    python step2_mixamo_download.py --fbx avatar.fbx \\     │
│           --token "paste_here"                            │
└───────────────────────────────────────────────────────────┘
        """)
        sys.exit(1)

    if not args.fbx and not args.character_id:
        print("❌ Provide --fbx (to upload) or --character-id (to reuse)")
        sys.exit(1)

    # ── Go! ──
    print("""
╔═══════════════════════════════════════════════════════════╗
║        MIXAMO ANIMATION AUTO-DOWNLOADER                   ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # Upload or reuse
    if args.character_id:
        char_id = args.character_id
        print(f"🔗 Reusing character: {char_id}")
    else:
        fbx = Path(args.fbx)
        if not fbx.exists():
            print(f"❌ File not found: {fbx}")
            sys.exit(1)
        char_id = upload_character(str(fbx), args.token)

    # Save character ID for future runs
    print(f"\n💡 TIP: Next time skip upload with:")
    print(f"   --character-id {char_id}\n")

    # Download all animations
    batch_download(
        ANIMATIONS,
        char_id,
        args.token,
        args.output,
        skip_existing=not args.no_cache,
    )

    print(f"🎉 Done! Your animation FBX files are in: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()