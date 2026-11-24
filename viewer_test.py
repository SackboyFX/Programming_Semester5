"""3D test: loads an IFC, turns every element into triangles and shows them in NiceGUI with Plotly.

Run it directly: python viewer_test.py
- Elements with PsetCheck.Status = PASS → green, FAIL → red, no PsetCheck → grey.
  Use a *_checked.ifc from the app to see colours, or the original IFC for all grey.
- The terminal prints how long the geometry took and how many triangles there are.
"""
import multiprocessing
import time

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import numpy as np
import plotly.graph_objects as go
from nicegui import ui

IFC_PATH = r"C:\Users\mikek\OneDrive - Hochschule Luzern\Semester 5\DT Programming\Coding Project\Beispiele_IfcOpenShell_Pandas SW4\25.011_GoBau.ifc"
SKIP_CLASSES = []   # e.g. ["IfcEarthworksFill"] if one class makes it too slow

# How fine curves are cut into triangles. ifcopenshell's default is 0.001 m (1 mm!) - far too fine for a road model.
# 0.05 m = a curve may be off by up to 5 cm: invisible at road scale, but MUCH fewer triangles and faster.
LINEAR_DEFLECTION = 0.05    # metres
ANGULAR_DEFLECTION = 0.5    # radians (default)

COLOURS = {"PASS": "#3F8A4A", "FAIL": "#C0392B", "NONE": "#A0A0A0"}


def get_status(element):
    """PASS / FAIL from PsetCheck.Status, NONE if the element was never checked."""
    status = ifcopenshell.util.element.get_psets(element).get("PsetCheck", {}).get("Status", "")
    if status.startswith("FAIL"):
        return "FAIL"
    if status == "PASS":
        return "PASS"
    return "NONE"


def build_figure(model):
    """Triangulates all IfcElements and merges them into ONE mesh per colour (fast to draw)."""
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)   # every element at its real position
    settings.set("mesher-linear-deflection", LINEAR_DEFLECTION)
    settings.set("mesher-angular-deflection", ANGULAR_DEFLECTION)

    elements = [e for e in model.by_type("IfcElement") if not any(e.is_a(c) for c in SKIP_CLASSES)]

    # one bucket per colour: all points and all triangles of that colour
    buckets = {key: {"verts": [], "faces": [], "count": 0} for key in COLOURS}
    per_class = {}   # IFC class → [elements, triangles], to see which class is the heavy one

    start = time.time()
    iterator = ifcopenshell.geom.iterator(settings, model, multiprocessing.cpu_count(), include=elements)
    done = 0
    if iterator.initialize():
        while True:
            shape = iterator.get()
            verts = np.array(shape.geometry.verts).reshape(-1, 3)   # points x, y, z
            faces = np.array(shape.geometry.faces).reshape(-1, 3)   # triangles: 3 point numbers each

            element = model.by_id(shape.id)
            stats = per_class.setdefault(element.is_a(), [0, 0])
            stats[0] += 1
            stats[1] += len(faces)

            bucket = buckets[get_status(element)]
            faces = faces + bucket["count"]   # point numbers continue after the points already in the bucket
            bucket["verts"].append(verts)
            bucket["faces"].append(faces)
            bucket["count"] += len(verts)

            done += 1
            if done % 100 == 0:
                print(f"  {done} of {len(elements)} elements triangulated ({time.time() - start:.0f} s)")
            if not iterator.next():
                break
    geom_time = time.time() - start

    print("Heaviest classes (elements, triangles):")
    for ifc_class, (count, tris) in sorted(per_class.items(), key=lambda x: -x[1][1])[:8]:
        print(f"  {ifc_class:30} {count:5} elements  {tris:10,} triangles")

    # Swiss coordinates are huge (2'600'000 / 1'200'000): move everything near 0 so zooming stays smooth
    all_verts = [v for b in buckets.values() for v in b["verts"]]
    if not all_verts:
        return go.Figure(), "No geometry found"
    offset = np.vstack(all_verts).min(axis=0)

    fig = go.Figure()
    triangles = 0
    for key, bucket in buckets.items():
        if not bucket["verts"]:
            continue
        v = np.vstack(bucket["verts"]) - offset
        f = np.vstack(bucket["faces"])
        triangles += len(f)
        fig.add_trace(go.Mesh3d(x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2],
                                color=COLOURS[key], name=key, flatshading=True, showlegend=True))

    fig.update_layout(scene_aspectmode="data", margin=dict(l=0, r=0, t=0, b=0))

    info = (f"{done} of {len(elements)} elements with geometry · {triangles:,} triangles · "
            f"geometry took {geom_time:.1f} s")
    print(info)
    return fig, info


print("Opening IFC ...")
t = time.time()
model = ifcopenshell.open(IFC_PATH)
print(f"Opened in {time.time() - t:.1f} s - now triangulating (this is the slow part)")
fig, info = build_figure(model)

ui.label(info)
ui.plotly(fig).classes("w-full h-[85vh]")

ui.run(native=True)
