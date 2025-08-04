from PIL import Image
import os

def resize_image(image, size):
    return image.resize(size, Image.Resampling.LANCZOS)


def center_crop(image, size):
    width, height = image.size
    new_width, new_height = size
    left = (width - new_width) // 2
    top = (height - new_height) // 2
    right = left + new_width
    bottom = top + new_height
    return image.crop((left, top, right, bottom))

def apply_resize_to_folder(folder, size, method='resize'):
    for filename in os.listdir(folder):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            path = os.path.join(folder, filename)
            try:
                img = Image.open(path)
                if method == 'resize':
                    img = resize_image(img, size)
                elif method == 'crop':
                    img = center_crop(img, size)
                img.save(path)
            except Exception as e:
                print(f" Błąd skalowania obrazu {filename}: {e}")
