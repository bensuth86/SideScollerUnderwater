from pygame import transform
from .spritesheet_functions import *


def resize_images(frame, newsize):  # (width, height)

    def apply(image):
        image = transform.scale(image, newsize)
        return image

    newframe = map(apply, frame)
    newframe = list(newframe)
    return list(newframe)


def load_spritesheets(*args):

    images = {}
    for filename in args:
        sprsheet = SpriteSheet(filename)
        image_dict = sprsheet.get_sprite_images()  # single nested dictionary for each spritesheet
        images.update(image_dict)

    return images

