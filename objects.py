FOCAL_LENGTH = 4.15
CAMERA_HEIGHT = 4608


class Object:
    distance = 0

    def __init__(self, img_height, real_height, desc):
        self.img_height = img_height
        self.real_height = real_height
        self.desc = desc

    def calculate_distance(self):
        self.distance = FOCAL_LENGTH * self.real_height * CAMERA_HEIGHT / self.img_height / 3.42

    def __str__(self):
        str1 = "Img_height:" + str(self.img_height) + " | Real_height: " + str(self.real_height) + " | Object: " + \
               str(self.desc) + " | Distance: " + str(self.distance) + "\n"
        return str1
