import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from downloader.unsplash_config import UNSPLASH_ACCESS_KEY
from exceptions.exceptions import RateLimitException

def download_images_unsplash(
    query, count, save_dir,
    progress_callback=None,
    start_index=0,
    method="resize",
    min_size=None,
    allowed_formats=None
):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    page = 1

    while downloaded < count:
        params = {
            "query": query,
            "client_id": UNSPLASH_ACCESS_KEY,
            "page": page,
            "per_page": min(10, count - downloaded)
        }

        response = requests.get("https://api.unsplash.com/search/photos",
                                params=params)
        if response.status_code == 403 and "Rate Limit Exceeded" in response.text:
            raise RateLimitException("Unsplash API limit exceeded")

        if response.status_code != 200:
            raise RateLimitException("Unsplash API returned an error")

        results = response.json().get("results", [])

        if not results:
            break

        for item in results:
            try:
                img_url = item["urls"]["regular"]
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
                        print("[Unsplash] Too small – skipped.")
                        continue

                if is_valid_image(img):
                    ext = (img.format or "jpg").lower()  # oryginalny typ z biblioteki Pillow
                    filename = os.path.join(save_dir, f"{start_index + downloaded + 1}.{ext}")
                    img.save(filename)
                    downloaded += 1
                    if progress_callback:
                        progress_callback(downloaded + start_index, count + start_index)
            except Exception:
                continue

            if downloaded >= count:
                break

        page += 1

    return downloaded
