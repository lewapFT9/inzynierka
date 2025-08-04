import os

from downloader.pixabay_downloader import download_images_pixabay
from downloader.pexels_downloader import download_images_pexels
from downloader.openverse_downloader import download_images_openverse
from downloader.wikimedia_downloader import download_images_wikimedia

def download_images_fallback(query, total_count, save_dir, progress_callback=None, start_index = 0):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0

    downloaders = [
        ("Pixabay", download_images_pixabay),
        ("Pexels", download_images_pexels),
        ("Openverse", download_images_openverse),
        ("Wikimedia", download_images_wikimedia)
    ]

    current_index = start_index

    for name, downloader in downloaders:
        remaining = total_count - downloaded
        if remaining <= 0:
            break

        print(f"\n Próba pobrania {remaining} obrazów z: {name}")
        newly_downloaded = downloader(query, remaining, save_dir, progress_callback, start_index=current_index)
        downloaded += newly_downloaded
        current_index += newly_downloaded

        print(f" {name} pobrał: {newly_downloaded} obrazów (łącznie: {downloaded}/{total_count})")

    if downloaded < total_count:
        print(f"\n Uwaga: udało się pobrać tylko {downloaded}/{total_count} obrazów.")
    else:
        print(f"\n Udało się! Pobieranie zakończone: {downloaded}/{total_count} obrazów.")

    return downloaded
