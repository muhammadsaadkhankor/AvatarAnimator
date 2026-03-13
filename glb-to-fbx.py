"""
Step 1: Convert Avaturn GLB → Mixamo-compatible FBX
Run via: blender --background --python step1_glb_to_fbx.py -- avatar.glb
Output:  avatar.fbx (same folder)
"""
import bpy
import sys
import os


def get_args():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    return []


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.armatures:
        if block.users == 0:
            bpy.data.armatures.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def convert(input_glb, output_fbx):
    print(f"\n{'='*50}")
    print(f"  GLB → FBX Converter")
    print(f"  Input:  {input_glb}")
    print(f"  Output: {output_fbx}")
    print(f"{'='*50}\n")

    # Clean slate
    clear_scene()

    # Import GLB
    print("📥 Importing GLB...")
    bpy.ops.import_scene.gltf(filepath=input_glb)

    imported = bpy.context.selected_objects
    print(f"   Found {len(imported)} objects")

    for obj in imported:
        print(f"   - {obj.name} ({obj.type})")

    # Apply all transforms
    print("🔧 Applying transforms...")
    bpy.ops.object.select_all(action='SELECT')
    for obj in bpy.context.selected_objects:
        bpy.context.view_layer.objects.active = obj
        try:
            bpy.ops.object.transform_apply(
                location=True, rotation=True, scale=True
            )
        except Exception:
            pass

    # Export FBX
    print("📤 Exporting FBX...")
    bpy.ops.export_scene.fbx(
        filepath=output_fbx,
        use_selection=False,
        embed_textures=True,
        path_mode='COPY',
        apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z',
        axis_up='Y',
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        add_leaf_bones=False,
        bake_anim=False,
        use_armature_deform_only=True,
    )

    size_mb = os.path.getsize(output_fbx) / (1024 * 1024)
    print(f"\n✅ Done! {output_fbx} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    args = get_args()
    if not args:
        print("Usage: blender --background --python step1_glb_to_fbx.py -- avatar.glb")
        sys.exit(1)

    input_glb = os.path.abspath(args[0])
    if not os.path.exists(input_glb):
        print(f"❌ File not found: {input_glb}")
        sys.exit(1)

    # Output: same name, .fbx extension, same folder
    output_fbx = os.path.splitext(input_glb)[0] + ".fbx"

    convert(input_glb, output_fbx)