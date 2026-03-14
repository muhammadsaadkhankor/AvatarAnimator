"""
Step 3: Convert animation FBX files → GLB
Run via: blender --background --python step3_fbx_to_glb.py -- ./animations/
Output:  .glb files next to each .fbx (same name)

Examples:
  # Convert all FBX in animations/ folder
  blender --background --python step3_fbx_to_glb.py -- ./animations/

  # Convert a single file
  blender --background --python step3_fbx_to_glb.py -- ./animations/talking_1.fbx

  # Convert to a different output folder
  blender --background --python step3_fbx_to_glb.py -- ./animations/ --out ./glb_animations/
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
    # Force-remove ALL data blocks so nothing leaks between conversions
    for block in list(bpy.data.actions):
        bpy.data.actions.remove(block)
    for block in list(bpy.data.armatures):
        bpy.data.armatures.remove(block)
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)
    for block in list(bpy.data.materials):
        bpy.data.materials.remove(block)


def convert_fbx_to_glb(fbx_path, glb_path):
    """Import FBX animation and export as GLB."""
    clear_scene()

    # Import FBX
    bpy.ops.import_scene.fbx(
        filepath=str(fbx_path),
        use_anim=True,
        ignore_leaf_bones=True,
        automatic_bone_orientation=True,
    )

    imported = bpy.context.selected_objects
    obj_types = [f"{o.name}({o.type})" for o in imported]
    print(f"   Imported: {', '.join(obj_types)}")

    # Select everything for export
    bpy.ops.object.select_all(action='SELECT')

    # Export GLB
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format='GLB',
        use_selection=False,
        export_animations=True,
        export_frame_range=True,
        export_anim_single_armature=True,
    )

    size_kb = os.path.getsize(glb_path) / 1024
    print(f"   ✅ {glb_path.name} ({size_kb:.0f} KB)")


def main():
    args = get_args()
    if not args:
        print("Usage:")
        print("  blender --background --python step3_fbx_to_glb.py -- ./animations/")
        print("  blender --background --python step3_fbx_to_glb.py -- file.fbx")
        sys.exit(1)

    input_path = Path(args[0])

    # Check for --out flag
    output_dir = None
    if len(args) >= 3 and args[1] == "--out":
        output_dir = Path(args[2])
        output_dir.mkdir(parents=True, exist_ok=True)

    # Collect FBX files
    if input_path.is_dir():
        fbx_files = sorted(input_path.glob("*.fbx"))
    elif input_path.is_file() and input_path.suffix.lower() == ".fbx":
        fbx_files = [input_path]
    else:
        print(f"❌ Not a valid FBX file or directory: {input_path}")
        sys.exit(1)

    if not fbx_files:
        print(f"❌ No .fbx files found in: {input_path}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"  FBX → GLB Converter")
    print(f"  Files: {len(fbx_files)}")
    print(f"  Output: {output_dir or 'same folder as FBX'}")
    print(f"{'='*50}\n")

    success = 0
    for i, fbx in enumerate(fbx_files, 1):
        # Output path: same name, .glb extension
        if output_dir:
            glb = output_dir / fbx.with_suffix(".glb").name
        else:
            glb = fbx.with_suffix(".glb")

        print(f"[{i}/{len(fbx_files)}] {fbx.name} → {glb.name}")

        try:
            convert_fbx_to_glb(fbx, glb)
            success += 1
        except Exception as e:
            print(f"   ❌ Failed: {e}")

    print(f"\n{'='*50}")
    print(f"  ✅ Converted: {success}/{len(fbx_files)}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()