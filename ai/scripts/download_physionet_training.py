import re
import shutil
import time
import urllib.request
from pathlib import Path

BASE_URL = "https://physionet.org/files/challenge-2019/1.0.0/training/"
TRAINING_SETS = ["training_setA", "training_setB"]

repo_root = Path(__file__).resolve().parents[2]
raw_root = repo_root / "ai" / "data" / "raw"
raw_root.mkdir(parents=True, exist_ok=True)

failed_downloads = []


def fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", "replace")


def download_file(url: str, target_path: Path) -> None:
    if target_path.exists():
        print(f"SKIP {target_path}", flush=True)
        return

    temp_path = target_path.with_suffix(target_path.suffix + ".part")

    for attempt in range(1, 4):
        if temp_path.exists():
            temp_path.unlink()

        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(request, timeout=180) as response:
                with open(temp_path, "wb") as out:
                    shutil.copyfileobj(response, out)

            temp_path.replace(target_path)
            print(f"DOWNLOADED {target_path}", flush=True)
            return

        except Exception as exc:
            if temp_path.exists():
                temp_path.unlink()

            if attempt < 3:
                print(
                    f"RETRY {attempt}/3 {target_path}: {exc}",
                    flush=True
                )
                time.sleep(5)
            else:
                print(
                    f"FAILED AFTER 3 ATTEMPTS {target_path}: {exc}",
                    flush=True
                )
                raise


for training_set in TRAINING_SETS:
    set_url = BASE_URL + training_set + "/"
    dest_dir = raw_root / training_set
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        index_html = fetch_html(set_url)
    except Exception as exc:
        failed_downloads.append({"set": training_set, "url": set_url, "error": str(exc)})
        print(f"FETCH_ERROR {training_set}: {exc}", flush=True)
        continue

    psv_links = sorted(set(re.findall(r'href="([^"]+\.psv)"', index_html)))
    if not psv_links:
        failed_downloads.append({
            "set": training_set,
            "url": set_url,
            "error": "No .psv links found in official directory listing",
        })
        print(f"NO_PSV_FILES {training_set}", flush=True)
        continue

    print(f"{training_set}: found {len(psv_links)} .psv files", flush=True)

    for index, link in enumerate(psv_links, start=1):
        file_url = set_url + link
        target_path = dest_dir / Path(link).name

        if target_path.exists():
            print(f"[{index}/{len(psv_links)}] SKIP {target_path}", flush=True)
            continue

        try:
            download_file(file_url, target_path)
        except Exception as exc:
            failed_downloads.append({"set": training_set, "url": file_url, "error": str(exc)})
            print(f"[{index}/{len(psv_links)}] FAILED {file_url}: {exc}", flush=True)
            continue

    final_count = sum(1 for _ in dest_dir.glob("*.psv"))
    print(f"VERIFIED {training_set}: {final_count} files", flush=True)

print("\nFINAL SUMMARY", flush=True)
for training_set in TRAINING_SETS:
    count = sum(1 for _ in (raw_root / training_set).glob("*.psv"))
    print(f"{training_set}: {count} files", flush=True)

print(f"FAILED_DOWNLOADS: {len(failed_downloads)}", flush=True)
for item in failed_downloads:
    print(item, flush=True)

used_bytes = sum(p.stat().st_size for p in raw_root.rglob("*") if p.is_file())
print(f"TOTAL_DISK_SPACE_USED_BYTES: {used_bytes}", flush=True)
print(f"TOTAL_DISK_SPACE_USED_MB: {used_bytes / (1024 * 1024):.2f} MB", flush=True)
print(f"RAW_ROOT_EXISTS: {raw_root.exists()}", flush=True)
print(f"RAW_ROOT_PATH: {raw_root.resolve()}", flush=True)
print(
    f"ALL_FILES_WITHIN_AI_RAW: {all(str(p.resolve()).startswith(str(raw_root.resolve())) for p in raw_root.rglob('*') if p.is_file())}",
    flush=True,
)
