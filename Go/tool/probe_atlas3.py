import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
env = UnityPy.load('/tmp/fight.plain')
for o in env.objects:
    if o.type.name != 'SpriteAtlas':
        continue
    a = o.read()
    if a.m_Name != 'PetFightIcon':
        continue
    for so in env.objects:
        if so.type.name != 'Sprite':
            continue
        s = so.read()
        if s.m_Name != '3577':
            continue
        d = next(v for k, v in a.m_RenderDataMap if k == s.m_RenderDataKey)
        print('render data', d)
        tex = d.texture.read()
        print('tex', tex.m_Name, tex.m_Width, tex.m_Height, tex.m_TextureFormat,
              'stream', d.texture.m_PathID, int(tex.m_StreamData.offset), int(tex.m_StreamData.size), tex.m_StreamData.path)
        print('url', tex.m_StreamData.path)
        break
    break
