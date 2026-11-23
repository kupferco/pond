# cad/parts/pod_store_dims.py: the pod store's shared numbers (OpenPocket #461), read by cad/pod_store_reach.py (the drawing) and exported to the sim
# (control-ui/src/podgrab/layout.ts), so the slope is defined once. mm / degrees.
# The rows slope DOWN towards the pick line at the front (the pods slide there); the store is loaded from the back, where the channel is highest.
# 12 degrees lifted the back end of the 13-pod channel (gate and roof) through the 4 mm lid; 7 degrees keeps the whole store under the lid with 6 mm to spare.
STORE_SLOPE_DEG = 7.0
