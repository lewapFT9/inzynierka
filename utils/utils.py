import os
import re


def get_next_image_index(folder_path):
    max_index = 0
    for filename in os.listdir(folder_path):
        match = re.match(r"(\d+)\.jpg$", filename)
        if match:
            index = int(match.group(1))
            if index > max_index:
                max_index = index
    return max_index + 1