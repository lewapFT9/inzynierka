import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from downloader.pexels_config import PEXELS_API_KEY
from exceptions.exceptions import RateLimitException


def download_images_pexels(query, count, save_dir, progress_callback=None, start_index=0):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    page = 1 + start_index // 15
    error_count = 0
    max_errors = 10  # limit błędów

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    print(f"[Pexels] Start pobierania ({count} obrazów) dla zapytania: '{query}'")

    while downloaded < count:
        params = {
            "query": query,
            "per_page": min(15, count - downloaded),
            "page": page
        }

        response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params)

        if response.status_code == 429:
            raise RateLimitException("Pexels API limit exceeded")
        elif response.status_code != 200:
            print(f"[Pexels] Błąd HTTP: {response.status_code}")
            print(f"[Pexels] Treść odpowiedzi: {response.text}")
            raise RateLimitException("Pexels API returned an error.")

        data = response.json()
        photos = data.get("photos", [])
        print(f"[Pexels] Otrzymano {len(photos)} wyników.")

        if not photos:
            break

        for item in photos:
            try:
                img_url = item["src"]["large"]
                print(f"[Pexels] Pobieram: {img_url}")
                img_data = requests.get(img_url, timeout=10).content
                img = Image.open(BytesIO(img_data))

                if is_valid_image(img):
                    filename = os.path.join(save_dir, f"{downloaded + 1 + start_index}.jpg")
                    img.convert("RGB").save(filename)
                    downloaded += 1
                    print(f"[Pexels] Zapisano: {filename}")
                    if progress_callback:
                        progress_callback(downloaded + start_index, count + start_index)
                else:
                    print("[Pexels] Odrzucony przez walidator.")

            except Exception as e:
                print(f"[Pexels] Błąd przy pobieraniu obrazu: {e}")
                error_count += 1
                if error_count >= max_errors:
                    print("[Pexels] Zbyt wiele błędów – przerywam.")
                    raise RateLimitException("Pexels: zbyt wiele błędów podczas pobierania.")
                continue

            if downloaded >= count:
                break

        page += 1

    print(f"[Pexels] Zakończono. Łącznie pobrano {downloaded}/{count} obrazów z Pexels.")
    return downloaded
