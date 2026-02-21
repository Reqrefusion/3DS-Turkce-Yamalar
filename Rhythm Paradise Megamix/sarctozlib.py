import zlib, struct

raw = open("pajama.sarc", "rb").read()
comp = zlib.compress(raw, level=9)
open("pajama_new.zlib", "wb").write(struct.pack(">I", len(raw)) + comp)

print("OK -> pajama_new.zlib")