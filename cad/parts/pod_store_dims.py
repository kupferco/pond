# cad/parts/pod_store_dims.py: the pod store's shared numbers (OpenPocket #461), read by cad/pond_unit_bottom.py (the drawing) and exported to the sim
# (control-ui/src/podgrab/layout.ts), so the slope is defined once. mm / degrees.
# Gravity-feed store (owner decision, 26 Nov): 7 lanes sloping DOWN towards the front; each lane ends in a short flat landing at the front row with a stop lip,
# so the pod being picked stands vertical and the next one slides forward onto the landing when it is lifted.
# 15 degrees is ASSUMED (enough for a dry plastic net pot to slide): test with the real dry pots.
STORE_SLOPE_DEG = 15.0
