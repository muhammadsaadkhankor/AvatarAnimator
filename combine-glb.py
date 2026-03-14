"""
Combine avatar GLB with animation GLBs into a single file
Usage: blender --background --python combine-glb.py -- <avatar.glb> <animations-dir> <output.glb>
"""

import bpy
import sys
import os
from pathlib import Path


def get_args():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    return []


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.actions):
        bpy.data.actions.remove(block)
    for block in list(bpy.data.armatures):
        bpy.data.armatures.remove(block)
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)
    for block in list(bpy.data.materials):
        bpy.data.materials.remove(block)


def main():
    args = get_args()
    if len(args) < 3:
        print("Usage: blender --background --python combine-glb.py -- <avatar.glb> <animations-dir> <output.glb>")
        sys.exit(1)

    avatar_path = Path(args[0])
    animations_dir = Path(args[1])
    output_path = Path(args[2])

    print(f"\n{'='*60}")
    print(f"  GLB Animation Combiner")
    print(f"  Avatar: {avatar_path.name}")
    print(f"  Animations: {animations_dir}")
    print(f"  Output: {output_path.name}")
    print(f"{'='*60}\n")

    clear_scene()

    # Import avatar
    print("📥 Loading avatar...")
    bpy.ops.import_scene.gltf(filepath=str(avatar_path))
    
    # Get armature
    armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
            break
    
    if not armature:
        print("❌ No armature found in avatar!")
        sys.exit(1)
    
    print(f"   ✅ Found armature: {armature.name}")

    # Load animations
    print("\n📥 Loading animations...")
    anim_files = sorted(animations_dir.glob("*.glb"))
    
    for anim_file in anim_files:
        anim_name = anim_file.stem
        print(f"   Loading {anim_name}...")
        
        # Import animation GLB
        bpy.ops.import_scene.gltf(filepath=str(anim_file))
        
        # Find the imported action
        if bpy.data.actions:
            action = bpy.data.actions[-1]  # Get last imported action
            action.name = anim_name
            print(f"   ✅ {anim_name} ({len(action.fcurves)} curves)")

    print(f"\n🎬 Total animations: {len(bpy.data.actions)}")

    # Export combined GLB
    print(f"\n💾 Exporting to {output_path.name}...")
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format='GLB',
        use_selection=False,
        export_animations=True,
        export_all_influences=True
    )

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ Success! {output_path.name} ({size_mb:.2f} MB)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
