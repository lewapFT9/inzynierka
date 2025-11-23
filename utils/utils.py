import os
import re

def get_next_image_index(folder_path):
    max_index = 0
    for filename in os.listdir(folder_path):
        name, ext = os.path.splitext(filename)
        if ext.lower() in (".jpg", ".jpeg", ".png", ".gif") and name.isdigit():
            index = int(name)
            if index > max_index:
                max_index = index
    return max_index + 1
