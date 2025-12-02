from PIL import Image
import os


def normalize_save_format(ext: str):
    """
    Zamienia rozszerzenie na prawidłowy format PIL do zapisu.
    """
    ext = ext.replace(".", "").lower()

    if ext in ("jpg", "jpeg"):
        return "JPEG"
    if ext == "png":
        return "PNG"
    if ext == "gif":
        return "GIF"

    # fallback – PIL sobie poradzi
    return ext.upper()


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
        if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
            path = os.path.join(folder, filename)
            try:
                img = Image.open(path)

                # transformacja
                if method == 'resize':
                    img = resize_image(img, size)
                elif method == 'crop':
                    img = center_crop(img, size)

                # normalizacja formatu do PIL
                ext = os.path.splitext(filename)[1]  # np .jpg
                save_fmt = normalize_save_format(ext)

                # JPG musi być RGB
                if save_fmt == "JPEG":
                    img = img.convert("RGB")

                img.save(path, format=save_fmt)

            except Exception as e:
                print(f" Błąd skalowania obrazu {filename}: {e}")
