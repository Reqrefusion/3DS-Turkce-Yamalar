"""Biçim hatalarını yakalayan hedefli regresyon testleri: python -m unittest discover -s araclar"""
import unittest,struct,random
import drmario_tool as t
class FormatTests(unittest.TestCase):
 def test_arcv_uses_console_alignment(self):
  parsed={'entries':[{'name':'x','hash':1,'data':b'abc'}]}
  raw=t.arcv_build(parsed)
  rebuilt=t.arcv_parse(raw)
  self.assertEqual(rebuilt['entries'][0]['offset'] % 0x80,0)
  self.assertEqual(len(raw) % 0x80,0)
 def test_lzss_wrap_and_overlap(self):
  rng=random.Random(413);noise=bytes(rng.randrange(256) for _ in range(9000))
  for raw in [b'',b'a'*18000,bytes(range(256))*50,noise+noise[-4096:],b'abc'*8000]:
   self.assertEqual(t.lzss_decompress(t.lzss_compress(raw),len(raw)),raw)
 def test_real_compression(self):
  self.assertLess(len(t.sszl_pack(b'abc'*10000)),5000)
 def test_sszl_truncated(self):
  with self.assertRaises(ValueError):t.sszl_unpack(t.sszl_pack(b'hello')[:-1])
 def test_color_green_channels(self):
  for fmt in [5,7]:
   for color in [(0,255,0,255),(255,255,255,255),(0,0,0,255)]:
    raw=t._raw_from_rgba(color,fmt,0,'<');self.assertEqual(t._rgba_from_raw(raw,fmt,0,'<'),color)
 def test_texture_padding_rotation(self):
  # Mantıksal 10x5, fiziksel 8x16; üst-sol piksel fiziksel (7,0).
  raw=bytearray(8*16*4);i=t._morton(7,0,8);raw[i*4:i*4+4]=bytes((255,0,0,255))
  footer=struct.pack('<4sHHIIHBB',b'FLIM',0xfeff,20,0x07010000,len(raw)+40,1,0,0)
  footer+=struct.pack('<4sIHHHBBI',b'imag',16,10,5,128,9,4,len(raw))
  image,_=t.bflim_decode_image(bytes(raw)+footer)
  self.assertEqual(image.size,(10,5));self.assertEqual(image.getpixel((0,0)),(255,0,0,255))
  self.assertEqual(image.getbbox(),(0,0,1,1))
  self.assertEqual(t.bflim_encode_image(image,bytes(raw)+footer),bytes(raw)+footer)
 def test_msbt_control_embedded_zero(self):
  text='A'+struct.pack('<4H',14,0,2,2).decode('utf-16le')+'\0'+'B'
  payload=text.encode('utf-16le')+b'\0\0';body=struct.pack('<II',1,8)+payload
  head=bytearray(32);head[:8]=b'MsgStdBn';head[8:10]=b'\xff\xfe';head[12]=1;struct.pack_into('<H',head,14,1)
  msbt=bytes(head)+b'TXT2'+struct.pack('<I',len(body))+b'\0'*8+body
  self.assertEqual(t.msbt_texts(msbt),[text]);self.assertEqual(t.msbt_texts(t.msbt_replace_texts(msbt,[text])),[text])
if __name__=='__main__':unittest.main()
