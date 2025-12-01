import requests
import os
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
    allowed_formats=None,
    resolution_filter=None
):

    print("[PEXELS] START",
          "query=", query,
          "count=", count,
          "start_index=", start_index,
          "allowed_formats=", allowed_formats,
          "resolution_filter=", resolution_filter)

    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    page = 1 + start_index // 15

    headers = {"Authorization": PEXELS_API_KEY}

    while downloaded < count:
        params = {
            "query": query,
            "per_page": min(15, count - downloaded),
            "page": page
        }

        response = requests.get("https://api.pexels.com/v1/search",
                                headers=headers, params=params, timeout=10)

        if response.status_code == 429:
            raise RateLimitException("Pexels API limit exceeded")

        if response.status_code != 200:
            raise RateLimitException("Pexels API returned an error.")

        photos = response.json().get("photos", [])
        if not photos:
            print("[PEXELS] Brak kolejnych zdjęć.")
            break

        for item in photos:
            try:
                # używamy oryginalnego zdjęcia -> lepsza jakość i brak parametrów w URL
                img_url = item["src"]["original"]
                print("[PEXELS] Fetching:", img_url)

                # --- pobieranie z limitem rozmiaru ---
                resp = requests.get(img_url, timeout=8, stream=True)
                resp.raise_for_status()

                MAX_BYTES = 12 * 1024 * 1024   # 12 MB limit
                img_data = resp.raw.read(MAX_BYTES)

                if not img_data:
                    print("[PEXELS] Empty image data, skipping.")
                    continue

                print("[PEXELS] GOT:", len(img_data), "bytes")

                # --- wczytanie obrazu ---
                img = Image.open(BytesIO(img_data))
                img.load()

                # poprawne rozpoznanie formatu
                ext = (img.format or "JPEG").lower()
                if ext == "jpeg":
                    ext = "jpg"

                # --- filtr formatu ---
                if allowed_formats is not None:
                    if ext not in allowed_formats:
                        print(f"[Pexels] Pominięto – niedozwolony format: {ext}")
                        continue

                # --- filtr rozdzielczości ---
                if resolution_filter:
                    w, h = img.size
                    min_w = resolution_filter.get("min_w")
                    min_h = resolution_filter.get("min_h")
                    max_w = resolution_filter.get("max_w")
                    max_h = resolution_filter.get("max_h")

                    if min_w and w < min_w:
                        print("[PEXELS] Too small W:", w)
                        continue
                    if min_h and h < min_h:
                        print("[PEXELS] Too small H:", h)
                        continue
                    if max_w and w > max_w:
                        print("[PEXELS] Too large W:", w)
                        continue
                    if max_h and h > max_h:
                        print("[PEXELS] Too large H:", h)
                        continue

                # --- filtr crop (min size) ---
                if method == "crop" and min_size:
                    mw, mh = min_size
                    if img.width < mw or img.height < mh:
                        print("[PEXELS] Too small for crop")
                        continue

                if not is_valid_image(img):
                    print("[PEXELS] Invalid image skipped.")
                    continue

                filename = os.path.join(
                    save_dir,
                    f"{start_index + downloaded + 1}.{ext}"
                )

                if ext in ("jpg", "jpeg"):
                    img = img.convert("RGB")

                img.save(filename)
                print("[PEXELS] Saved:", filename)

                downloaded += 1

                if progress_callback:
                    progress_callback(downloaded + start_index, count + start_index)

            except Exception as e:
                print("[Pexels] Error:", e)
                continue

            if downloaded >= count:
                break

        page += 1

    return downloaded
