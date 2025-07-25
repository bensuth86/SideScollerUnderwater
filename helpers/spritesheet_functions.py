# source code: https://stackoverflow.com/questions/45526988/does-anyone-have-an-example-of-using-sprite-sheets-in-tandem-with-xml-files

import xml.etree.ElementTree as ET
import pygame
from collections import defaultdict
from settings import *


class SpriteSheet:
    """ load an atlas image (spritesheet) pass an associated XML file to dictionary self.animation_frames"""
    def __init__(self, filename):

        imgfile = path.join(repos, 'Images', filename + ".png")
        self.spritesheet = pygame.image.load(imgfile).convert_alpha()  # convert_alpha maintains transparent pixels whereas convert() replaces them with black pixels
        self.xmlfile = path.join(repos, 'Images', filename + ".xml")

    def get_image(self, x, y, width, height):

        image = pygame.Surface(([width, height]), pygame.SRCALPHA)  # Create a new blank image
        image.blit(self.spritesheet, (0, 0), (x, y, width, height))
        # image.set_colorkey(BLACK)  # set background to be transparent
        return image

    def get_sprite_images(self):

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
