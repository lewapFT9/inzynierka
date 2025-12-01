import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from exceptions.exceptions import RateLimitException


def download_images_openverse(
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
    Pobiera obrazy z Openverse API.

    - Zachowuje oryginalny format obrazów.
    - Filtruje po formacie (allowed_formats).
    - Filtruje po rozdzielczości (resolution_filter).
    """
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    page = 1 + start_index // 20

    headers = {"Accept": "application/json"}

    while downloaded < count:
        params = {
            "q": query,
            "page_size": min(20, count - downloaded),
            "page": page,
        }

        response = requests.get(
            "https://api.openverse.engineering/v1/images",
            params=params,
            headers=headers,
        )

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
                if not img_url:
                    continue

                img_data = requests.get(img_url, timeout=10).content
                img = Image.open(BytesIO(img_data))

                # --- filtr formatu ---
                img_format = (img.format or "").lower()
                if allowed_formats is not None and img_format not in allowed_formats:
                    print(f"[Openverse] Pominięto – niedozwolony format: {img_format}")
                    continue

                # --- filtr rozdzielczości ---
                if resolution_filter:
                    w, h = img.size
                    min_w = resolution_filter.get("min_w")
                    min_h = resolution_filter.get("min_h")
                    max_w = resolution_filter.get("max_w")
                    max_h = resolution_filter.get("max_h")

                    if min_w is not None and w < min_w:
                        print(f"[Openverse] Za mała szerokość: {w} < {min_w}")
                        continue
                    if min_h is not None and h < min_h:
                        print(f"[Openverse] Za mała wysokość: {h} < {min_h}")
                        continue
                    if max_w is not None and w > max_w:
                        print(f"[Openverse] Za duża szerokość: {w} > {max_w}")
                        continue
                    if max_h is not None and h > max_h:
                        print(f"[Openverse] Za duża wysokość: {h} > {max_h}")
                        continue

                # --- minimalny rozmiar do crop ---
                if method == "crop" and min_size is not None:
                    min_w_crop, min_h_crop = min_size
                    if img.width < min_w_crop or img.height < min_h_crop:
                        print("[Openverse] Za małe – pominięte.")
                        continue

                if not is_valid_image(img):
                    continue

                ext = (img.format or "JPEG").lower()
                idx = start_index + downloaded + 1
                filename = os.path.join(save_dir, f"{idx}.{ext}")

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

        page += 1

    return downloaded
