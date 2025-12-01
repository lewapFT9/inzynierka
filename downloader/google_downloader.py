import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from downloader.google_config import API_KEY, CSE_ID
from exceptions.exceptions import RateLimitException


def download_images_google(
    query,
    count,
    save_dir,
    progress_callback=None,
    start_index=0,
    method="resize",
    min_size=None,
    allowed_formats=None,
    resolution_filter=None,
):
    """
    Pobiera obrazy z Google Custom Search API.

    - Zachowuje oryginalny format pliku (JPEG/PNG/GIF → .jpeg/.png/.gif).
    - Filtruje po dozwolonych formatach (allowed_formats).
    - Filtruje po rozdzielczości (resolution_filter: min_w, min_h, max_w, max_h).
    - Dba o to, by łączna liczba poprawnych obrazów = count.
    """
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    start = 1  # parametr "start" w Google CSE (1-indeksowany)

    while downloaded < count and start <= 91:
        num = min(10, count - downloaded)
        params = {
            "q": query,
            "cx": CSE_ID,
            "key": API_KEY,
            "searchType": "image",
            "start": start,
            "num": num,
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

                # --- filtr formatu wejściowego ---
                img_format = (img.format or "").lower()
                if allowed_formats is not None and img_format not in allowed_formats:
                    print(f"[Google] Pominięto – niedozwolony format: {img_format}")
                    continue

                # --- filtr rozdzielczości (WEJŚCIOWEJ) ---
                if resolution_filter:
                    w, h = img.size
                    min_w = resolution_filter.get("min_w")
                    min_h = resolution_filter.get("min_h")
                    max_w = resolution_filter.get("max_w")
                    max_h = resolution_filter.get("max_h")

                    if min_w is not None and w < min_w:
                        print(f"[Google] Za mała szerokość: {w} < {min_w}")
                        continue
                    if min_h is not None and h < min_h:
                        print(f"[Google] Za mała wysokość: {h} < {min_h}")
                        continue
                    if max_w is not None and w > max_w:
                        print(f"[Google] Za duża szerokość: {w} > {max_w}")
                        continue
                    if max_h is not None and h > max_h:
                        print(f"[Google] Za duża wysokość: {h} > {max_h}")
                        continue

                # --- minimalny rozmiar do crop ---
                if method == "crop" and min_size is not None:
                    min_w_crop, min_h_crop = min_size
                    if img.width < min_w_crop or img.height < min_h_crop:
                        print("[Google] Pominięto – za małe do crop.")
                        continue

                if not is_valid_image(img):
                    continue

                # --- zapis w oryginalnym formacie ---
                ext = (img.format or "JPEG").lower()
                idx = start_index + downloaded + 1
                filename = os.path.join(save_dir, f"{idx}.{ext}")

                # konwersja do RGB tylko jeśli JPEG / JPG
                if ext in ("jpg", "jpeg"):
                    img = img.convert("RGB")

                img.save(filename)

                downloaded += 1
                if progress_callback:
                    progress_callback(downloaded + start_index, count + start_index)

                if downloaded >= count:
                    break

            except Exception:
                continue

        start += 10
        if start > 91 and downloaded < count:
            raise RateLimitException("Google API pagination limit reached")

    return downloaded
