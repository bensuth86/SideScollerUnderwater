# source code: https://stackoverflow.com/questions/45526988/does-anyone-have-an-example-of-using-sprite-sheets-in-tandem-with-xml-files

import xml.etree.ElementTree as ET
import pygame
from os import path
from pathlib import Path

from ..helpers.file_io import load_json

# Resolve paths relative to project root dir


class SpriteSheet:
    """ load an atlas image (spritesheet) pass an associated XML file to dictionary self.animation_frames"""
    def __init__(self, filename):

        image_path = self._load_image_path()
        imgfile = path.join(image_path, filename + ".png")
        self.spritesheet = pygame.image.load(imgfile).convert_alpha()  # convert_alpha maintains transparent pixels whereas convert() replaces them with black pixels
        self.xmlfile = path.join(image_path, filename + ".xml")

    def _load_image_path(self):

        config_dir = Path("config")
        game_config = load_json(config_dir / "game_config.json")
        base = Path(game_config["base"])
        image_path = base / game_config["rel_paths"]["images"]
        return image_path

    def get_image(self, x, y, width, height):

        image = pygame.Surface(([width, height]), pygame.SRCALPHA)  # Create a new blank image
        image.blit(self.spritesheet, (0, 0), (x, y, width, height))
        # image.set_colorkey(BLACK)  # set background to be transparent
        return image

    def get_sprite_images(self):
        """get images from spritesheet and cache image surf to dictionary - dictionary ordered by category, then nested subcat if applicable"""
        if self.xmlfile:
            tree = ET.parse(self.xmlfile)
            images = {}
            for node in tree.iter():
                    if node.attrib.get('SPRITECAT'):
                        spritecategory = node.attrib.get('SPRITECAT')
                        x = int(node.attrib.get('X'))
                        y = int(node.attrib.get('Y'))
                        width = int(node.attrib.get('WIDTH'))
                        height = int(node.attrib.get('HEIGHT'))
                        img = self.get_image(x, y, width, height)

                        if spritecategory not in images:
                            images[spritecategory] = []
                        images[spritecategory].append(img)
        return images
