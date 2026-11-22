import sys, os, math
sys.path.insert(0, '/workspace/tools')
import UnityPy
from PIL import Image, ImageFilter
UnityPy.config.FALLBACK_UNITY_VERSION = '5.6.7f1'

ICON = '/workspace/pdapp/assets/pets'
OUT = '/workspace/pdapp/assets/pets_big'
os.makedirs(OUT, exist_ok=True)

def mask_of(img, side=64):
    a = img.getchannel('A')
    bbox = a.getbbox()
    if not bbox:
        return None, None
    m = a.crop(bbox).point(lambda v: 1 if v >= 128 else 0)
    w, h = m.size
    s = side / float(max(w, h))
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    m = m.resize((nw, nh), Image.BILINEAR).point(lambda v: 1 if v >= 128 else 0)
    c = Image.new('L', (side, side), 0)
    c.paste(m, ((side - nw) // 2, (side - nh) // 2))
    return bbox, c

def iou(a, b):
    pa, pb = list(a.getdata()), list(b.getdata())
    inter = sum(1 for x, y in zip(pa, pb) if x and y)
    uni = sum(1 for x, y in zip(pa, pb) if x or y)
    return inter / float(max(1, uni))

env = UnityPy.load('/workspace/work/fight.plain')
icons = {}      # id -> Image (PetFightIcon)
others = {}     # id -> list of Image
for obj in env.objects:
    if obj.type.name != 'Sprite':
        continue
    s = obj.read()
    pid = s.m_Name.strip()
    if not pid.isdigit():
        continue
    try:
        im = s.image.convert('RGBA')
    except Exception:
        continue
    if 'PetFightIcon' in (s.m_AtlasTags or []):
        if pid not in icons or im.size[0] * im.size[1] > icons[pid].size[0] * icons[pid].size[1]:
            icons[pid] = im
    else:
        others.setdefault(pid, []).append(im)

ids = sorted(set(icons) | set(others), key=lambda x: int(x))
used_icon = used_iou = 0
for pid in ids:
    img = None
    if pid in icons:
        img = icons[pid]
        used_icon += 1
    else:
        # 极少数 ID 在 fight 包中只有特效/UI 图，没有身体：直接用小头像素材，不猜测
        ip = os.path.join(ICON, pid + '.webp')
        if not os.path.exists(ip):
            continue
        img = Image.open(ip).convert('RGBA')
        used_iou += 1
    a = img.getchannel('A')
    bbox = a.getbbox()
    if not bbox:
        continue
    im = img.crop(bbox)
    w, h = im.size
    m = max(w, h)
    target = 156
    if m < target:
        sc = target / float(m)
        nw, nh = int(round(w * sc)), int(round(h * sc))
        up = im.resize((nw, nh), Image.LANCZOS)
        # 轻度锐化补偿放大后的模糊
        rgb = up.convert('RGB').filter(ImageFilter.UnsharpMask(radius=1.2, percent=140, threshold=2))
        im = Image.merge('RGBA', rgb.split() + (up.getchannel('A'),))
    elif m > 240:
        sc = 240 / float(m)
        im = im.resize((int(round(w * sc)), int(round(h * sc))), Image.LANCZOS)
    im.save(os.path.join(OUT, pid + '.webp'), 'WEBP', quality=80, method=4)
print('total', len(ids), 'by_tag', used_icon, 'by_iou', used_iou)
