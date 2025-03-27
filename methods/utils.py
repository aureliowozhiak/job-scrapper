import os

class Utils:
    def __init__(self):
        pass

    def createDir(self, directory):
        if not os.path.exists(directory):
            os.mkdir(directory)

    def listDir(self, directory):
        return os.listdir(directory)

    def loadFile(self, file_name_path):
        with open(file_name_path, "r") as f:
            return f.read()