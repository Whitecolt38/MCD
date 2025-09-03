# scripts/freecad_convert.py
import sys, os, argparse

# FreeCAD inyecta sus módulos al sys.path al lanzar con FreeCADCmd -c script.py
import FreeCAD as App
import Mesh, Part, MeshPart

def mesh_to_solid(mesh_obj, tol=0.1):
    # malla -> shape (caro; aproxima)
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh_obj.Topology, tol)  # tolerancia
    solid = Part.Solid(shape) if shape.Solids else shape
    return solid

def main(inp, outp, target):
    target = target.lower()
    doc = App.newDocument()

    # Carga malla
    m = Mesh.Mesh(inp)

    # Aproximación a sólido
    solid = mesh_to_solid(m, tol=0.1)

    if target == "step":
        Part.export([solid], outp)
    elif target == "iges":
        Part.export([solid], outp)
    else:
        raise RuntimeError(f"Destino no soportado por FreeCAD: {target}")

    doc.saveCompressed = False
    App.closeDocument(doc.Name)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", required=True)
    a = ap.parse_args()
    main(a.inp, a.out, a.target)
