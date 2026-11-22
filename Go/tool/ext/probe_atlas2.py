import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
env = UnityPy.load('/tmp/fight.plain')
for o in env.objects:
    if o.type.name != 'SpriteAtlas':
        continue
    a = o.read()
    if a.m_Name != 'PetFightIcon':
        continue
    names = list(a.m_PackedSpriteNamesToIndex)
    idx = names.index('3577')
    print('idx', idx, 'packed len', len(a.m_PackedSprites))
    pp = a.m_PackedSprites[idx]
    print('pptr', pp, 'pathid', pp.m_PathID)
    for pair in a.m_RenderDataMap:
        k, v = pair
        if k[1] == pp.m_PathID:
            print('renderdata', v)
            tex = v.texture.read()
            print('tex', tex.m_Name, tex.m_Width, tex.m_Height, tex.m_TextureFormat)
            sd = tex.m_StreamData
            print('stream', sd.path, int(sd.offset), int(sd.size))
            break
