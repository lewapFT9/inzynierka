import os
import requests
from PIL import Image
from io import BytesIO

from validator.image_validator import is_valid_image
from downloader.unsplash_config import UNSPLASH_ACCESS_KEY
from exceptions.exceptions import (
    RateLimitException,
    TooManyFormatFilteredException,
    TooManyResolutionFilteredException,
    SourceExhaustedException,
)

MAX_FORMAT_ERRORS = 100
MAX_RES_ERRORS = 100
SOURCE_NAME = "Unsplash"


def _normalize_ext(pil_format: str):
    if not pil_format:
        return None, None

    fmt = pil_format.upper()
    if fmt in ("JPG", "JPEG"):
        return "jpg", "JPEG"
    if fmt == "PNG":
        return "png", "PNG"
    if fmt == "GIF":
        return "gif", "GIF"
    return None, None


def _ext_to_save_fmt(ext: str):
    ext = (ext or "").lower()
    if ext in ("jpg", "jpeg"):
        return "JPEG"
    if ext == "png":
        return "PNG"
    if ext == "gif":
        return "GIF"
    return ext.upper()


def download_images_unsplash(
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
    os.makedirs(save_dir, exist_ok=True)
    downloaded = 0
    page = 1
    format_errors = 0
    resolution_errors = 0

    while downloaded < count:
        params = {
            "query": query,
            "client_id": UNSPLASH_ACCESS_KEY,
            "page": page,
            "per_page": min(10, count - downloaded),
        }

        response = requests.get(
            "https://api.unsplash.com/search/photos",
            params=params,
        )

        if response.status_code == 403 and "Rate Limit Exceeded" in response.text:
            raise RateLimitException("Unsplash API limit exceeded")

        if response.status_code != 200:
            raise RateLimitException("Unsplash API returned an error")

        results = response.json().get("results", [])
        if not results:
            raise SourceExhaustedException(
                f"{SOURCE_NAME}: brak dalszych wyników. "
                f"Pobrano {downloaded} z {count} obrazów."
            )

        for item in results:
            try:
                img_url = item["urls"]["regular"]
                img_data = requests.get(img_url, timeout=10).content
                img = Image.open(BytesIO(img_data))

                ext, _ = _normalize_ext(img.format)
                if ext is None:
                    continue

                if allowed_formats is not None and ext not in [f.lower() for f in allowed_formats]:
                    format_errors += 1
                    if format_errors >= MAX_FORMAT_ERRORS:
                        raise TooManyFormatFilteredException(
                            f"{SOURCE_NAME}: zbyt wiele obrazów odrzuconych przez filtr formatu."
                        )
                    continue

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

                if method == "crop" and min_size is not None:
                    mw, mh = min_size
                    if img.width < mw or img.height < mh:
                        resolution_errors += 1
                        if resolution_errors >= MAX_RES_ERRORS:
                            raise TooManyResolutionFilteredException(
                                f"{SOURCE_NAME}: zbyt wiele zbyt małych obrazów dla crop."
                            )
                        continue

                if not is_valid_image(img):
                    continue

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

        page += 1

    return downloaded
