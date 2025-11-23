import os
import random
import shutil

def split_images(source_dir, dest_dir, subset_ratio, subsets):

    images = [f for f in os.listdir(source_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
    random.shuffle(images)

    n = len(images)
    counts = {
        'train': int(subset_ratio[0] / 100 * n),
        'valid': int(subset_ratio[1] / 100 * n),
        'test': n
    }
    counts['test'] = n - counts['train'] - counts['valid']

    i = 0
    for subset in subsets:
        subset_dir = os.path.join(dest_dir, subset)
        os.makedirs(subset_dir, exist_ok=True)
        for _ in range(counts[subset]):
            if i >= len(images):
                break
            src = os.path.join(source_dir, images[i])
            ext = os.path.splitext(src)[1]  # zachowaj rozszerzenie
            dst = os.path.join(subset_dir, f"{i + 1}{ext}")
            shutil.copy2(src, dst)
            i += 1
