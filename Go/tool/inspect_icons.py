import sys, os
sys.path.insert(0, '/workspace/tools')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2021.3.16f1'

env = UnityPy.load('/tmp/p113/peticon_orig.plain')
atlas = None
for o in env.objects:
    if o.type.name == 'SpriteAtlas':
        atlas = o.read()
rdm = dict(atlas.m_RenderDataMap)
texobj = {o.path_id: o for o in env.objects if o.type.name == 'Texture2D'}
texmap = {pid: o.read().m_Name for pid, o in texobj.items()}
print('textures', texmap)
print('renderdata entries', len(rdm))

os.makedirs('/tmp/p113/icons', exist_ok=True)
rows = []
for o in env.objects:
    if o.type.name != 'Sprite':
        continue
    s = o.read()
    rd = rdm.get(s.m_RenderDataKey)
    if rd is None:
        rows.append((s.m_Name, s.m_Rect.width, s.m_Rect.height, None, None))
        continue
    r = rd.textureRect
    pid = rd.texture.path_id if hasattr(rd.texture, 'path_id') else None
    page = texmap.get(pid, '?')
    rows.append((s.m_Name, s.m_Rect.width, s.m_Rect.height, (r.width, r.height), page))
    if s.m_Name in ('5000', '3577', '855', '776', '70', '3438'):
        img = s.image
        img.save(f'/tmp/p113/icons/{s.m_Name}.png')
        bb = img.getchannel('A').getbbox()
        print('SPRITE', s.m_Name, 'rect', (round(s.m_Rect.width), round(s.m_Rect.height)),
              'texrect', (round(r.width), round(r.height)), 'page', page,
              'img', img.size, 'alphabbox', bb)

from collections import Counter
c = Counter((round(rw), round(rh)) for n, rw, rh, tr, pg in rows)
print('most common rects:')
for k, v in c.most_common(10):
    print(k, v)
print('5000/3577:', [(n, tr, pg) for n, rw, rh, tr, pg in rows if n in ('5000', '3577')])
print('pages used:', Counter(pg for *_, pg in rows))
