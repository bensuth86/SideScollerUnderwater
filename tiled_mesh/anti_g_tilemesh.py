"""
Mesh generation utilities for Anti-G fields based on TMX tile maps.

This module:
    • Loads TMX tile data
    • Builds an initial velocity mesh from tile layers
    • Applies a Jacobi relaxation method to propagate velocity through empty tiles
    • Computes unit direction vectors
    • Exports and visualises the final mesh

Author: <The Hand>
"""

import pytmx
import numpy as np
import copy
from pytmx import TiledTileLayer
from pathlib import Path
from tiled_mesh.heat_map import visualise_mesh

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------

mesh_types = ['anti_g', 'water_flow']
platform_grav = [20, 20]  # repulsive velocity at platform tile

# Mapping TMX layer names to velocity vectors
layer_to_values = {
    'anti_g':
        {'Platforms': platform_grav,  # Platform
         },
    'waterflow':
        {
        }
}


def apply_jacobi_method(initial_mesh: np.ndarray, empty_mask, tolerance: float = 1.0):
    # ui,j​= 1/4​(ui+1,j​+ui−1,j​+ui,j+1​+ui,j−1​−h2ρi,j​)
    """
    Jacobi method on a 3D mesh (H, W, 2-component vector field).
    Only updates tiles where empty_mask == True.
    Solves:
        u_new = (u_left + u_right) / 2   for x-component
        u_new = (u_up   + u_down) / 2    for y-component
    """
    current_mesh = initial_mesh.copy()
    updated_mesh = current_mesh.copy()

    h, w, vec = current_mesh.shape

    diff = np.inf  # initialize diffence between arr+1 and prior arr to positive infinity to ensure while loop executes at least once

    cnt = 0
    while diff > tolerance:  # solution converges once max(arr+1-arr) < tolerance

        cnt += 1
        # iterate mesh interior, excluding map edges, to update velocity component
        for j in range(1, h - 1):
            for i in range(1, w - 1):
                # only update empty tiles
                if empty_mask[j, i]:
                    # apply Jacobie method along x - axis and update vel.x component
                    updated_mesh[j, i][0] = (current_mesh[j, i - 1][0] + current_mesh[j, i + 1][0]) / 2
                    # print(updated_mesh[j, i][0])
                    # # apply Jacobie method along y - axis and update vel.y component
                    updated_mesh[j, i][1] = (current_mesh[j - 1, i][1] + current_mesh[j + 1, i][1]) / 2
                    # print(updated_mesh[j, i][1])

        # compute difference arr+1 - arr on empty tiles only
        diff_arr = updated_mesh[empty_mask] - current_mesh[empty_mask]
        diff = np.max(np.abs(diff_arr))

        current_mesh[:] = updated_mesh[:]  # update current_mesh for next iteration

    print(f"Jacobi converged after {cnt} iterations")
    # print_array(current_mesh)
    return current_mesh


def get_vector_directions(current_mesh, empty_mask):
    """ Determines the direction of anti_g vector; [1, 0] = right, [-1, 0] = left, [0, 1] = down, [0, -1] = up"""
    h, w, vec = current_mesh.shape
    unit_vec_mesh = np.zeros((h, w, 2), dtype=int)
    for j in range(1, h - 1):
        for i in range(1, w - 1):
            # only update empty tiles
            if empty_mask[j, i]:
                # x component
                dx = current_mesh[j, i - 1][0] - current_mesh[j, i + 1][0]
                unit_vec_mesh[j, i][0] = np.sign(dx)
                # y component
                dy = current_mesh[j - 1, i][1] - current_mesh[j + 1, i][1]
                unit_vec_mesh[j, i][1] = np.sign(dy)

    return unit_vec_mesh


def mesh_setup(map_file):
    """ Creates initial velocity mesh from TMX tiles.
    # Platform tiles are assigned a fixed anti_g velocity vector: platform_grav """

    tmxdata = pytmx.TiledMap(map_file)
    # --- Setup initial mesh --- #

    # empty mesh: height x width x vector(2)
    mesh = np.zeros((tmxdata.height, tmxdata.width, 2), dtype=int)

    for y in range(tmxdata.height):
        for x in range(tmxdata.width):
            for layer in tmxdata.layers:
                if isinstance(layer, TiledTileLayer):
                    gid = layer.data[y][x]
                    if gid != 0:
                        # Assign values if the layer name is recognized under anti_g
                        if layer.name in layer_to_values['anti_g']:
                            mesh[y, x] = layer_to_values['anti_g'][layer.name]

    return mesh


# ---------------------------------------------------------------------
# MESH SOLVER
# ---------------------------------------------------------------------


def generate_mesh(initial_mesh: np.ndarray, empty_mask):
    """ Apply Jacobi method along x or y axis across empty tiles (3D array element vector in form [x, y])
    Update until solution converges at max(arr+1 - arr) < tolerance """

    current_mesh = apply_jacobi_method(initial_mesh, empty_mask, tolerance=1.0)
    unit_vec_mesh = get_vector_directions(current_mesh, empty_mask)  # return corresponding mesh of unit vectors that determine direction (+/-1)

    # Multiply all elements in solved mesh (current_mesh) by corresponding unit direction vectors
    final_mesh = np.where(empty_mask[..., None], current_mesh * unit_vec_mesh, current_mesh)

    return final_mesh


def load_map():
    """Hardcoded loader for a test TMX file."""
    maps_path = Path(
        r"C:\Users\ben_s\Documents\Python_Scripts\PROJECTS\SideScrollerUnderwater\assets\maps"
    )
    map_file = maps_path / "test.tmx"
    return map_file


def export_array(map_file, anti_g_mesh):
    """
    Save mesh as .npy with filename based on TMX map name.
    """
    map_file = Path(map_file)

    # Use the TMX file name without extension
    map_name = map_file.stem

    # Build directory and filename
    output_dir = Path(
        r"C:\Users\ben_s\Documents\Python_Scripts\PROJECTS\SideScrollerUnderwater\assets\mesh_files"
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    # Full path to saved file
    save_path = output_dir / f"{map_name}_anti_g.npy"

    # Save array
    np.save(save_path, anti_g_mesh)

    print(f"Saved mesh to: {save_path}")


def print_array(arr):
    """Pretty-print 2D or 3D array row by row."""

    for row in arr:
        print(" ".join(str(cell) for cell in row))
    print('\n')


def main():
    map_file = load_map()
    initial_mesh = mesh_setup(map_file)
    empty_mask = ~np.all(initial_mesh == platform_grav, axis=2)  # mask for empty tiles between platforms
    final_mesh = generate_mesh(initial_mesh, empty_mask)
    print_array(final_mesh)
    export_array(map_file, final_mesh)
    visualise_mesh(final_mesh, title="Anti_g Mesh Field")


if __name__ == "__main__":
    main()
