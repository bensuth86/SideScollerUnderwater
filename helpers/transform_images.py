from pygame import transform


def resize_images(frame, newsize, ):  # (width, height)

    def apply(image):
        image = transform.scale(image, newsize)
        return image

    newframe = map(apply, frame)
    newframe = list(newframe)
    return list(newframe)


def flip_images(frame, flip):  # (list of images, (bool x, bool y))

    def apply(image):
        image = transform.flip(image, flip[0], flip[1])
        return image

    newframe = map(apply, frame)
    newframe = list(newframe)
    return list(newframe)


def rotate_images(frame, rotation):  # angle

    def apply(image):
        image = transform.rotate(image, rotation)
        return image

    newframe = map(apply, frame)
    newframe = list(newframe)
    return list(newframe)
