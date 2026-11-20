# cad/parts/common.py: small CadQuery helpers shared by the part files (mm, Z up). Not parts themselves.
import cadquery as cq


def box(sx, sy, sz, cx, cy, z0):
    """Box sx x sy x sz centred in x and y at (cx, cy), bottom face at z0."""
    return cq.Workplane("XY").box(sx, sy, sz, centered=(True, True, False)).translate((cx, cy, z0))


def cyl(r, h, x, y, z0):
    """Cylinder along Z, bottom at z0."""
    return cq.Workplane("XY").circle(r).extrude(h).translate((x, y, z0))


def tube(ro, ri, h, x, y, z0):
    return cyl(ro, h, x, y, z0).cut(cyl(ri, h + 2, x, y, z0 - 1))


def tdir(ro, ri, L, p, d):
    """Tube of length L from point p along direction d."""
    p = cq.Vector(*p)
    d = cq.Vector(*d).normalized()
    o = cq.Solid.makeCylinder(ro, L, p, d)
    i = cq.Solid.makeCylinder(ri, L + 2, p - d, d)
    return cq.Workplane("XY").add(o.cut(i))


def union_all(parts):
    out = None
    for p in parts:
        out = p if out is None else out.union(p)
    return out


def hose(r, pts):
    """Solid hose of radius r along a polyline of points (x, y, z), with a ball at each bend."""
    out = None
    for a, b in zip(pts, pts[1:]):
        v = cq.Vector(*b) - cq.Vector(*a)
        s = cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, cq.Vector(*a), v.normalized()))
        out = s if out is None else out.union(s)
    for p in pts[1:-1]:
        out = out.union(cq.Workplane("XY").add(cq.Solid.makeSphere(r, cq.Vector(*p), cq.Vector(0, 0, 1), -90, 90, 360)))
    return out


def vol(w):
    return sum(s.Volume() for s in w.solids().vals()) if w.solids().vals() else 0.0


def inter(a, b):
    """Volume of the overlap of two workplanes (bounding-box test first, so it is fast when they are apart)."""
    bb, cc = a.val().BoundingBox(), b.val().BoundingBox()
    if bb.xmax < cc.xmin or cc.xmax < bb.xmin or bb.ymax < cc.ymin or cc.ymax < bb.ymin or bb.zmax < cc.zmin or cc.zmax < bb.zmin:
        return 0.0
    return vol(a.intersect(b))
