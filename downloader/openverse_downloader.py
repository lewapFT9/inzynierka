import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image

def download_images_openverse(query, count, save_dir, progress_callback=None, start_index=0):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    page = 1 + start_index // 20

    print(f"[Openverse] Start pobierania ({count} obrazów) dla zapytania: '{query}'")

    while downloaded < count:
        params = {
            "q": query,
            "license": "cc_by",
            "source": "all",
            "page_size": min(20, count - downloaded),
            "page": page
        }

        response = requests.get("https://api.openverse.engineering/v1/images", params=params)

        if response.status_code != 200:
            print(f"[Openverse] Błąd HTTP: {response.status_code}")
            break

        data = response.json()
        results = data.get("results", [])
        print(f"[Openverse] Otrzymano {len(results)} wyników.")

        if not results:
            break

        for item in results:
            try:
                img_url = item.get("url")
                print(f"[Openverse] Pobieram: {img_url}")
                img_data = requests.get(img_url, timeout=10).content
                img = Image.open(BytesIO(img_data))

                if is_valid_image(img):
                    filename = os.path.join(save_dir, f"{downloaded + 1 + start_index}.jpg")
                    img.convert("RGB").save(filename)
                    downloaded += 1
                    print(f"[Openverse] Zapisano: {filename}")
                    if progress_callback:
                        progress_callback(downloaded + start_index, count + start_index)
                else:
                    print("[Openverse] Odrzucony przez walidator.")
            except Exception as e:
                print(f"[Openverse] Błąd przy pobieraniu obrazu: {e}")
                continue

            if downloaded >= count:
                break

        page += 1

    print(f"[Openverse] Zakończono. Łącznie pobrano {downloaded}/{count} obrazów z Openverse.")
    return downloaded
