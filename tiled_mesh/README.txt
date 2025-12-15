######################################################

"""
Mesh generation utilities for Anti-G, Waterflow fields based on TMX tile maps.

This module:
    • Loads TMX tile data
    • Builds an initial velocity mesh from tile layers
    • Applies a Jacobi relaxation method to propagate velocity through empty tiles
    • Computes unit direction vectors
    • Exports and visualises the final mesh

Exports to C:\Users\ben_s\Documents\Python_Scripts\PROJECTS\SideScrollerUnderwater\assets\mesh_files

NB- Run anti_g_tilemesh independtly.  Will move this tiled_mesh directory outside Sidescroller project directory later.
