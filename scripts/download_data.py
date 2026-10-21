"""Download pinned author-published CAN-MIRGU samples; never redistribute raw logs."""

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "375ad16faeab5f1cbec145e8a963a3619b1a7207"
BASE = f"https://raw.githubusercontent.com/sampathrajapaksha/CAN-MIRGU/{COMMIT}/Sample%20dataset/"
FILES = {
    "benign.log": "Benign/Day_1/Benign_day1_file1.log",
    "injection.log": "Attack/Real_attacks/Break_and_fog_light_attack.log",
    "masquerade.log": "Attack/Masquerade_attacks/Break_and_fog_light_masquerade_attack.log",
}
EXPECTED_SHA256 = {
    "benign.log": "7ace6721ddf51768078b07f4070a954a4daacd4766c720d7328600c51ff3148c",
    "injection.log": "48335c1717b9934673d9dccb56048acbd52e858e9a0bdbf2590276a17cf8bfe0",
    "masquerade.log": "81466dd0751c1590b01c695e474d1cd0a3ddc4d71a8eef4cea51571c0e7040cb",
}


def main():
    folder = ROOT / "data/raw"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, path in FILES.items():
        destination = folder / name
        if not destination.exists():
            with urlopen(BASE + path, timeout=120) as response:
                payload = response.read()
            if len(payload) < 1000 or not payload.startswith(b"("):
                raise ValueError(f"invalid download: {name}")
            destination.write_bytes(payload)
        manifest[name] = {
            "url": BASE + path,
            "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        }
        if manifest[name]["sha256"] != EXPECTED_SHA256[name]:
            raise ValueError(
                f"SHA-256 mismatch for {name}; inspect the local file and pinned upstream source"
            )
        print(name, manifest[name]["sha256"])
    (ROOT / "artifacts/data_manifest.json").write_text(
        json.dumps(
            {
                "source": "CAN-MIRGU authors' sample dataset",
                "commit": COMMIT,
                "files": manifest,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
