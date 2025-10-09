from pygame import sprite, Vector2 as vec


class ObjectPool(sprite.Group):
    """A reusable object pool for mobile sprite management (e.g., missiles, enemies, map obstacles)."""

    refill_threshold = 3  # Number of objects below which we attempt refill

    def __init__(self, game, sprite_class, size):

        super().__init__()
        self.game = game
        self.sprite_class = sprite_class
        self.map_layer = sprite_class.map_layer
        self.refkey = sprite_class.refkey

        for _ in range(size):
            self.add_new_sprite()

    def borrow_object(self, new_x, new_y):
        """ On player shoot, assign missile to map grid for update and all_sprites grid for drawing"""
        self.refill_if_needed()

        # Create a new missile if pool is empty
        if not self:
            self.add_new_sprite()

        # Borrow one obj from pool
        for sprite_obj in self:
            self.activate_sprite(sprite_obj, new_x, new_y)
            self.remove(sprite_obj)  # remove from pool after adding to active map_layer
            return sprite_obj  # currently only missile sprites return in use

    def rtrn_object(self, sprite_obj):
        """ Return used missiles to pool"""
        self.add(sprite_obj)
        self.game.all_sprites.remove(sprite_obj)
        self.game.hold_sprites.remove(sprite_obj)
        self.game.map.layers[sprite_obj.map_layer][sprite_obj.gridref].remove(sprite_obj)
        # sprite_obj.pos = vec(0, 0)
        sprite_obj.change_action(self.game.mobile_sprite_images, self.refkey)

    def activate_sprite(self, sprite, x, y):
        """Prepare sprite for active use; reposition, add to map layer, drawing layer."""
        sprite.pos = vec(x, y)
        sprite.rect.center = sprite.pos
        sprite.hitrect.center = sprite.rect.center

        sprite.add_to_map_layer()
        self.game.all_sprites.add(sprite)

    def add_new_sprite(self):
        """Create and add a new sprite to the pool."""
        sprite = self.sprite_class(self.game, 0, 0)
        self.add(sprite)

    def refill_if_needed(self):
        """ If pool is empty or close too, retrieve inactive sprites from hold_sprites group, or create new sprite_objects last resort"""
        if len(self) < self.refill_threshold:
            # Reuse obj from hold_sprites if pool has fewer than 3
            for sprite_obj in self.game.hold_sprites:
                if isinstance(sprite_obj, self.sprite_class):
                    self.rtrn_object(sprite_obj)
                    self.game.hold_sprites.remove(sprite_obj)
                    break
        # Create a new missile if none in hold_sprites
        if not self:
            self.add_new_sprite()
        # print(f'Missile Pool:  {len(self)}')
        # print(f'Hold sprites:  {len(self.game.hold_sprites)}')
