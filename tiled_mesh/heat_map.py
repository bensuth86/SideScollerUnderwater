import numpy as np
import matplotlib.pyplot as plt


def visualise_mesh(mesh: np.ndarray, title="Mesh Visualisation"):
    """
    Visualizes a 3D mesh array (H x W x 2) using:
        • A heat map based on vector magnitudes
        • A quiver plot (direction arrows)
    """

    # -----------------------------------------------------
    # Extract vector components from the mesh
    # mesh[:, :, 0] = X component of vectors
    # mesh[:, :, 1] = Y component of vectors
    # -----------------------------------------------------
    vx = mesh[:, :, 0]     # horizontal velocity component
    vy = mesh[:, :, 1]     # vertical velocity component

    # -----------------------------------------------------
    # Compute vector magnitude at each grid cell
    # magnitude = sqrt(vx^2 + vy^2)
    # This will be used for the heatmap
    # -----------------------------------------------------
    magnitude = np.sqrt(vx**2 + vy**2)

    # -----------------------------------------------------
    # Create coordinate grids for plotting
    # X and Y match the mesh shape and give positions for arrows
    # For a width=W and height=H array:
    #   X has W columns replicated across rows
    #   Y has H rows replicated across columns
    # -----------------------------------------------------
    h, w = magnitude.shape
    X, Y = np.meshgrid(np.arange(w), np.arange(h))

    # -----------------------------------------------------
    # Create a figure and axis to draw on
    # figsize controls the window size in inches
    # -----------------------------------------------------
    fig, ax = plt.subplots(figsize=(15, 6))

    # -----------------------------------------------------
    # Draw the heatmap:
    #   • imshow plots the magnitude array as colors
    #   • cmap chooses the color palette ("turbo" = bright rainbow)
    #   • origin="upper" keeps (0,0) at the top-left, like image pixels
    # -----------------------------------------------------
    heatmap = ax.imshow(magnitude, cmap='turbo', origin='upper')

    # -----------------------------------------------------
    # Add a colorbar on the right side showing magnitude scale
    # -----------------------------------------------------
    plt.colorbar(heatmap, ax=ax, label="Vector Magnitude")

    # -----------------------------------------------------
    # Draw the direction vectors using quiver:
    #   • (X, Y) give arrow origins
    #   • (vx, vy) give direction + magnitude
    #   • color="white" draws arrows in white
    #   • scale controls arrow length (higher = shorter arrows)
    #   • width controls arrow thickness
    # -----------------------------------------------------
    # ax.quiver(
    #     X, Y,      # arrow start positions
    #     vx, vy,    # arrow directions
    #     color="white",
    #     scale=50,      # increasing this shrinks arrows
    #     width=0.003     # arrow thickness
    # )

    # -----------------------------------------------------
    # Add plot title and axis labels
    # -----------------------------------------------------
    ax.set_title(title)
    ax.set_xlabel("X (tile)")
    ax.set_ylabel("Y (tile)")

    # -----------------------------------------------------
    # Force equal scaling:
    # Without this, the grid might look stretched
    # -----------------------------------------------------
    ax.set_aspect("equal")

    # -----------------------------------------------------
    # Finally, display the figure on screen
    # -----------------------------------------------------
    plt.show()


if __name__ == "__main__":
    # Sample mesh: gradient in x, constant in y
    h, w = 20, 30
    mesh_example = np.zeros((h, w, 2))
    mesh_example[:, :, 0] = np.linspace(-10, 10, w)  # vx
    mesh_example[:, :, 1] = 3                        # vy constant

    visualise_mesh(mesh_example, title="Sample Mesh Field")
