import sys, os
sys.path.insert(0, '/workspace/tools')
import seer
import UnityPy

src = '/tmp/p113/orig/peticon_assets_all_051ca4e72be71ecbb6da4b41b3d7a753.bundle'
plain, salt = seer.decrypt(src)
open('/tmp/p113/peticon_orig.plain', 'wb').write(plain)
print('plain', len(plain))

env = UnityPy.load('/tmp/p113/peticon_orig.plain')
print(env)
counts = {}
sprites = []
for obj in env.objects:
    t = obj.type.name
    counts[t] = counts.get(t, 0) + 1
    if t == 'Sprite':
        s = obj.read()
        sprites.append(s)
print(counts)
print('sprites', len(sprites))
for s in sprites:
    if s.m_Name in ('5000', '3577', '3188', '4007'):
        print(s.m_Name, 'rect', s.m_Rect, 'rdkey', s.m_RenderDataKey)
atlas = [o.read() for o in env.objects if o.type.name == 'SpriteAtlas']
for a in atlas:
    print('atlas', a.m_Name)
    for k, v in a.m_RenderDataMap:
        print(' key', k, 'tex', v.texture, 'rect', v.textureRect, 'offset', v.offset, 'scale', v.scale)
        break
