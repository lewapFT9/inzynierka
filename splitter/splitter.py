import os
import shutil
import random

def split_images(src_folder, dst_folder, ratios, subsets, mode="random"):
    train_ratio, valid_ratio, test_ratio = ratios

    # wczytujemy wszystkie pliki
    files = [
        f for f in os.listdir(src_folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
    ]

    # --- TRYB PRIORYTETOWY ---
    if mode == "prioritize":
        def extract_num(filename):
            name, _ = os.path.splitext(filename)
            return int(name) if name.isdigit() else 999999999

        files = sorted(files, key=extract_num)

    # --- TRYB RANDOM ---
    else:
        random.shuffle(files)

    total = len(files)
    train_end = int((train_ratio / 100) * total)
    valid_end = train_end + int((valid_ratio / 100) * total)

    train_files = files[:train_end]
    valid_files = files[train_end:valid_end]
    test_files = files[valid_end:]

    # Tworzymy folder docelowy
    for subset in subsets:
        os.makedirs(os.path.join(dst_folder, subset), exist_ok=True)

    def copy_files(fs, subset):
        subset_path = os.path.join(dst_folder, subset)
        for filename in fs:
            shutil.copy(os.path.join(src_folder, filename), os.path.join(subset_path, filename))

    if "train" in subsets:
        copy_files(train_files, "train")
    if "valid" in subsets:
        copy_files(valid_files, "valid")
    if "test" in subsets:
        copy_files(test_files, "test")
