import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from downloader.google_config import API_KEY, CSE_ID
from downloader.unsplash_downloader import download_images_unsplash
from downloader.fallback_downloader import download_images_fallback

def download_images_google(query, count, save_dir, progress_callback=None, start_index=0):
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

        try:
            response = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
            response.raise_for_status()
            data = response.json()

            if "items" not in data:
                print("Brak wyników – zakończono Google.")
                break

            for item in data["items"]:
                try:
                    img_url = item["link"]
                    img_data = requests.get(img_url, timeout=10).content
                    img = Image.open(BytesIO(img_data))

                    if is_valid_image(img):
                        filename = os.path.join(save_dir, f"{start_index + downloaded + 1}.jpg")
                        img.convert("RGB").save(filename)
                        downloaded += 1
                        if progress_callback:
                            progress_callback(downloaded, count)

                    if downloaded >= count:
                        break
                except Exception:
                    continue

        except requests.exceptions.HTTPError as e:
            print(f"Błąd zapytania Google API: {e}")
            break

        start += 10

    print(f"Ukończono pobieranie z Google: {downloaded}/{count} obrazów.")

    if downloaded < count:
        remaining = count - downloaded
        print(f"Próbuję pobrać brakujące {remaining} obrazów z Unsplash...")
        additional = download_images_unsplash(
            query, remaining, save_dir, progress_callback, start_index=downloaded
        )
        downloaded += additional

    if downloaded < count:
        remaining = count - downloaded
        print(
            f"Próbuję pobrać brakujące {remaining} obrazów z innych źródeł")
        additional = download_images_fallback(
            query, remaining, save_dir, progress_callback, start_index=downloaded
        )
        downloaded += additional

    print(f"Łącznie pobrano: {downloaded}/{count} obrazów (Google + Unsplash + fallback).")
    return downloaded
