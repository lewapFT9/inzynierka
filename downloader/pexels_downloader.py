import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from downloader.pexels_config import PEXELS_API_KEY
from exceptions.exceptions import RateLimitException

def download_images_pexels(
    query, count, save_dir,
    progress_callback=None,
    start_index=0,
    method="resize",
    min_size=None,
    allowed_formats=None
):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    page = 1 + start_index // 15
    error_count = 0
    max_errors = 10

    headers = {"Authorization": PEXELS_API_KEY}

    while downloaded < count:
        params = {
            "query": query,
            "per_page": min(15, count - downloaded),
            "page": page
        }

        response = requests.get("https://api.pexels.com/v1/search",
                                headers=headers, params=params)

        if response.status_code == 429:
            raise RateLimitException("Pexels API limit exceeded")

        if response.status_code != 200:
            raise RateLimitException("Pexels API returned an error.")

        photos = response.json().get("photos", [])

        if not photos:
            break

        for item in photos:
            try:
                img_url = item["src"]["large"]
                img_data = requests.get(img_url, timeout=10).content
                img = Image.open(BytesIO(img_data))

                # sprawdzenie formatu wejściowego
                img_format = (img.format or "").lower()
                if allowed_formats and img_format not in allowed_formats:
                    print(f"[Google] Pominięto – niedozwolony format: {img_format}")
                    continue
                # size check
                if method == "crop" and min_size is not None:
                    min_w, min_h = min_size
                    if img.width < min_w or img.height < min_h:
                        print("[Pexels] Pominięto – za małe.")
                        continue

                if is_valid_image(img):
                    ext = (img.format or "jpg").lower()  # oryginalny typ z biblioteki Pillow
                    filename = os.path.join(save_dir, f"{start_index + downloaded + 1}.{ext}")
                    img.save(filename)
                    downloaded += 1
                    if progress_callback:
                        progress_callback(downloaded + start_index, count + start_index)
            except Exception:
                error_count += 1
                if error_count >= max_errors:
                    raise RateLimitException("Pexels: Too many errors")
                continue

            if downloaded >= count:
                break

        page += 1

    return downloaded
