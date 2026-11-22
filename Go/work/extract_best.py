"""Combine PetIconBig (peticon) and PetFightIcon (fight) per pet, keep the larger native art."""
import sys, os
sys.path.insert(0, '/workspace/tools')
import UnityPy
from PIL import Image, ImageFilter
UnityPy.config.FALLBACK_UNITY_VERSION = '5.6.7f1'

OUT = '/workspace/pdapp/assets/pets_big'
os.makedirs(OUT, exist_ok=True)

small = {}   # id -> (area, Image)  PetFightIcon
big = {}     # id -> (area, Image)  PetIconBig


def collect(path, tag, store):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name != 'Sprite':
            continue
        s = o.read()
        pid = s.m_Name.strip()
        if not pid.isdigit():
            continue
        if tag not in (s.m_AtlasTags or []):
            continue
        try:
            im = s.image.convert('RGBA')
        except Exception:
            continue
        a = im.getchannel('A').getbbox()
        if not a:
            continue
        im = im.crop(a)
        area = im.size[0] * im.size[1]
        cur = store.get(pid)
        if cur is None or area > cur[0]:
            store[pid] = (area, im)


collect('/workspace/work/fight.plain', 'PetFightIcon', small)
collect('/workspace/work/pic.plain', 'PetIconBig', big)

ids = sorted(set(small) | set(big), key=int)
from_big = from_small = upscaled = 0
for pid in ids:
    a = small.get(pid)
    b = big.get(pid)
    if b and (a is None or b[0] > a[0] * 1.15):
        im = b[1]
        from_big += 1
    elif a:
        im = a[1]
        from_small += 1
    else:
        im = b[1]
        from_big += 1
    w, h = im.size
    m = max(w, h)
    if m > 240:
        s = 240.0 / m
        im = im.resize((max(1, int(round(w * s))), max(1, int(round(h * s)))), Image.LANCZOS)
    elif m < 170:
        s = 170.0 / m
        up = im.resize((max(1, int(round(w * s))), max(1, int(round(h * s)))), Image.LANCZOS)
        rgb = up.convert('RGB').filter(ImageFilter.UnsharpMask(radius=1.0, percent=110, threshold=2))
        im = Image.merge('RGBA', rgb.split() + (up.getchannel('A'),))
        upscaled += 1
    im.save(os.path.join(OUT, pid + '.webp'), 'WEBP', quality=82, method=4)
print('total', len(ids), 'from_big', from_big, 'from_small', from_small, 'upscaled', upscaled)
