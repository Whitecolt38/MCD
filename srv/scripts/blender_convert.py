# scripts/blender_convert.py
import bpy, argparse, os, sys

def import_any(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in [".obj"]:  bpy.ops.import_scene.obj(filepath=path)
    elif ext in [".stl"]: bpy.ops.import_mesh.stl(filepath=path)
    elif ext in [".ply"]: bpy.ops.import_mesh.ply(filepath=path)
    elif ext in [".fbx"]: bpy.ops.import_scene.fbx(filepath=path)
    elif ext in [".gltf", ".glb"]: bpy.ops.import_scene.gltf(filepath=path)
    elif ext in [".blend"]: bpy.ops.wm.open_mainfile(filepath=path)
    else:
        raise RuntimeError(f"Formato de entrada no soportado por Blender: {ext}")

def main(inp, outp, target):
    # Limpia escena
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_any(inp)

    t = target.lower()
    if t == "blend":
        bpy.ops.wm.save_as_mainfile(filepath=outp)
    else:
        # si quisieras exportar a otros: obj/stl/fbx/gltf…
        if t == "obj":  bpy.ops.export_scene.obj(filepath=outp)
        elif t == "stl": bpy.ops.export_mesh.stl(filepath=outp)
        elif t == "ply": bpy.ops.export_mesh.ply(filepath=outp)
        elif t == "fbx": bpy.ops.export_scene.fbx(filepath=outp)
        elif t in ("gltf","glb"): bpy.ops.export_scene.gltf(filepath=outp, export_format="GLB" if t=="glb" else "GLTF_SEPARATE")
        else:
            raise RuntimeError(f"Destino no soportado por Blender: {t}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", required=True)
    a = ap.parse_args()
    main(a.inp, a.out, a.target)
