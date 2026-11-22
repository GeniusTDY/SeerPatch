"""High-res portraits from per-pet fight<id> bundles.

usage: python extract_hires.py <KEY_HEX> <OUT_DIR> [start] [end]
"""
import sys, os, re, zipfile, json, io
import UnityPy
from PIL import Image
import seer

UnityPy.config.FALLBACK_UNITY_VERSION = '5.6.7f1'

APK = '/workspace/Seer_patched_signed.apk'
ICON = '/workspace/pdapp/assets/pets'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/workspace/work/hires'
START = int(sys.argv[3]) if len(sys.argv) > 3 else 0
END = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9

key = bytes.fromhex(sys.argv[1])
UnityPy.set_assetbundle_decrypt_key(key)
os.makedirs(OUT, exist_ok=True)

zf = zipfile.ZipFile(APK)
bymap = {}
for n in zf.namelist():
    m = re.search(r'/fight(\d+)_assets_all_', n)
    if m:
        bymap[int(m.group(1))] = n


def stat(img):
    a = img.getchannel('A')
    b = a.getbbox()
    if not b:
        return None
    hist = a.histogram()
    opaque = sum(hist[250:])
    bw, bh = b[2] - b[0], b[3] - b[1]
    return opaque / float(max(1, bw * bh))


def pick(env):
    best_tag = None
    best_big = None
    for o in env.objects:
        if o.type.name != 'Sprite':
            continue
        s = o.read()
        if 'PetFightIcon' in (s.m_AtlasTags or []):
            im = s.image.convert('RGBA')
            if best_tag is None or im.size[0] * im.size[1] > best_tag[0]:
                best_tag = (im.size[0] * im.size[1], im)
            continue
        try:
            im = s.image.convert('RGBA')
        except Exception:
            continue
        f = stat(im)
        if f is None or f < 0.35:
            continue
        area = im.size[0] * im.size[1]
        if best_big is None or area > best_big[0]:
            best_big = (area, im)
    # 优先大图本体；退回官方战斗小图
    if best_big is not None and best_big[0] > 200 * 200:
        return best_big[1]
    if best_tag is not None:
        return best_tag[1]
    return best_big[1] if best_big else None


done = 0
for pid in sorted(bymap):
    if pid < START or pid >= END:
        continue
    try:
        raw = zf.read(bymap[pid])
        plain, _ = seer.decrypt_bytes(raw)
        env = UnityPy.load(plain)
        im = pick(env)
        if im is None:
            print('skip', pid, 'no sprite', flush=True)
            continue
        a = im.getchannel('A')
        b = a.getbbox()
        im = im.crop(b)
        w, h = im.size
        m = max(w, h)
        if m > 240:
            s = 240.0 / m
            im = im.resize((max(1, int(round(w * s))), max(1, int(round(h * s)))), Image.LANCZOS)
        im.save(os.path.join(OUT, '%d.webp' % pid), 'WEBP', quality=80, method=4)
        done += 1
        if done % 25 == 0:
            print('done', done, 'last', pid, flush=True)
    except Exception as e:
        print('ERR', pid, type(e).__name__, str(e)[:120], flush=True)

print('finished', done, flush=True)
