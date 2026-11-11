# Dimension lines for the cart_base drawings (model mm), used by render_outline.py:
#   python cad/render_outline.py cad/cart_base.py docs/gallery/renders cart-base-v1 cad/cart_base_dims.py
# plan view (looking at the plate from -Y): 2D point = (X, Z). side view (looking along -X): (Y, Z).
# Entry: (label, "h" or "v", a, b, offset): "h" runs from u=a to u=b at v=offset; "v" from v=a to v=b at u=offset.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_layout as L
import cart_base as B

x0, x1 = L.PLATE_X0, L.PLATE_X0 + L.PLATE_W
hz = L.HAND_Z
DIMS = {
    "plan": [
        ("plate 100 wide (ASSUMED)", "h", x0, x1, L.PLATE_L / 2 + 22),
        ("plate 332 long (ASSUMED)", "v", -L.PLATE_L / 2, L.PLATE_L / 2, x0 - 56),
        ("hands 220 apart (ASSUMED)", "v", -hz, hz, x1 + 40),
        ("M4 pair 30 apart", "v", hz - 15, hz + 15, x1 + 14),
        ("arm M4 square 50 (ASSUMED)", "v", B.ARM_Z - 25, B.ARM_Z + 25, x0 - 14),
        ("battery 70 long (ASSUMED)", "v", B.BATT_Z - 35, B.BATT_Z + 35, x0 - 35),
    ],
    "side": [
        ("plate 6", "h", L.PLATE_Y0, L.PLATE_Y1, L.PLATE_L / 2 + 14),
        ("battery 50 out (ASSUMED)", "h", L.PLATE_Y0 - L.BATT[1], L.PLATE_Y0, -L.PLATE_L / 2 - 14),
        ("motor 28 dia (ASSUMED)", "h", L.PLATE_Y0 - 28, L.PLATE_Y0, hz + 55 + 20 + 12),
        ("hands 220 apart (ASSUMED)", "v", -hz, hz, L.PLATE_Y1 + 55),
    ],
}
