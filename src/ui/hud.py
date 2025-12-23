from pygame import Rect, draw, font
from ..settings import WHITE, GREEN, BLUE, RED, SCREENWIDTH


def draw_sprite_bar(surf, x, y, pct, c1, c2, c3):
    pct = max(0, pct)
    bar_length, bar_height = 100, 20
    # bar_height = 20
    fill = pct * bar_length
    outline_rect = Rect(x, y, bar_length, bar_height)
    fill_rect = Rect(x, y, fill, bar_height)
    if pct > 0.6:
        col = c1
    elif pct > 0.3:
        col = c2
    else:
        col = c3
    draw.rect(surf, col, fill_rect)
    draw.rect(surf, WHITE, outline_rect, 2)


def ammo_display():
    pass


def score():
    pass


def notications():
    pass


def quest_prompts():
    pass


def draw_text(game, text, size, colour, x, y):

    fnt = font.Font('freesansbold.ttf', size)  # text font
    text_surface = fnt.render(text, True, colour)
    # text_surface.convert()
    text_rect = text_surface.get_rect()
    text_rect.center = (x, y)
    game.screen.blit(text_surface, text_rect)


def draw_grid(game):  # (rows,columns)
    """ Display grid squares TESTING ONLY"""
    fnt = font.Font('freesansbold.ttf', 16)

    for grid in game.map.layers['empty'].values():
        x1 = grid.x1
        y1 = grid.y1
        x1 = x1 - game.camera.pos.x  # update with camera movement
        y1 = y1 - game.camera.pos.y
        draw.rect(game.screen, WHITE, [x1, y1, game.map.gridwidth, game.map.gridheight], 1)
        text = fnt.render(grid.coordinates, True, GREEN, BLUE)
        textRect = text.get_rect()
        textRect.topleft = (x1, y1)
        game.screen.blit(text, textRect)


def draw_ray(game):

    start = game.player.pos
    line_vec = game.player.aim_direction.normalize() * SCREENWIDTH
    end = start + line_vec
    draw.line(game.screen, RED, start - game.camera.pos, (end - game.camera.pos), 1)