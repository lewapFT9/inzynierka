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
    TooManyFilesizeFilteredException,
)

MAX_FORMAT_ERRORS = 40
MAX_RES_ERRORS = 40
MAX_FILESIZE_ERRORS = 40
SOURCE_NAME = "Google"


def _normalize_ext(fmt):
    if not fmt:
        return None, None
    fmt = fmt.upper()
    if fmt in ("JPEG", "JPG"):
        return "jpg", "JPEG"
    if fmt == "PNG":
        return "png", "PNG"
    if fmt == "GIF":
        return "gif", "GIF"
    return None, None


def _ext_to_save_fmt(ext):
    ext = ext.lower()
    if ext in ("jpg", "jpeg"):
        return "JPEG"
    if ext == "png":
        return "PNG"
    if ext == "gif":
        return "GIF"
    return ext.upper()


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
    filesize_filter=None,
):
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    start = 1

    format_errors = 0
    res_errors = 0
    filesize_errors = 0

    while downloaded < count and start <= 91:
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "q": query,
                "cx": CSE_ID,
                "key": API_KEY,
                "searchType": "image",
                "start": start,
                "num": min(10, count - downloaded),
            },
        )

        if response.status_code == 429:
            raise RateLimitException("Google API limit exceeded.")

        data = response.json()
        items = data.get("items", [])

        if not items:
            raise SourceExhaustedException(
                f"{SOURCE_NAME}: brak dalszych wyników. Pobrano {downloaded}/{count}."
            )

        for item in items:
            try:
                url = item["link"]
                raw = requests.get(url, timeout=10).content

                # --- FILTR WAGI PLIKU (MB) ---
                if filesize_filter:
                    size_mb = len(raw) / (1024 * 1024)
                    min_mb = filesize_filter.get("min_mb")
                    max_mb = filesize_filter.get("max_mb")

                    if min_mb is not None and size_mb < min_mb:
                        filesize_errors += 1
                        if downloaded > 0 and filesize_errors >= MAX_FILESIZE_ERRORS:
                            raise SourceExhaustedException(
                                f"{SOURCE_NAME}: wyczerpane przez filtr minimalnej wagi pliku."
                            )
                        if downloaded == 0 and filesize_errors >= MAX_FILESIZE_ERRORS:
                            raise TooManyFilesizeFilteredException(
                                f"{SOURCE_NAME}: zbyt restrykcyjny filtr minimalnej wagi pliku."
                            )
                        continue

                    if max_mb is not None and size_mb > max_mb:
                        filesize_errors += 1
                        if downloaded > 0 and filesize_errors >= MAX_FILESIZE_ERRORS:
                            raise SourceExhaustedException(
                                f"{SOURCE_NAME}: wyczerpane przez filtr maksymalnej wagi pliku."
                            )
                        if downloaded == 0 and filesize_errors >= MAX_FILESIZE_ERRORS:
                            raise TooManyFilesizeFilteredException(
                                f"{SOURCE_NAME}: zbyt restrykcyjny filtr maksymalnej wagi pliku."
                            )
                        continue

                img = Image.open(BytesIO(raw))

                ext, save_fmt = _normalize_ext(img.format)
                if not ext:
                    continue

                # --- FILTR FORMATU ---
                if allowed_formats and ext not in allowed_formats:
                    format_errors += 1
                    if downloaded > 0 and format_errors >= MAX_FORMAT_ERRORS:
                        raise SourceExhaustedException(
                            f"{SOURCE_NAME}: wyczerpane filtrem formatu."
                        )
                    if downloaded == 0 and format_errors >= MAX_FORMAT_ERRORS:
                        raise TooManyFormatFilteredException(
                            f"{SOURCE_NAME}: zbyt restrykcyjny filtr formatu."
                        )
                    continue

                # --- FILTR ROZDZIELCZOŚCI ---
                if resolution_filter:
                    w, h = img.size
                    if resolution_filter.get("min_w") and w < resolution_filter["min_w"]:
                        res_errors += 1
                        if downloaded > 0 and res_errors >= MAX_RES_ERRORS:
                            raise SourceExhaustedException(
                                f"{SOURCE_NAME}: wyczerpane (za wąskie)."
                            )
                        if downloaded == 0 and res_errors >= MAX_RES_ERRORS:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: zbyt restrykcyjne filtry rozdzielczości."
                            )
                        continue
                    if resolution_filter.get("min_h") and h < resolution_filter["min_h"]:
                        res_errors += 1
                        if downloaded > 0 and res_errors >= MAX_RES_ERRORS:
                            raise SourceExhaustedException(
                                f"{SOURCE_NAME}: wyczerpane (za niskie)."
                            )
                        if downloaded == 0:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: zbyt restrykcyjne filtry rozdzielczości."
                            )
                        continue
                    if resolution_filter.get("max_w") and w > resolution_filter["max_w"]:
                        res_errors += 1
                        if downloaded > 0 and res_errors >= MAX_RES_ERRORS:
                            raise SourceExhaustedException(
                                f"{SOURCE_NAME}: wyczerpane (za szerokie)."
                            )
                        if downloaded == 0:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: zbyt restrykcyjne filtry rozdzielczości."
                            )
                        continue
                    if resolution_filter.get("max_h") and h > resolution_filter["max_h"]:
                        res_errors += 1
                        if downloaded > 0 and res_errors >= MAX_RES_ERRORS:
                            raise SourceExhaustedException(
                                f"{SOURCE_NAME}: wyczerpane (za wysokie)."
                            )
                        if downloaded == 0:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: zbyt restrykcyjne filtry rozdzielczości."
                            )
                        continue

                # --- CROP ---
                if method == "crop" and min_size:
                    mw, mh = min_size
                    if img.width < mw or img.height < mh:
                        res_errors += 1
                        if downloaded > 0 and res_errors >= MAX_RES_ERRORS:
                            raise SourceExhaustedException(
                                f"{SOURCE_NAME}: wyczerpane (crop)."
                            )
                        if downloaded == 0:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: za małe obrazy dla crop."
                            )
                        continue

                if not is_valid_image(img):
                    continue

                final_ext = (force_output_format or ext).lower()
                filename = os.path.join(save_dir, f"{start_index + downloaded + 1}.{final_ext}")

                if final_ext in ("jpg", "jpeg"):
                    img = img.convert("RGB")

                img.save(filename, _ext_to_save_fmt(final_ext))
                downloaded += 1

                if progress_callback:
                    progress_callback(start_index + downloaded, start_index + count)

            except (TooManyFormatFilteredException, TooManyResolutionFilteredException, TooManyFilesizeFilteredException):
                raise
            except Exception:
                continue

        start += 10

    if downloaded < count:
        raise SourceExhaustedException(
            f"{SOURCE_NAME}: brak dalszych wyników. Pobrano {downloaded}/{count}."
        )

    return downloaded
