#!/usr/bin/env python3
"""Sign an SCP document with an Ed25519 key from ~/.config/scp/keys/."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import argparse, json
from store.signing import sign, normalise_signature

KEYS_DIR = Path.home() / ".config" / "scp" / "keys"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("doc", help="SCP document (.json)")
    p.add_argument("-k", "--key", default="default",
                   help="key name (without .json) or full path")
    p.add_argument("-o", "--out", help="output path (default: <doc>.signed.json)")
    args = p.parse_args()

    doc_path = Path(args.doc)
    if not doc_path.exists():
        raise SystemExit(f"document not found: {doc_path}")

    key_path = Path(args.key)
    if not key_path.exists():
        key_path = KEYS_DIR / f"{args.key}.json"
    if not key_path.exists():
        raise SystemExit(f"key not found: {args.key}")

    doc = json.loads(doc_path.read_text(encoding="utf-8"))
    kp  = json.loads(key_path.read_text(encoding="utf-8"))

    signed = sign(normalise_signature(doc), kp["private_b64"])

    out = Path(args.out) if args.out else doc_path.with_suffix(".signed.json")
    out.write_text(json.dumps(signed, indent=2, ensure_ascii=False))

    print(f"signed: {doc_path} → {out}")
    print(f"  key_id: {signed['signature']['key_id']}")
    print(f"  value:  {signed['signature']['value'][:32]}...")

if __name__ == "__main__":
    main()
