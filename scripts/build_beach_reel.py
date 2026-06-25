#!/usr/bin/env python3
# Summer Christmas beach-drive — 20s rough assemblies (V1 montage / V2 map-spine)
import subprocess, os, math, shutil
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont

SRC = Path("/Users/jean/Documents/Today's stroll/SummerChristmas")
WORK = Path("/tmp/sc_build")
SEG = WORK/"seg"; PREP = WORK/"prep"; MAPF = WORK/"mapf"; TXT = WORK/"txt"
for d in (WORK, SEG, PREP, MAPF, TXT): d.mkdir(parents=True, exist_ok=True)
OUT = Path("/Users/jean/Documents/Claude/Projects/detailpage-gen/stroll/exports")

FONT_EN = "/System/Library/Fonts/Avenir Next.ttc"
FONT_KR = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
GRADE = "eq=contrast=1.07:saturation=1.14:gamma=1.03,colorbalance=rm=0.05:gm=0.01:bm=-0.05"
W, H, FPS = 1080, 1920, 30

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FFMPEG ERR:", " ".join(str(c) for c in cmd[:8]), "...\n", r.stderr[-700:])
        raise SystemExit(1)

def font(size, kr=False):
    try: return ImageFont.truetype(FONT_KR if kr else FONT_EN, size)
    except: return ImageFont.load_default()

def prep_photo(name):
    out = PREP/name
    if not out.exists():
        Image.fromarray(__import__("numpy").asarray(ImageOps.exif_transpose(Image.open(SRC/name)).convert("RGB"))).save(out, quality=92) \
            if False else ImageOps.exif_transpose(Image.open(SRC/name)).convert("RGB").save(out, quality=92)
    return out

# ---------- text PNG (transparent, centered) ----------
def text_png(tag, lines):
    """lines: list of (txt, size, y_abs, color, kr)"""
    if not lines: return None
    p = TXT/f"{tag}.png"
    img = Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    for txt,size,y,color,kr in lines:
        f=font(size,kr)
        bb=d.textbbox((0,0),txt,font=f); tw=bb[2]-bb[0]
        x=(W-tw)//2 - bb[0]
        d.text((x+2,y+2),txt,font=f,fill=(0,0,0,150))   # shadow
        d.text((x,y),txt,font=f,fill=color)
    img.save(p); return p

def overlay_chain(dur, in_label="b", out_label="v"):
    return (f"[1:v]format=rgba,fade=in:st=0:d=0.25:alpha=1,"
            f"fade=out:st={max(0,dur-0.3):.2f}:d=0.3:alpha=1[t];[{in_label}][t]overlay=0:0[{out_label}]")

# ---------- segment builders ----------
def seg_video(idx, clip, ss, dur, tp=None):
    out=SEG/f"{idx:02d}.mp4"
    base=f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},{GRADE},setsar=1"
    if tp:
        fc=base+"[b];"+overlay_chain(dur)
        run(["ffmpeg","-y","-ss",str(ss),"-i",str(SRC/clip),"-loop","1","-i",str(tp),"-t",str(dur),"-an",
             "-filter_complex",fc,"-map","[v]","-c:v","libx264","-pix_fmt","yuv420p","-preset","veryfast","-r",str(FPS),str(out)])
    else:
        run(["ffmpeg","-y","-ss",str(ss),"-i",str(SRC/clip),"-t",str(dur),"-an",
             "-vf",base,"-c:v","libx264","-pix_fmt","yuv420p","-preset","veryfast","-r",str(FPS),str(out)])
    return out

def seg_hero(idx, clip, ss, src_dur, out_dur, tp=None):
    out=SEG/f"{idx:02d}.mp4"; speed=src_dur/out_dur
    base=(f"[0:v]split=2[bg][fg];"
          f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:4,eq=brightness=-0.06[bgb];"
          f"[fg]scale={W}:-2[fgs];"
          f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setpts={1/speed:.4f}*PTS,fps={FPS},{GRADE},setsar=1")
    if tp:
        fc=base+"[b];"+overlay_chain(out_dur)
        run(["ffmpeg","-y","-ss",str(ss),"-i",str(SRC/clip),"-loop","1","-i",str(tp),"-t",str(out_dur),"-an",
             "-filter_complex",fc,"-map","[v]","-c:v","libx264","-pix_fmt","yuv420p","-preset","veryfast","-r",str(FPS),str(out)])
    else:
        run(["ffmpeg","-y","-ss",str(ss),"-i",str(SRC/clip),"-t",str(out_dur),"-an",
             "-filter_complex",base+"[v]","-map","[v]","-c:v","libx264","-pix_fmt","yuv420p","-preset","veryfast","-r",str(FPS),str(out)])
    return out

def seg_photo(idx, name, dur, tp=None, z=0.0010):
    out=SEG/f"{idx:02d}.mp4"; p=prep_photo(name); frames=int(dur*FPS)
    base=(f"[0:v]scale={W*3//2}:{H*3//2}:force_original_aspect_ratio=increase,crop={W*3//2}:{H*3//2},"
          f"zoompan=z='min(zoom+{z},1.12)':d={frames}:s={W}x{H}:fps={FPS},{GRADE},setsar=1")
    if tp:
        fc=base+"[b];"+overlay_chain(dur)
        run(["ffmpeg","-y","-loop","1","-i",str(p),"-loop","1","-i",str(tp),"-t",str(dur),"-an",
             "-filter_complex",fc,"-map","[v]","-c:v","libx264","-pix_fmt","yuv420p","-preset","veryfast","-r",str(FPS),str(out)])
    else:
        run(["ffmpeg","-y","-loop","1","-i",str(p),"-t",str(dur),"-an",
             "-vf",base,"-c:v","libx264","-pix_fmt","yuv420p","-preset","veryfast","-r",str(FPS),str(out)])
    return out

# ---------- real-tile map (Carto voyager basemap + road-snapped route + car) ----------
import requests, math as _m, io, json
# drive: Mona Vale -> Bungan -> Newport (home photos deleted -> tighter zoom)
STOPS=[(-33.6790,151.3070,"Mona Vale"),(-33.6640,151.3140,"Bungan"),(-33.6557,151.3267,"Newport"),(-33.6357,151.3290,"Avalon"),(-33.5950,151.3243,"Palm Beach")]
TILE=512  # @2x carto tiles
def _gpx(lat,lon,z):
    n=2**z; x=(lon+180)/360*n*TILE
    lr=_m.radians(lat); y=(1-_m.log(_m.tan(lr)+1/_m.cos(lr))/_m.pi)/2*n*TILE
    return x,y
def _haversine(a,b):
    R=6371.0; la1,lo1=map(_m.radians,a); la2,lo2=map(_m.radians,b)
    h=_m.sin((la2-la1)/2)**2+_m.cos(la1)*_m.cos(la2)*_m.sin((lo2-lo1)/2)**2
    return 2*R*_m.asin(_m.sqrt(h))
# --- road-snapped polyline via OSRM (no key); fallback = straight stops ---
def fetch_route():
    cache=PREP/"route.json"
    if cache.exists(): return json.loads(cache.read_text())
    coords=";".join(f"{lo},{la}" for la,lo,_ in STOPS)
    url=f"https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"
    try:  # curl: local python SSL stack fails the OSRM TLS handshake
        raw=subprocess.run(["curl","-s","--max-time","20","-A","stroll/1.0",url],
                           capture_output=True,text=True).stdout
        r=json.loads(raw)
        line=[(c[1],c[0]) for c in r["routes"][0]["geometry"]["coordinates"]]
        km=r["routes"][0]["distance"]/1000.0
        out={"poly":line,"km":round(km,1)}
    except Exception as e:
        print("OSRM fail -> straight",e); out={"poly":[(la,lo) for la,lo,_ in STOPS],"km":None}
    cache.write_text(json.dumps(out)); return out
for _stale in (PREP/"route.json", PREP/"basemap.png"):  # invalidate cross-run cache
    if _stale.exists(): _stale.unlink()
ROUTE_DATA=fetch_route(); POLY=ROUTE_DATA["poly"]
KM=ROUTE_DATA["km"] or round(sum(_haversine(POLY[i-1],POLY[i]) for i in range(1,len(POLY))),1)
BASEMAP=PREP/"basemap.png"; PROJ={}
def build_basemap():
    lats=[p[0] for p in POLY]; lons=[p[1] for p in POLY]
    mlat=(max(lats)-min(lats))*0.16+0.003; mlon=(max(lons)-min(lons))*0.16+0.003
    la0,la1=min(lats)-mlat,max(lats)+mlat; lo0,lo1=min(lons)-mlon,max(lons)+mlon
    z=13
    for zz in range(16,9,-1):
        x0,_=_gpx(la0,lo0,zz); x1,_=_gpx(la0,lo1,zz)
        _,y0=_gpx(la1,lo0,zz); _,y1=_gpx(la0,lo0,zz)
        if abs(x1-x0)<=W and abs(y1-y0)<=H: z=zz; break
    cx=(_gpx(la0,lo0,z)[0]+_gpx(la0,lo1,z)[0])/2
    cy=(_gpx(la1,lo0,z)[1]+_gpx(la0,lo0,z)[1])/2
    ox=cx-W/2; oy=cy-H/2
    PROJ.update(z=z,ox=ox,oy=oy)
    if BASEMAP.exists(): return
    canvas=Image.new("RGB",(W,H),(232,232,228))
    tx0=int(ox//TILE); tx1=int((ox+W)//TILE); ty0=int(oy//TILE); ty1=int((oy+H)//TILE)
    sess=requests.Session()
    for tx in range(tx0,tx1+1):
        for ty in range(ty0,ty1+1):
            url=f"https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{tx}/{ty}@2x.png"
            try:
                r=sess.get(url,timeout=15,headers={"User-Agent":"stroll/1.0"})
                t=Image.open(io.BytesIO(r.content)).convert("RGB")
            except Exception as e:
                print("tile fail",tx,ty,e); t=Image.new("RGB",(TILE,TILE),(232,232,228))
            canvas.paste(t,(int(tx*TILE-ox),int(ty*TILE-oy)))
    from PIL import ImageEnhance
    canvas=ImageEnhance.Color(canvas).enhance(0.92)
    canvas=ImageEnhance.Brightness(canvas).enhance(1.02)
    canvas.save(BASEMAP)
def _cpx(lat,lon):
    gx,gy=_gpx(lat,lon,PROJ["z"]); return (gx-PROJ["ox"], gy-PROJ["oy"])
build_basemap()
PPX=[_cpx(la,lo) for la,lo in POLY]              # road polyline in canvas px
LENS=[0.0]
for i in range(1,len(PPX)): LENS.append(LENS[-1]+_m.dist(PPX[i-1],PPX[i]))
TOTAL=LENS[-1] or 1
STOPPX=[_cpx(la,lo) for la,lo,_ in STOPS]
def _at(frac):
    """return (point, heading_deg, index_into_PPX) at fractional distance along road"""
    d=max(0,min(1,frac))*TOTAL
    for i in range(1,len(PPX)):
        if d<=LENS[i] or i==len(PPX)-1:
            seg=LENS[i]-LENS[i-1]; t=0 if seg==0 else max(0,min(1,(d-LENS[i-1])/seg))
            x=PPX[i-1][0]+(PPX[i][0]-PPX[i-1][0])*t; y=PPX[i-1][1]+(PPX[i][1]-PPX[i-1][1])*t
            dx=PPX[i][0]-PPX[i-1][0]; dy=PPX[i][1]-PPX[i-1][1]
            hd=_m.degrees(_m.atan2(-dy,dx))-90
            return (x,y),hd,i
    return PPX[-1],0,len(PPX)-1
ROUTE=(238,108,54)   # warm coral
def _car_sprite():
    s=Image.new("RGBA",(58,104),(0,0,0,0)); d=ImageDraw.Draw(s)
    d.rounded_rectangle([12,8,46,96],radius=16,fill=ROUTE+(255,),outline=(255,255,255,255),width=4)
    d.rounded_rectangle([17,20,41,40],radius=7,fill=(255,255,255,235))   # windshield (front=top)
    d.rounded_rectangle([17,64,41,82],radius=7,fill=(255,255,255,150))   # rear window
    return s
CAR=_car_sprite()
def seg_map(idx, f0, f1, dur, label=None, final=False):
    out=SEG/f"{idx:02d}.mp4"; fdir=MAPF/f"m{idx}"
    if fdir.exists(): shutil.rmtree(fdir)
    fdir.mkdir(); n=max(1,int(dur*FPS))
    fL=font(46); fS=font(34); fLab=font(32)
    base=Image.open(BASEMAP).convert("RGB")
    for k in range(n):
        a=k/(n-1) if n>1 else 1; frac=f0+(f1-f0)*a
        img=base.copy(); d=ImageDraw.Draw(img,"RGBA")
        d.rectangle([0,0,W,150],fill=(0,0,0,70))
        d.rectangle([0,H-300,W,H],fill=(0,0,0,95))
        head,hd,i=_at(frac)
        pts=PPX[:i]+[head]
        if len(pts)>=2:
            d.line(pts,fill=(255,255,255,180),width=12,joint="curve")
            d.line(pts,fill=ROUTE+(255,),width=7,joint="curve")
        # stop dots reached so far
        reached=max(0,min(len(STOPS), int(round(frac*(len(STOPS)-1)))+1)) if frac>0 else 1
        for si in range(reached):
            px,py=STOPPX[si]
            d.ellipse([px-10,py-10,px+10,py+10],fill=(255,255,255),outline=ROUTE,width=4)
        # car at head
        car=CAR.rotate(hd,expand=True,resample=Image.BICUBIC)
        img.paste(car,(int(head[0]-car.width/2),int(head[1]-car.height/2)),car)
        if label: d.text((64,96),label,font=fL,fill=(255,255,255))
        if final:
            for (la,lo,nm),(px,py) in zip(STOPS,STOPPX):
                d.text((px+18,py-16),nm,font=fLab,fill=(255,255,255),
                       stroke_width=3,stroke_fill=(0,0,0,180))
            d.text((64,H-150),"SYDNEY · NORTHERN BEACHES",font=fS,fill=ROUTE+(255,))
            d.text((64,H-108),f"{len(STOPS)} stops · {KM} km · Dec 24",font=fL,fill=(255,255,255))
        img.convert("RGB").save(fdir/f"{k:04d}.png")
    run(["ffmpeg","-y","-framerate",str(FPS),"-i",str(fdir/"%04d.png"),"-t",str(dur),
         "-vf","setsar=1","-c:v","libx264","-pix_fmt","yuv420p","-preset","veryfast","-r",str(FPS),str(out)])
    return out

def concat(segs, outfile):
    lst=WORK/"list.txt"; lst.write_text("".join(f"file '{s}'\n" for s in segs))
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(lst),"-c:v","libx264",
         "-pix_fmt","yuv420p","-r",str(FPS),"-movflags","+faststart",str(outfile)])
    dur=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(outfile)],capture_output=True,text=True).stdout.strip()
    print(f"  -> {outfile.name}  ({dur}s)")

WHITE=(255,255,255,255); GOLD=(242,178,92,255)
# ===================== V1: cinematic montage (beach only) =====================
print("Building V1 (cinematic montage)...")
v1=[]; i=0
v1.append(seg_photo(i:=i+1,"20251224_122832.jpg",1.6,text_png("v1a",[("CHRISTMAS ON THE BEACH",50,int(H*0.44),WHITE,False),("Sydney · 32°",36,int(H*0.44)+78,GOLD,False)])))
v1.append(seg_map(i:=i+1,0.0,0.12,0.9,label="Dec 24"))
v1.append(seg_video(i:=i+1,"20251224_121214.mp4",2.0,1.1))
v1.append(seg_video(i:=i+1,"20251224_122655.mp4",4.0,0.9))
v1.append(seg_video(i:=i+1,"20251224_121824.mp4",4.0,0.9))
v1.append(seg_video(i:=i+1,"20251224_122341.mp4",10.0,0.8))
v1.append(seg_video(i:=i+1,"20251224_121515.mp4",3.0,0.8))
v1.append(seg_video(i:=i+1,"20251224_123322.mp4",2.0,0.8))
v1.append(seg_video(i:=i+1,"20251224_132144.mp4",2.0,0.8))
v1.append(seg_video(i:=i+1,"20251224_133114.mp4",1.5,0.7))
v1.append(seg_video(i:=i+1,"20251224_142049.mp4",1.0,0.7))
v1.append(seg_video(i:=i+1,"20251224_142208.mp4",3.0,1.1))
v1.append(seg_hero(i:=i+1,"20251224_143027.mp4",6.0,3.2,4.5,text_png("v1c",[("the longest day of summer",38,int(H*0.86),WHITE,False)])))
v1.append(seg_photo(i:=i+1,"20251224_143023.jpg",0.9))
v1.append(seg_map(i:=i+1,0.12,1.0,3.0,final=True))
v1.append(seg_photo(i:=i+1,"20251224_122833.jpg",1.3,text_png("v1end",[("하루 여행기",54,int(H*0.42),WHITE,True),("@graceandwhy.ai",38,int(H*0.42)+86,GOLD,False)])))
concat(v1, OUT/"summerchristmas-v1-montage.mp4")

# ===================== V2: map spine (beach only) =====================
print("Building V2 (map spine)...")
v2=[]; i=0
v2.append(seg_photo(i:=i+1,"20251224_122832.jpg",1.5,text_png("v2a",[("CHRISTMAS ON THE BEACH",50,int(H*0.44),WHITE,False)])))
v2.append(seg_map(i:=i+1,0.0,0.16,0.9,label="Mona Vale"))
v2.append(seg_video(i:=i+1,"20251224_121214.mp4",2.0,1.0))
v2.append(seg_video(i:=i+1,"20251224_122655.mp4",4.0,0.9))
v2.append(seg_map(i:=i+1,0.16,0.45,0.8))
v2.append(seg_video(i:=i+1,"20251224_121824.mp4",4.0,0.9))
v2.append(seg_video(i:=i+1,"20251224_122341.mp4",10.0,0.8))
v2.append(seg_map(i:=i+1,0.45,0.70,0.8))
v2.append(seg_video(i:=i+1,"20251224_132144.mp4",2.0,0.8))
v2.append(seg_video(i:=i+1,"20251224_133114.mp4",1.5,0.7))
v2.append(seg_map(i:=i+1,0.70,0.90,0.7))
v2.append(seg_video(i:=i+1,"20251224_142208.mp4",3.0,1.1))
v2.append(seg_hero(i:=i+1,"20251224_143027.mp4",6.0,3.2,4.5,text_png("v2c",[("the longest day of summer",38,int(H*0.86),WHITE,False)])))
v2.append(seg_map(i:=i+1,0.90,1.0,2.8,final=True))
concat(v2, OUT/"summerchristmas-v2-mapspine.mp4")
print("DONE")
