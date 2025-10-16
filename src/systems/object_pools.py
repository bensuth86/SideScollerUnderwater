from pygame import sprite, Vector2 as vec


class ObjectPool(sprite.Group):
    """A reusable object pool for mobile sprite management (e.g., missiles, enemies, map obstacles)."""

    refill_threshold = 3  # Number of objects below which we attempt refill

    def __init__(self, game, sprite_class, refill_threshold=3, max_size=None):
        """
        Create an object pool.

        :param game: The main game object with access to sprite groups and layers.
        :param sprite_class: The class of sprite to instantiate and manage.
        :param refill_threshold: The minimum size before triggering refill.
        :param max_size: Optional cap on total pool size (including active + held).
        """

        super().__init__()
        self.game = game
        self.sprite_class = sprite_class
        self.refill_threshold = refill_threshold
        self.max_size = max_size

        # self.map_layer = sprite_class.map_layer
        self.refkey = sprite_class.refkey

    def populate(self, count):

        for _ in range(count):
            self.add_new_sprite()

    def borrow_object(self, new_x, new_y):
        """
        Borrow an object from the pool.
        Repositions and activates the object on the map.
        """
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
        """ Return a used object to pool and reset its state """
        self.add(sprite_obj)

        # remove from active layers
        self.game.all_sprites.remove(sprite_obj)
        self.game.hold_sprites.remove(sprite_obj)
        self.game.map.layers[sprite_obj.map_layer][sprite_obj.gridref].remove(sprite_obj)

        # Reset sprite's action/state
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
        if self.max_size is None or len(self) < self.max_size:
            sprite = self.sprite_class(self.game, 0, 0)
            self.add(sprite)

    def refill_if_needed(self):
        """ If pool is empty or close too, retrieve inactive sprites from hold_sprites group, or create new sprite_objects last resort"""
        if len(self) < self.refill_threshold:
            # Try to retrieve object from hold_sprites
            for sprite_obj in list(self.game.hold_sprites):
                if isinstance(sprite_obj, self.sprite_class):
                    self.rtrn_object(sprite_obj)
                    self.game.hold_sprites.remove(sprite_obj)
                    break
        # If still beloew refill_threshold, create a new sprite
        if not self:
            self.add_new_sprite()
        # print(f'Missile Pool:  {len(self)}')
        # print(f'Hold sprites:  {len(self.game.hold_sprites)}')

    def current_size(self):
        """Return the number of available objects in the pool."""
        return len(self)

    def clear_pool(self):
        """Completely empty the pool."""
        self.empty()
