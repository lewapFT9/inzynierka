import os
import uuid

def get_next_image_index(folder_path):
    max_index = 0
    for filename in os.listdir(folder_path):
        name, ext = os.path.splitext(filename)
        if ext.lower() in (".jpg", ".jpeg", ".png", ".gif") and name.isdigit():
            index = int(name)
            if index > max_index:
                max_index = index
    return max_index + 1



def renumber_images(folder):
    images = sorted(
        f for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
    )

    # === ETAP 1: tymczasowe nazwy ===
    temp_names = []

    for filename in images:
        ext = os.path.splitext(filename)[1]
        temp_name = f"__tmp_{uuid.uuid4().hex}{ext}"
        old_path = os.path.join(folder, filename)
        temp_path = os.path.join(folder, temp_name)
        os.rename(old_path, temp_path)
        temp_names.append(temp_name)

    # === ETAP 2: finalna numeracja ===
    for idx, temp_name in enumerate(sorted(temp_names), start=1):
        ext = os.path.splitext(temp_name)[1]
        final_name = f"{idx}{ext}"
        temp_path = os.path.join(folder, temp_name)
        final_path = os.path.join(folder, final_name)
        os.rename(temp_path, final_path)
