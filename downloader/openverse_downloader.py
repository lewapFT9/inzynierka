import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from exceptions.exceptions import RateLimitException

def download_images_openverse(
    query, count, save_dir,
    progress_callback=None,
    start_index=0,
    method="resize",
    min_size=None,
    allowed_formats=None
):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    page = 1 + start_index // 20

    headers = {"Accept": "application/json"}

    while downloaded < count:
        params = {
            "q": query,
            "page_size": min(20, count - downloaded),
            "page": page
        }

        response = requests.get("https://api.openverse.engineering/v1/images",
                                params=params, headers=headers)

        if response.status_code == 429:
            raise RateLimitException("Openverse API limit exceeded")

        if response.status_code != 200:
            raise RateLimitException("Openverse API returned an error.")

        data = response.json()
        results = data.get("results", [])

        if not results:
            break

        for item in results:
            try:
                img_url = item.get("url")
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
                        print("[Openverse] Za małe – pominięte.")
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
