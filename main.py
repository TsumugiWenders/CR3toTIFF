import rawpy
import os
from tqdm import tqdm
from PIL import Image
import subprocess
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed

input_dir = "input_cr3"
output_dir = "output_tiff"

os.makedirs(output_dir, exist_ok=True)

files = [f for f in os.listdir(input_dir) if f.lower().endswith(".cr3")]

MAX_WORKERS = min(16, os.cpu_count() or 8)
BATCH_SIZE = 50


def process_file(file):
    input_path = os.path.join(input_dir, file)
    output_path = os.path.join(output_dir, os.path.splitext(file)[0] + ".tiff")

    try:
        if os.path.exists(output_path):
            return None

        with rawpy.imread(input_path) as raw:
            rgb = raw.postprocess(use_camera_wb=True, output_bps=8)

        img = Image.fromarray(rgb)
        img.save(output_path, format="TIFF", compression="tiff_deflate")

        if shutil.which("exiftool"):
            subprocess.run([
                "exiftool",
                "-TagsFromFile", input_path,
                "-all:all",
                "-overwrite_original",
                output_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return None

    except Exception as e:
        return f"{file} -> {e}"


if __name__ == "__main__":
    errors = []

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []

        for i in range(0, len(files), BATCH_SIZE):
            batch = files[i:i + BATCH_SIZE]

            for file in batch:
                futures.append(executor.submit(process_file, file))

            for future in tqdm(as_completed(futures), total=len(futures), desc="转换进度"):
                result = future.result()
                if result:
                    errors.append(result)

    print("\n--- 失败文件 ---")
    for e in errors:
        print(e)