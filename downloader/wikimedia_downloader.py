import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image

def download_images_wikimedia(query, count, save_dir, progress_callback=None, start_index=0):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    sroffset = 0

    print(f"[Wikimedia] Start pobierania ({count} obrazów) dla zapytania: '{query}'")

    while downloaded < count:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": 6,
            "gsrlimit": min(10, count - downloaded),
            "gsroffset": sroffset,
            "gsrsearch": query,
            "prop": "imageinfo",
            "iiprop": "url"
        }

        response = requests.get("https://commons.wikimedia.org/w/api.php", params=params)

        if response.status_code != 200:
            print(f"[Wikimedia] Błąd HTTP: {response.status_code}")
            break

        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        print(f"[Wikimedia] Otrzymano {len(pages)} wyników.")

        if not pages:
            break

        for _, item in pages.items():
            try:
                img_url = item["imageinfo"][0]["url"]
                print(f"[Wikimedia] Pobieram: {img_url}")
                img_data = requests.get(img_url, timeout=10).content
                img = Image.open(BytesIO(img_data))

                if is_valid_image(img):
                    filename = os.path.join(save_dir, f"{downloaded + 1 + start_index}.jpg")
                    img.convert("RGB").save(filename)
                    downloaded += 1
                    print(f"[Wikimedia] Zapisano: {filename}")
                    if progress_callback:
                        progress_callback(downloaded + start_index, count + start_index)
                else:
                    print("[Wikimedia] Odrzucony przez walidator.")
            except Exception as e:
                print(f"[Wikimedia] Błąd przy pobieraniu obrazu: {e}")
                continue

            if downloaded >= count:
                break

        sroffset += 10

    print(f"[Wikimedia] Zakończono. Łącznie pobrano {downloaded}/{count} obrazów z Wikimedia.")
    return downloaded
