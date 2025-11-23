import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from downloader.google_config import API_KEY, CSE_ID
from exceptions.exceptions import RateLimitException

def download_images_google(
    query, count, save_dir,
    progress_callback=None,
    start_index=0,
    method="resize",
    min_size=None,
    allowed_formats=None
):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    start = 1

    while downloaded < count and start <= 91:
        num = min(10, count - downloaded)
        params = {
            "q": query,
            "cx": CSE_ID,
            "key": API_KEY,
            "searchType": "image",
            "start": start,
            "num": num
        }

        response = requests.get("https://www.googleapis.com/customsearch/v1", params=params)

        if response.status_code == 429:
            raise RateLimitException("Google API limit exceeded.")

        try:
            response.raise_for_status()
            data = response.json()

            if "error" in data and "quota" in data["error"].get("message", "").lower():
                raise RateLimitException("Google API quota exceeded.")

        except requests.exceptions.HTTPError:
            raise RateLimitException("Google API HTTPError")

        if "items" not in data:
            raise RateLimitException("Google API returned no items")

        for item in data["items"]:
            try:
                img_url = item["link"]
                img_data = requests.get(img_url, timeout=10).content
                img = Image.open(BytesIO(img_data))

                # sprawdzenie formatu wejściowego
                img_format = (img.format or "").lower()
                if allowed_formats and img_format not in allowed_formats:
                    print(f"[Google] Pominięto – niedozwolony format: {img_format}")
                    continue
                # --- MINIMAL SIZE CHECK FOR CROP ---
                if method == "crop" and min_size is not None:
                    min_w, min_h = min_size
                    if img.width < min_w or img.height < min_h:
                        print("[Google] Pominięto – za małe do crop.")
                        continue

                if is_valid_image(img):
                    ext = (img.format or "jpg").lower()  # oryginalny typ z biblioteki Pillow
                    filename = os.path.join(save_dir, f"{start_index + downloaded + 1}.{ext}")
                    img.save(filename)
                    downloaded += 1
                    if progress_callback:
                        progress_callback(downloaded + start_index, count + start_index)

                if downloaded >= count:
                    break
            except Exception:
                continue

        start += 10
        if start > 91:
            raise RateLimitException("Google API pagination limit reached")

    return downloaded
