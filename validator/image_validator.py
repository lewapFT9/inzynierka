def is_valid_image(img):
    try:
        img = img.convert("RGB")
        img.verify()
        extrema = img.getextrema()

        if all(channel[0] == channel[1] for channel in extrema):
            return False
        return True
    except Exception as e:
        print(f"[Walidacja] Obraz odrzucony: {e}")
        return False
