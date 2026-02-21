import zlib, struct

inp = "pajama.zlib"
outp = "pajama.sarc"

data = open(inp, "rb").read()
raw = zlib.decompress(data[4:])   # ilk 4 byte boyut, sonra zlib
open(outp, "wb").write(raw)

print("OK ->", outp, "size:", len(raw))