from src.settings import *
import logging

logger = logging.getLogger(__name__)

# --- CAMERA ---


def camera_lerp(lerp_factor):

    if not (0 < lerp_factor <= 1):
        logger.warning(f"[CAMERA] lerp_factor abnormal ({lerp_factor}) — expected 0 < f ≤ 1")


def detectNan_infinite_drift(pos, old_pos):
    # Detect NaN / infinite drift
    if not (pos.x == pos.x and pos.y == pos.y):  # NaN check
        logger.warning(f"[CAMERA] NaN position detected after update: {pos}")
        pos.update(0, 0)

    if abs(pos.x - old_pos.x) > SCREENWIDTH:
        logger.warning("[CAMERA] Excessive camera jump on X axis — target teleported?")
    if abs(pos.y - old_pos.y) > SCREENHEIGHT:
        logger.warning("[CAMERA] Excessive camera jump on Y axis — target teleported?")

# --- PERFORMANCE ---

def performance_FPS_monitoring(FPS):
    """ Raise warning if FPS below thresholds, adaptive rendering triggered"""
    if FPS < 20:
        print(FPS)
        logger.warning(f"[PERF] Critical low FPS: {FPS:.1f}")
    elif FPS < 30:
        print(FPS)
        logger.warning(f"[PERF] Low FPS: {FPS:.1f} — adaptive rendering triggered.")


# --- IMAGES ---

def check_sprite_size(images, tilesize):
    """ Check sprite images are a multiple of half a tilesize"""

    for name, img_list in images.items():
        for img in img_list:
            width = img.get_width()
            height = img.get_height()
            # if img.get_width() < tilesize // 2:
            if width % (tilesize // 2) != 0:
                logger.warning(f"[IMAGES] '{name}' width doesn't fit tile size.")
            elif height % (tilesize // 2) != 0:
                logger.warning(f"[IMAGES] '{name}' height doesn't fit tile size.")


# --- SPRITES ---

def check_valid_grid(gridref, sprite, grid_coords):
    """ Check grid sprite reassigned exist within map confines"""
    if gridref not in grid_coords:
        logger.warning(f"[GRID] For sprite {sprite} gridref {gridref} does not exist")


def check_extreme_vel(sprite):
    """ Return warning if sprite vel exceeds threshold collision detection can't handle"""
    if sprite.vel.length() > 300:
        logger.warning(f"[PHYSICS] Extreme velocity on {sprite}: {sprite.vel}")


def left_map_bounds(sprite, game_map):
    """ Warning if sprite somehow leaves map boundaries"""

    if not 0 < sprite.pos.x < game_map.width:
        logger.warning(f"[WORLD] {sprite} out of map bounds at {sprite.pos.x}.")
    elif not 0 < sprite.pos.y < game_map.height:
        logger.warning(f"[WORLD] {sprite} out of map bounds at {sprite.pos.y}.")


def check_hitrect_position(sprite):
    if sprite.hitrect.center != sprite.pos + (sprite.direction * sprite.HRoffset):
        logger.warning(f"[WARNING] sprite {sprite} and hitrect out of sync")


# --- Object pooling --- ~

def check_sprite_groups(sprite_obj, pool):

    """
    Ensure the sprite belongs ONLY to the object pool group.
    No other membership checks — just inspect sprite_obj.groups().
    """

    groups = sprite_obj.groups()

    # Must be exactly one group (the pool)
    if len(groups) != 1:
        logger.warning(
            f"[POOL CHECK] Sprite {sprite_obj.ID} belongs to {len(groups)} groups: "
            f"{groups}. Expected ONLY the pool."
        )

    # Must specifically be THIS pool
    if pool not in groups:
        logger.warning(
            f"[POOL CHECK] Sprite {sprite_obj.ID} is NOT in its pool group."
        )

