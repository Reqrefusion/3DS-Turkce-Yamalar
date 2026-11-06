from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import sys,json
sys.path.insert(0,'/mnt/data/fullblox_work/tools')
from bflim_codec import decode_bflim
ROOT=Path('/mnt/data/fullblox_localized_png')
OUT=Path('/mnt/data/fullblox_work/previews');OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
# palette sampled/approximated from official START/CLEAR assets
COLORS=[(235,80,49,255),(249,200,38,255),(57,109,224,255),(79,194,42,255),(237,96,48,255),(151,77,208,255)]
WHITE=(250,247,224,255); BLUE=(25,51,167,255); EDGE=(25,45,120,255)

def rainbow_text(text,size,canvas, top_margin=0):
    scale=4; W,H=canvas[0]*scale,canvas[1]*scale
    font=ImageFont.truetype(FONT,size*scale)
    # widths per glyph with tiny negative tracking
    d=ImageDraw.Draw(Image.new('RGBA',(1,1)))
    widths=[d.textlength(ch,font=font) for ch in text]
    track=-1.2*scale
    total=sum(widths)+track*(len(text)-1)
    x=(W-total)/2; y=top_margin*scale
    img=Image.new('RGBA',(W,H),(0,0,0,0)); dr=ImageDraw.Draw(img)
    # common baselines; outer dark edge and blue drop shadow
    for i,ch in enumerate(text):
        w=widths[i]
        # shadow down and slightly right; large blue mass like official assets
        dr.text((x+1*scale,y+4*scale),ch,font=font,fill=BLUE,stroke_width=3*scale,stroke_fill=BLUE)
        x+=w+track
    x=(W-total)/2
    for i,ch in enumerate(text):
        w=widths[i]; fill=COLORS[i%len(COLORS)]
        # dark keyline behind white outline
        dr.text((x,y),ch,font=font,fill=fill,stroke_width=4*scale,stroke_fill=EDGE)
        # white outline and face
        dr.text((x,y),ch,font=font,fill=fill,stroke_width=2*scale,stroke_fill=WHITE)
        # subtle highlight on upper face by drawing a semi-transparent white offset mask? keep crisp
        x+=w+track
    return img.resize(canvas,Image.Resampling.LANCZOS)

def make_start_clear():
    # Match English template display sizes exactly
    start=rainbow_text('BAŞLA!',32,(198,44),top_margin=-2)
    clear=rainbow_text('TAMAM!',35,(198,56),top_margin=0)
    start.save(OUT/'BAŞLA.png');clear.save(OUT/'TAMAM.png')

def make_map():
    base=Image.open(ROOT/'EURen__G_Btn_Map_EURen.png').convert('RGBA')
    # restore the text area using the panel's left-side vertical gradient
    pix=base.load();
    for y in range(14,35):
        samples=[]
        for x in (12,13,42,43):
            r,g,b,a=pix[x,y];
            if a>0: samples.append((r,g,b,a))
        if samples:
            c=tuple(sum(v[i] for v in samples)//len(samples) for i in range(4))
            for x in range(13,43): pix[x,y]=c
    # Draw HARİTA compactly in the original brown family
    d=ImageDraw.Draw(base); font=ImageFont.truetype(FONT,7)
    text='HARİTA'; box=d.textbbox((0,0),text,font=font,stroke_width=0);tw=box[2]-box[0];th=box[3]-box[1]
    x=(54-tw)//2; y=22-th//2-1
    d.text((x,y),text,font=font,fill=(177,120,79,255))
    base.save(OUT/'HARİTA.png')

def make_congrats():
    # Fullblox has two official congratulations texture schemes. Turkish uses
    # the EURes-style ETC1A4 font + A4 highlight mask because it behaves
    # conventionally and matches the 40px result layout.
    W,H=358,40
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',36)
    text='TEBRİKLER!'
    dummy=ImageDraw.Draw(Image.new('RGBA',(1,1)))
    box=dummy.textbbox((0,0),text,font=font)
    tw=box[2]-box[0]
    x=(W-tw)//2; y=1-box[1]
    # Palette sampled from the official EURes result texture.
    img=Image.new('RGBA',(W,H),(25,74,124,0)); d=ImageDraw.Draw(img)
    d.text((x+2,y+3),text,font=font,fill=(25,74,124,255))
    d.text((x,y),text,font=font,fill=(0,155,221,255))
    # subtle top highlight, clipped to the face
    face=Image.new('L',(W,H),0); fd=ImageDraw.Draw(face); fd.text((x,y),text,font=font,fill=255)
    hi=Image.new('RGBA',(W,H),(0,0,0,0)); hp=hi.load(); fp=face.load()
    for yy in range(H):
        a=max(0,min(160,int(160*(1-yy/16))))
        if not a: continue
        for xx in range(W):
            if fp[xx,yy]: hp[xx,yy]=(70,215,245,a)
    img=Image.alpha_composite(img,hi)

    # In-game result layout positions this texture against a fixed baseline.
    # DejaVu's cap body sits ~8 px lower than the official localized glyph art,
    # so translate the complete Turkish artwork upward before encoding.
    shift_y=-6
    aligned=Image.new('RGBA',(W,H),(0,0,0,0))
    aligned.alpha_composite(img,(0,shift_y))
    img=aligned
    img.save(OUT/'TEBRİKLER_font.png')

    # Official EURes/IT result masks are a shifted strip of the font alpha,
    # not a full letter silhouette. Empirically: x -2, y -26.
    alpha=img.getchannel('A')
    ma=Image.new('L',(W,H),0)
    ma.paste(alpha.crop((2,26,W,H)),(0,0))
    m=Image.new('RGBA',(W,H),(255,255,255,0)); m.putalpha(ma)
    m.save(OUT/'TEBRİKLER_mask.png')

if __name__=='__main__':
    make_start_clear();make_map();make_congrats();print(OUT)
