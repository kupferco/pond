import cadquery as cq

OD = 33.7; WALL = 2.0; ID = OD - 2*WALL
SP_OD = ID - 0.3; SP_ID = SP_OD - 4.0
SEC = 250.0; SP_IN = 100.0; SP_OUT = 100.0
KEY_W = 3.0; KEY_H = 12.0; SLOT_W = 3.4; SLOT_D = 16.0
TUBE_D = 10.0; CORD_D = 4.0

def tube(od, idd, h):
    return cq.Workplane("XY").circle(od/2).circle(idd/2).extrude(h)

def lower_section():
    s = tube(OD, ID, SEC)
    sp = tube(SP_OD, SP_ID, SP_IN + SP_OUT).translate((0, 0, SEC - SP_IN))
    key = (cq.Workplane("XY").box(KEY_W, WALL, KEY_H, centered=(True, False, False))
           .translate((0, SP_OD/2 - 0.2, SEC + 4)))
    return s.union(sp).union(key)

def upper_section():
    s = tube(OD, ID, SEC)
    slot = (cq.Workplane("XY").box(SLOT_W, WALL*3, SLOT_D, centered=(True, False, False))
            .translate((0, ID/2 - 0.5, 0)))
    return s.cut(slot)

def bore(z0, h):
    t = cq.Workplane("XY").circle(TUBE_D/2).extrude(h).translate((-5.5, 0, z0))
    c = cq.Workplane("XY").circle(CORD_D/2).extrude(h).translate((6.5, 0, z0))
    return t.union(c)

GAP = 150.0
# exploded at x=0
low_e = lower_section()
up_e = upper_section().translate((0, 0, SEC + GAP))
bore_e = bore(0, 2*SEC + GAP)
# joined at x=120
low_j = lower_section().translate((120, 0, 0))
up_j = upper_section().translate((120, 0, SEC))
bore_j = bore(0, 2*SEC).translate((120, 0, 0))

result = (cq.Workplane("XY").add(low_e).add(up_e).add(bore_e)
          .add(low_j).add(up_j).add(bore_j))
