"""
Run this from your backend folder:
  python diagnose_env.py

It will tell you exactly why .env is not loading.
"""
import os
import sys
from pathlib import Path

here = Path(__file__).parent

candidates = [
    here / ".env",
    here.parent / ".env",
    Path(".env"),
    Path("../.env"),
]

print("=== .env file search ===")
for p in candidates:
    resolved = p.resolve()
    exists = resolved.exists()
    print(f"  {'FOUND ' if exists else 'MISS  '} {resolved}")
    if exists:
        print(f"         size: {resolved.stat().st_size} bytes")
        raw = resolved.read_bytes()
        print(f"         first 4 bytes (hex): {raw[:4].hex()}")
        if raw[:3] == b'\xef\xbb\xbf':
            print("         ⚠ BOM detected (UTF-8 with BOM) — this can break dotenv!")
        lines = raw.replace(b'\r\n', b'\n').replace(b'\r', b'\n').split(b'\n')
        print(f"         lines: {len(lines)}")
        for i, line in enumerate(lines[:10], 1):
            try:
                decoded = line.decode('utf-8').strip()
            except Exception:
                decoded = repr(line)
            # mask values for security
            if '=' in decoded and not decoded.startswith('#'):
                k, _, v = decoded.partition('=')
                masked = v[:4] + '***' if len(v) > 4 else ('SET' if v else 'EMPTY')
                print(f"         line {i}: {k.strip()}={masked}")
            else:
                print(f"         line {i}: {decoded[:60]}")

print()
print("=== dotenv load test ===")
from dotenv import load_dotenv, dotenv_values

for p in candidates:
    resolved = p.resolve()
    if resolved.exists():
        vals = dotenv_values(resolved)
        print(f"  {resolved}")
        for k, v in vals.items():
            masked = (v[:4] + '***') if v and len(v) > 4 else ('SET' if v else 'EMPTY')
            print(f"    {k} = {masked}")
        if not vals:
            print("    (no key=value pairs parsed — check formatting)")

print()
print("=== os.environ after load ===")
load_dotenv(Path(".env"))
load_dotenv(Path("../.env"))
for k in ["SERPAPI_KEY", "FIRECRAWL_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"]:
    v = os.getenv(k, "")
    status = (v[:4] + '***') if v else "NOT SET"
    print(f"  {k}: {status}")
