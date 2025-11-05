import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from downloader.pixabay_config import PIXABAY_API_KEY
from exceptions.exceptions import RateLimitException


def download_images_pixabay(query, count, save_dir, progress_callback=None, start_index=0):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    page = 1

    print(f"[Pixabay] Start pobierania ({count} obrazów) dla zapytania: '{query}'")

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
        elif response.status_code != 200:
            print(f"[Pixabay] Błąd HTTP: {response.status_code}")
            print(f"[Pixabay] Treść odpowiedzi: {response.text}")
            break

        data = response.json()
        hits = data.get("hits", [])
        print(f"[Pixabay] Otrzymano {len(hits)} wyników.")

        if not hits:
            break

        for item in hits:
            try:
                img_url = item["largeImageURL"]
                print(f"[Pixabay] Pobieram: {img_url}")
                img_data = requests.get(img_url, timeout=10).content
                img = Image.open(BytesIO(img_data))

                if is_valid_image(img):
                    filename = os.path.join(save_dir, f"{downloaded + 1 + start_index}.jpg")
                    img.convert("RGB").save(filename)
                    downloaded += 1
                    print(f"[Pixabay] Zapisano: {filename}")
                    if progress_callback:
                        progress_callback(downloaded + start_index, count + start_index)
                else:
                    print("[Pixabay] Odrzucony przez walidator.")
            except Exception as e:
                print(f"[Pixabay] Błąd przy pobieraniu obrazu: {e}")
                continue

            if downloaded >= count:
                break

        page += 1

    print(f"[Pixabay] Zakończono. Łącznie pobrano {downloaded}/{count} obrazów z Pixabay.")
    return downloaded
