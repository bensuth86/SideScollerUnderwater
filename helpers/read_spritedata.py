def readSpriteData(filename):

    sprites = {}

    with open(filename, 'r') as f:
        headings = f.readline().strip('\n').split('|')  # read first line of file
        for line in f:
            listDetails = line.strip('\n').split('|')
            sprites[listDetails[0]] = {headings[1]: int(listDetails[1])}
            sprites[listDetails[0]].update({headings[2]: int(listDetails[2])})

    return sprites