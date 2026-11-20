# cad/parts/: the ONE place each part of the Pond unit and cart is defined (OpenPocket #365). See docs/cad-structure.md.
# Every assembly, render, GLB and drawing imports these functions; nothing else may build the same geometry again.
# cad/check_single_source.py fails if two files define the same part.
