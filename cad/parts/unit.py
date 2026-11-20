# cad/parts/unit.py: the unit as an ordered list of (name, shape, colour), built ONLY from the part files in this package.
# unit_v3_aframe.py, track_supports.py, complete_unit.py and water_station.py all take their unit geometry from here.
from . import unit_frame as uf
from .tank import tank_shell, tank_lid, COLOR_TANK, COLOR_LID
from .track import track_loop, COLOR_TRACK
from .water_volume import water_volume, COLOR_WATER, PART_NAME as WATER_NAME

GREY, ORANGE, DARK = (0.55, 0.57, 0.6, 1), (0.95, 0.6, 0.2, 1), (0.2, 0.2, 0.2, 1)


def unit_parts(water=True):
    (collar_a, legs_a), (collar_b, legs_b) = uf.collars_and_legs()
    out = [("tank", tank_shell(), COLOR_TANK)]
    if water:
        out.append((WATER_NAME, water_volume(), COLOR_WATER))
    out += [
        ("lid", tank_lid(), COLOR_LID),
        ("socket", uf.pipe_socket(), ORANGE),
        ("growing_pipe", uf.growing_pipe(), (0.95, 0.95, 0.95, 0.5)),
        ("spine_tube", uf.spine_tube(), (0.35, 0.35, 0.35, 1)),
        ("track_loop", track_loop(), COLOR_TRACK),
        ("spine_brackets", uf.spine_brackets(), DARK),
        ("clamp_collars_50mm", collar_a.union(collar_b), GREY),
        ("lower_aframe_and_back_strut_16mm", legs_a, ORANGE),
        ("top_triangle_legs_16mm", legs_b, ORANGE),
        ("internal_spacers", uf.internal_spacers(), (0.1, 0.1, 0.1, 1)),
        ("base_bar_and_lid_plates", uf.lid_plates(), GREY),
        ("top_bar", uf.top_bar(), GREY),
        ("solar_panel_30W", uf.solar_panel(), (0.08, 0.12, 0.35, 1)),
        ("panel_rails_and_posts", uf.panel_mount(), GREY),
        ("fold_out_feet", uf.fold_out_feet(), DARK),
        ("sandbags", uf.sandbags(), (0.8, 0.7, 0.45, 1)),
    ]
    return out
