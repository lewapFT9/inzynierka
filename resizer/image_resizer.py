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

def _ext_to_save_fmt_from_path(path: str) -> str | None:
    """
    Mapuje rozszerzenie pliku na format Pillow:
    .jpg/.jpeg -> "JPEG"
    .png       -> "PNG"
    .gif       -> "GIF"
    Inne → None (pominiemy plik).
    """
    ext = os.path.splitext(path)[1].lower()  # np. ".jpg"
    if ext in (".jpg", ".jpeg"):
        return "JPEG"
    if ext == ".png":
        return "PNG"
    if ext == ".gif":
        return "GIF"
    return None

def apply_resize_to_folder2(root_folder, size, method="resize"):
    """
    Rekurencyjnie przechodzi po `root_folder` i wszystkich podfolderach
    i zmienia rozdzielczość wszystkich plików graficznych
    (.jpg, .jpeg, .png, .gif).
    """
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for filename in filenames:
            if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                continue

            path = os.path.join(dirpath, filename)
            try:
                with Image.open(path) as img:
                    if method == "resize":
                        img = resize_image(img, size)
                    elif method == "crop":
                        img = center_crop(img, size)

                    save_fmt = _ext_to_save_fmt_from_path(path)
                    if save_fmt is None:
                        # na wszelki wypadek pomijamy nieobsługiwane rozszerzenia
                        print(f"Pominięto plik o nieobsługiwanym rozszerzeniu: {path}")
                        continue

                    # JPG/JPEG → wymuś RGB
                    if save_fmt == "JPEG":
                        img = img.convert("RGB")

                    img.save(path, format=save_fmt)

            except Exception as e:
                print(f"Błąd skalowania obrazu {path}: {e}")
