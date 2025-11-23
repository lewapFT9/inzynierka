import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from downloader.pixabay_config import PIXABAY_API_KEY
from exceptions.exceptions import RateLimitException

def download_images_pixabay(
    query, count, save_dir,
    progress_callback=None,
    start_index=0,
    method="resize",
    min_size=None,
    output_format="jpg"
):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    page = 1

    while downloaded < count:
        params = {
            "key": PIXABAY_API_KEY,
            "q": query,
            "image_type": "photo",
            "per_page": min(20, count - downloaded),
            "page": page
        }

        response = requests.get("https://pixabay.com/api/", params=params)

        if response.status_code == 429:
            raise RateLimitException("Pixabay API limit exceeded")

        if response.status_code != 200:
            raise RateLimitException("Pixabay API returned an error.")

        hits = response.json().get("hits", [])

        if not hits:
            break

        for item in hits:
            try:
                img_url = item["largeImageURL"]
                img_data = requests.get(img_url, timeout=10).content
                img = Image.open(BytesIO(img_data))

                # size check
                if method == "crop" and min_size is not None:
                    min_w, min_h = min_size
                    if img.width < min_w or img.height < min_h:
                        print("[Pixabay] Too small – skipped.")
                        continue

                if is_valid_image(img):
                    filename = os.path.join(save_dir, f"{start_index + downloaded + 1}.{output_format}")
                    img = img.convert("RGB") if output_format in ["jpg", "jpeg"] else img  # JPG musi być RGB
                    img.save(filename, format=output_format.upper())
                    downloaded += 1
                    if progress_callback:
                        progress_callback(downloaded + start_index, count + start_index)
            except Exception:
                continue

            if downloaded >= count:
                break

        page += 1

    return downloaded
