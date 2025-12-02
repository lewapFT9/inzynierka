import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from downloader.google_config import API_KEY, CSE_ID
from exceptions.exceptions import (
    RateLimitException,
    TooManyFormatFilteredException,
    TooManyResolutionFilteredException,
    SourceExhaustedException,
)

MAX_FORMAT_ERRORS = 40
MAX_RES_ERRORS = 40
SOURCE_NAME = "Google"


def _normalize_ext(pil_format: str):
    """
    Normalizuje format z Pillow do (ext, save_fmt).

    Zwraca:
      ("jpg", "JPEG") / ("png", "PNG") / ("gif", "GIF") / (None, None)
    """
    if not pil_format:
        return None, None

    fmt = pil_format.upper()
    if fmt in ("JPG", "JPEG"):
        return "jpg", "JPEG"
    if fmt == "PNG":
        return "png", "PNG"
    if fmt == "GIF":
        return "gif", "GIF"
    return None, None  # inne formaty pomijamy


def _ext_to_save_fmt(ext: str):
    ext = (ext or "").lower()
    if ext in ("jpg", "jpeg"):
        return "JPEG"
    if ext == "png":
        return "PNG"
    if ext == "gif":
        return "GIF"
    return ext.upper()  # awaryjnie


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
    force_output_format=None,
):
    """
    Pobiera obrazy z Google Custom Search API.

    - allowed_formats: lista np. ["jpg","jpeg","png","gif"] lub None
    - resolution_filter: dict z min_w, min_h, max_w, max_h lub None
    - min_size: (w,h) dla 'crop'
    - force_output_format: np. 'jpg' / 'png' lub None (zachowaj oryginalny)
    """
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    start = 1  # offset CSE API
    format_errors = 0
    resolution_errors = 0

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

        items = data.get("items", [])
        if not items:
            # brak dalszych wyników
            raise SourceExhaustedException(
                f"{SOURCE_NAME}: brak dalszych wyników. "
                f"Pobrano {downloaded} z {count} obrazów."
            )

        for item in items:
            try:
                img_url = item["link"]
                img_data = requests.get(img_url, timeout=10).content
                img = Image.open(BytesIO(img_data))

                ext, save_fmt = _normalize_ext(img.format)
                if ext is None:
                    # Nieobsługiwany format – po prostu pomijamy
                    continue

                # --- FILTR FORMATU ---
                if allowed_formats is not None and ext not in [f.lower() for f in allowed_formats]:
                    format_errors += 1
                    if format_errors >= MAX_FORMAT_ERRORS:
                        raise TooManyFormatFilteredException(
                            f"{SOURCE_NAME}: zbyt wiele obrazów odrzuconych przez filtr formatu."
                        )
                    continue

                # --- FILTR ROZDZIELCZOŚCI ---
                if resolution_filter:
                    w, h = img.size
                    min_w = resolution_filter.get("min_w")
                    min_h = resolution_filter.get("min_h")
                    max_w = resolution_filter.get("max_w")
                    max_h = resolution_filter.get("max_h")

                    if min_w is not None and w < min_w:
                        resolution_errors += 1
                        if resolution_errors >= MAX_RES_ERRORS:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: zbyt wiele obrazów za wąskich."
                            )
                        continue
                    if min_h is not None and h < min_h:
                        resolution_errors += 1
                        if resolution_errors >= MAX_RES_ERRORS:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: zbyt wiele obrazów za niskich."
                            )
                        continue
                    if max_w is not None and w > max_w:
                        resolution_errors += 1
                        if resolution_errors >= MAX_RES_ERRORS:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: zbyt wiele obrazów za szerokich."
                            )
                        continue
                    if max_h is not None and h > max_h:
                        resolution_errors += 1
                        if resolution_errors >= MAX_RES_ERRORS:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: zbyt wiele obrazów za wysokich."
                            )
                        continue

                # --- MINIMALNY ROZMIAR DO CROP ---
                if method == "crop" and min_size is not None:
                    mw, mh = min_size
                    if img.width < mw or img.height < mh:
                        resolution_errors += 1
                        if resolution_errors >= MAX_RES_ERRORS:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: zbyt wiele obrazów za małych dla crop."
                            )
                        continue

                if not is_valid_image(img):
                    continue

                # finalny format
                final_ext = (force_output_format or ext).lower()
                save_format = _ext_to_save_fmt(final_ext)

                idx = start_index + downloaded + 1
                filename = os.path.join(save_dir, f"{idx}.{final_ext}")

                if final_ext in ("jpg", "jpeg"):
                    img = img.convert("RGB")

                img.save(filename, save_format)
                downloaded += 1

                if progress_callback:
                    progress_callback(downloaded + start_index, count + start_index)

                if downloaded >= count:
                    break

            except (TooManyFormatFilteredException, TooManyResolutionFilteredException):
                raise
            except Exception:
                continue

        start += 10

    if downloaded < count:
        # dotarliśmy do limitu paginacji
        raise SourceExhaustedException(
            f"{SOURCE_NAME}: brak dalszych wyników. "
            f"Pobrano {downloaded} z {count} obrazów."
        )

    return downloaded
