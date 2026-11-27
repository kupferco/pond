# cad/unit_structure_drawing.py: the unit's structure (tank with water, frame, spine, growing pipe, track, panel, feet) as the Drawings page shows it from
# OpenPocket #570: cad/unit_v3_aframe.py's unit with the three-seat pipe collar in place of the clamp collars and the spine-to-track connector on the track
# (both from cad/unit_drawing.py). unit_v3_aframe.py itself is unchanged: the track-supports drawing is built from it.
import os
import sys
import cadquery as cq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unit_drawing as ud

assy = cq.Assembly()
for _n, _s, _c in ud.drawing_parts():
    assy.add(_s, name=_n, color=cq.Color(*_c))
result = assy
