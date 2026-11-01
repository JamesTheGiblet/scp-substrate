#!/usr/bin/env python3
"""Generate an Ed25519 keypair and save it under ~/.config/scp/keys/."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import json, os
from signing import generate_keypair

KEYS_DIR = Path.home() / ".config" / "scp" / "keys"

def main():
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(KEYS_DIR.parent.parent, 0o700)
    os.chmod(KEYS_DIR.parent, 0o700)
    os.chmod(KEYS_DIR, 0o700)

    name = sys.argv[1] if len(sys.argv) > 1 else "default"
    path = KEYS_DIR / f"{name}.json"
    if path.exists():
        sys.exit(f"key already exists: {path}\n(delete it first if you want a new one)")

    kp = generate_keypair()
    path.write_text(json.dumps(kp, indent=2))
    os.chmod(path, 0o600)

    print(f"generated: {path}")
    print(f"  did:key: {kp['did_key']}")
    print()
    print("  ⚠  private key on disk — keep this file safe, back it up offline")

if __name__ == "__main__":
    main()
