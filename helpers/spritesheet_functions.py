# source code: https://stackoverflow.com/questions/45526988/does-anyone-have-an-example-of-using-sprite-sheets-in-tandem-with-xml-files

import xml.etree.ElementTree as ET
import pygame
from collections import defaultdict
from settings import *


class SpriteSheet:
    """ load an atlas image (spritesheet) pass an associated XML file to dictionary self.animation_frames"""
    def __init__(self, filename):

        imgfile = path.join(repos, 'spritesheets', filename + ".png")
        self.spritesheet = pygame.image.load(imgfile).convert_alpha()
        self.xmlfile = path.join(repos, 'spritesheets', filename + ".xml")

    def get_image(self, x, y, width, height):

        image = pygame.Surface([width, height]).convert()  # Create a new blank image
        image.blit(self.spritesheet, (0, 0), (x, y, width, height))

        image.set_colorkey(BLACK)  # set background to be transparent
        return image

    def get_sprite_images(self, spritedata):

        if self.xmlfile:
            tree = ET.parse(self.xmlfile)
            images = {}
            for node in tree.iter():
                for cat in list(spritedata.keys()):
                    if node.attrib.get('SPRITECATEGORY') == cat:
                        spritecategory = node.attrib.get('SPRITECATEGORY')
                        x = int(node.attrib.get('X'))
                        y = int(node.attrib.get('Y'))
                        width = int(node.attrib.get('WIDTH'))
                        height = int(node.attrib.get('HEIGHT'))
                        img = self.get_image(x, y, width, height)
                        new_width = spritedata[cat]['width'] * TILESIZE
                        new_height = spritedata[cat]['height'] * TILESIZE
                        img = pygame.transform.scale(img, (new_width, new_height))  # resize image

                        if node.attrib.get('SUBCAT'):
                            subcat = node.attrib.get('SUBCAT')
                            if spritecategory not in images:
                                images[spritecategory] = {}
                            if subcat not in images[spritecategory]:
                                images[spritecategory][subcat] = []
                            images[spritecategory][subcat].append(img)
                        else:
                            if spritecategory not in images:
                                images[spritecategory] = []
                            images[spritecategory].append(img)
        return images



    # def get_sprite_images(self, spritedata):
    #
    #     if self.xmlfile:
    #         tree = ET.parse(self.xmlfile)
    #         images = {}
    #         for node in tree.iter():
    #             for cat in list(spritedata.keys()):
    #                 if node.attrib.get('SPRITECATEGORY') == cat:
    #                     spritecategory = node.attrib.get('SPRITECATEGORY')
    #                     if spritecategory not in images:
    #                         images[spritecategory] = {}
    #                     if node.attrib.get('SUBCAT'):
    #                         subcat = node.attrib.get('SUBCAT')
    #                         if subcat not in images[spritecategory]:
    #                             images[spritecategory][subcat] = []
    #
    #                         x = int(node.attrib.get('X'))
    #                         y = int(node.attrib.get('Y'))
    #                         width = int(node.attrib.get('WIDTH'))
    #                         height = int(node.attrib.get('HEIGHT'))
    #                         img = self.get_image(x, y, width, height)
    #                         new_width = spritedata[cat]['width']
    #                         new_height = spritedata[cat]['height']
    #                         img = pygame.transform.scale(img, (new_width, new_height))  # resize image
    #                         images[spritecategory][subcat].append(img)
    #
    #     return images
    # def animated(self, new_width, new_height):
    #
    #     if self.xmlfile:
    #         tree = ET.parse(self.xmlfile)
    #         frames = {}
    #         for node in tree.iter():
    #             if node.attrib.get('SPRITEACTION'):
    #                 spriteaction = node.attrib.get('SPRITEACTION')
    #                 if spriteaction not in frames:
    #                     frames[spriteaction] = {}
    #                 if node.attrib.get('DIRECTION'):
    #                     direction = node.attrib.get('DIRECTION')
    #                     if direction not in frames[spriteaction]:
    #                         frames[spriteaction][direction] = []
    #                     if node.attrib.get('SPRSHEETPOS'):
    #                         # pos = (node.attrib.get('SPRSHEETPOS'))
    #                         x = int(node.attrib.get('X'))
    #                         y = int(node.attrib.get('Y'))
    #                         width = int(node.attrib.get('WIDTH'))
    #                         height = int(node.attrib.get('HEIGHT'))
    #                         img = self.get_image(x, y, width, height)
    #                         # img = pygame.transform.scale(img, (new_width, new_height))  # resize image
    #                         frames[spriteaction][direction].append(img)
    #                         # self.frames[spriteaction][direction].append(pos)
    #     return frames

