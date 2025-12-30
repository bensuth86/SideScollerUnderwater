# https://stackoverflow.com/questions/45526988/does-anyone-have-an-example-of-using-sprite-sheets-in-tandem-with-xml-files

import xml.etree.ElementTree as ET
import pygame
from pathlib import Path

from ..helpers.file_io import load_json

# Resolve paths relative to project root dir


class SpriteSheet:
    """ load an atlas image (spritesheet) pass an associated XML file to dictionary self.animation_frames"""
    def __init__(self, filename):

        self.image_path = self._load_image_path()

        # Resolve image file (.png)
        self.imgfile = self._find_file(self.image_path, filename, ["png"])
        self.spritesheet = pygame.image.load(str(self.imgfile)).convert_alpha()

        # Resolve XML file (.xml or .XML etc.)
        self.xmlfile = self._find_file(self.image_path, filename, ["xml"])

    def _load_image_path(self):

        config_dir = Path("config")
        game_config = load_json(config_dir / "game_config.json")
        base = Path(game_config["base"])
        image_path = base / game_config["rel_paths"]["images"]
        if not image_path.is_dir():
            raise FileNotFoundError(f"Image directory not found: {image_path}")

        return image_path

    def _find_file(self, directory: Path, stem: str, extensions):
        """
        Find a file ignoring extension case (.xml vs .XML).
        """
        for ext in extensions:
            matches = list(directory.glob(f"{stem}.[{ext[0]}{ext[0].upper()}]"
                                           f"[{ext[1]}{ext[1].upper()}]"
                                           f"[{ext[2]}{ext[2].upper()}]"))
            if matches:
                return matches[0]

    def get_image(self, x, y, width, height):

        image = pygame.Surface(([width, height]), pygame.SRCALPHA)  # Create a new blank image
        image.blit(self.spritesheet, (0, 0), (x, y, width, height))
        # image.set_colorkey(BLACK)  # set background to be transparent
        return image

    def get_sprite_images(self):
        """
        Extract and cache sprite images from the XML file.
        Returns a dict keyed by SPRITECAT.
        """
        images = {}

        tree = ET.parse(str(self.xmlfile))
        for node in tree.iter():
            spritecategory = node.attrib.get("SPRITECAT")
            if not spritecategory:
                continue

            x = int(node.attrib["X"])
            y = int(node.attrib["Y"])
            width = int(node.attrib["WIDTH"])
            height = int(node.attrib["HEIGHT"])

            img = self.get_image(x, y, width, height)
            images.setdefault(spritecategory, []).append(img)

        return images