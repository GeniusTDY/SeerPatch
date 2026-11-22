import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
env = UnityPy.load('/tmp/fight.plain')
for o in env.objects:
    if o.type.name == 'Sprite':
        s = o.read()
        if s.m_Name == '3577':
            print('rect', s.m_Rect, 'ppu', s.m_PixelsToUnits)
            rd = s.m_RD
            for a in [x for x in dir(rd) if not x.startswith('__')]:
                try:
                    v = getattr(rd, a)
                except Exception:
                    continue
                if not callable(v):
                    print(' ', a, v)
            print('atlas ref', s.m_SpriteAtlas)
            at = s.m_SpriteAtlas
            if at and at.m_PathID:
                a = at.read()
                print('atlas', a.m_Name, 'type', type(a))
                print('atlas attrs', [x for x in dir(a) if not x.startswith('__')][:30])
            img = s.image
            print('image', img.size)
            break
