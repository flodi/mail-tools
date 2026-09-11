#!/usr/bin/env python3
"""
Converte un file .emlx in .eml rimuovendo la prima riga (byte count Apple)
e il metadata plist in fondo.

Usage: emlx_to_eml.py <input.emlx> <output.eml>
"""
import sys

if len(sys.argv) != 3:
    print("Usage: emlx_to_eml.py <input.emlx> <output.eml>", file=sys.stderr)
    sys.exit(1)

with open(sys.argv[1], 'rb') as f:
    data = f.read()

parts = data.split(b'\n', 1)
try:
    byte_count = int(parts[0].strip())
    out = parts[1][:byte_count]
except Exception:
    out = data  # fallback: usa tutto il contenuto

with open(sys.argv[2], 'wb') as f:
    f.write(out)
