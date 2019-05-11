FOCAL_LENGTH = 4.15
CAMERA_HEIGHT = 4608


class Object:
    distance = 0

    def __init__(self, img_height, real_height, desc, position):
        self.img_height = img_height
        self.real_height = real_height
        self.desc = desc
        self.position = position

    def calculate_distance(self):
        self.distance = FOCAL_LENGTH * self.real_height * CAMERA_HEIGHT / self.img_height / 3.42

    def __str__(self):
        str1 = "Img_height:" + str(self.img_height) + " | Real_height: " + str(self.real_height) + " | Object: " + \
               str(self.desc) + " | Distance: " + str(self.distance) + "\n"
        return str1

    def __dict__(self):
        # str1 = "Img_height:" + str(self.img_height) + " | Real_height: " + str(self.real_height) + " | Object: " + \
        #       str(self.desc) + " | Distance: " + str(self.distance) + "\n"
        d = {'img_height': self.img_height,
                'real_height': self.real_height,
                'desc': self.desc,
                'distance': self.distance}
        return d
