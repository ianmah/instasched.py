from PIL import Image
import math
import io
from io import BytesIO
import requests

class Img:
    __image = ''

    def __init__(self, img):
        if img[:4] == 'http':
            imgGet = requests.get(img)
            self.__image = Image.open(BytesIO(imgGet.content))
        else:
            self.__image = Image.open(img)
        self.__image.load()

    def crop(self):
        height = self.__image.height
        width = self.__image.width

        mod_ratio = height/width-1.25

        if mod_ratio > 0:
            newheight = height-math.floor(height*mod_ratio)

            hmid = height/2

            bottom = hmid+newheight/2
            top = hmid-newheight/2

            area = (0, top, width, bottom)
            self.__image = self.__image.crop(area)

    def resize(self):
        height = self.__image.height
        width = self.__image.width

        if height > 1080:
            self.__image.thumbnail((1080, 1080), Image.ANTIALIAS)


    def getImg(self):
        self.crop()
        self.resize()
        return self.__image

    def size(self):
        return self.__image.size

    def getByteArr(self):
        imgByteArr = io.BytesIO()
        self.__image.save(imgByteArr, format='JPEG')
        return imgByteArr.getvalue()
