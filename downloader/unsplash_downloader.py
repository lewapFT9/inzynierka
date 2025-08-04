import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from downloader.unsplash_config import UNSPLASH_ACCESS_KEY

def download_images_unsplash(query, count, save_dir, progress_callback=None, start_index=0):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    page = 1

    print(f"[Unsplash] Start pobierania ({count} obrazów) dla zapytania: '{query}'")
    print(f"[Unsplash] Używany klucz API: {'OK' if UNSPLASH_ACCESS_KEY else 'BRAK!'}")

    while downloaded < count:
        params = {
            "query": query,
            "client_id": UNSPLASH_ACCESS_KEY,
            "page": page,
            "per_page": min(10, count - downloaded)
        }

        print(f"[Unsplash] Zapytanie: page={page}, per_page={params['per_page']}")
        response = requests.get("https://api.unsplash.com/search/photos", params=params)

        if response.status_code != 200:
            print(f"[Unsplash] Błąd HTTP: {response.status_code}")
            print(f"[Unsplash] Treść odpowiedzi: {response.text}")
            break

        data = response.json()
        results = data.get("results", [])
        print(f"[Unsplash] Otrzymano {len(results)} wyników.")

        if not results:
            print("[Unsplash] Brak wyników — kończę.")
            break

        for item in results:
            try:
                img_url = item["urls"]["regular"]
                print(f"[Unsplash] Próbuję pobrać: {img_url}")
                img_data = requests.get(img_url, timeout=10).content
                img = Image.open(BytesIO(img_data))

                if is_valid_image(img):
                    filename = os.path.join(save_dir, f"{start_index + downloaded + 1}.jpg")
                    img.convert("RGB").save(filename)
                    downloaded += 1
                    print(f"[Unsplash] Zapisano: {filename}")
                    if progress_callback:
                        progress_callback(downloaded + start_index , count + start_index )
                else:
                    print(f"[Unsplash] Obraz odrzucony przez walidację.")
            except Exception as e:
                print(f"[Unsplash] Błąd przy pobieraniu obrazu: {e}")
                continue

            if downloaded >= count:
                break

        page += 1

    print(f"[Unsplash] Zakończono. Łącznie pobrano {downloaded}/{count} obrazów z Unsplash.")
    return downloaded
