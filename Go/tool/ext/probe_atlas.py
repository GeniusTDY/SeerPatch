import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
env = UnityPy.load('/tmp/fight.plain')
for o in env.objects:
    if o.type.name == 'SpriteAtlas':
        a = o.read()
        if a.m_Name != 'PetFightIcon':
            continue
        m = a.m_RenderDataMap
        print('map type', type(m), 'len', len(m))
        print('first entry type', type(m[0]), m[0])
        for pair in m:
            k, v = pair
            if k[1] == 5530600774423084396:
                print('found key', k)
                for x in [y for y in dir(v) if not y.startswith('__')]:
                    try:
                        val = getattr(v, x)
                    except Exception:
                        continue
                    if not callable(val):
                        print('   ', x, val)
                print('--- first entry for comparison ---')
                kk, vv = m[0]
                for x in [y for y in dir(vv) if not y.startswith('__')]:
                    try:
                        val = getattr(vv, x)
                    except Exception:
                        continue
                    if not callable(val):
                        print('   ', x, val)
                break
