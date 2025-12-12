import os
import requests
from PIL import Image
from io import BytesIO
from validator.image_validator import is_valid_image
from downloader.pixabay_config import PIXABAY_API_KEY
from exceptions.exceptions import (
    RateLimitException,
    TooManyFormatFilteredException,
    TooManyResolutionFilteredException,
    SourceExhaustedException,
    TooManyFilesizeFilteredException,
    DownloadCancelledException
)

MAX_FORMAT_ERRORS = 100
MAX_RES_ERRORS = 100
MAX_FILESIZE_ERRORS = 100
SOURCE_NAME = "Pixabay"


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


def download_images_pixabay(
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
    should_stop=None,
):
    os.makedirs(save_dir, exist_ok=True)

    downloaded = 0
    page = 1
    format_errors = 0
    res_errors = 0
    filesize_errors = 0

    while downloaded < count:
        if should_stop and should_stop():
            raise DownloadCancelledException()

        response = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_API_KEY,
                "q": query,
                "image_type": "photo",
                "page": page,
                "per_page": min(20, count - downloaded),
            },
        )

        if response.status_code == 429:
            raise RateLimitException("Pixabay API limit exceeded")

        hits = response.json().get("hits", [])

        if not hits:
            raise SourceExhaustedException(
                f"{SOURCE_NAME}: brak dalszych wyników. Pobrano {downloaded}/{count}."
            )

        for item in hits:
            if should_stop and should_stop():
                raise DownloadCancelledException()

            try:
                url = item["largeImageURL"]
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

                ext, _ = _normalize_ext(img.format)
                if not ext:
                    continue

                # --- FORMAT FILTER ---
                if allowed_formats and ext not in allowed_formats:
                    format_errors += 1
                    if downloaded > 0 and format_errors >= MAX_FORMAT_ERRORS:
                        raise SourceExhaustedException(
                            f"{SOURCE_NAME}: wyczerpane filtrem formatu."
                        )
                    if downloaded == 0 and format_errors >= MAX_FORMAT_ERRORS:
                        raise TooManyFormatFilteredException(
                            f"{SOURCE_NAME}: zbyt restrykcyjne filtry formatu"
                        )
                    continue

                # --- RESOLUTION FILTER ---
                if resolution_filter:
                    w, h = img.size

                    def fail(msg):
                        nonlocal res_errors
                        res_errors += 1
                        if downloaded > 0 and res_errors >= MAX_RES_ERRORS:
                            raise SourceExhaustedException(
                                f"{SOURCE_NAME}: wyczerpane ({msg})"
                            )
                        if downloaded == 0:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: zbyt restrykcyjny filtr ({msg})"
                            )

                    if resolution_filter.get("min_w") and w < resolution_filter["min_w"]:
                        fail("za wąskie")
                        continue
                    if resolution_filter.get("min_h") and h < resolution_filter["min_h"]:
                        fail("za niskie")
                        continue
                    if resolution_filter.get("max_w") and w > resolution_filter["max_w"]:
                        fail("za szerokie")
                        continue
                    if resolution_filter.get("max_h") and h > resolution_filter["max_h"]:
                        fail("za wysokie")
                        continue

                # --- CROP ---
                if method == "crop" and min_size:
                    mw, mh = min_size
                    if img.width < mw or img.height < mh:
                        res_errors += 1
                        if downloaded > 0 and res_errors >= MAX_RES_ERRORS:
                            raise SourceExhaustedException(
                                f"{SOURCE_NAME}: wyczerpane (crop)"
                            )
                        if downloaded == 0:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: za małe do crop"
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

            except (
                TooManyFormatFilteredException,
                TooManyResolutionFilteredException,
                TooManyFilesizeFilteredException,
            ):
                raise
            except Exception:
                continue

        page += 1

    return downloaded
