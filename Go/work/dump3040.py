import sys, json
sys.path.insert(0,'/workspace/tools'); sys.path.insert(0,'/workspace/tools/ext/unitypy-1.23.0')
import warnings; warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION='2022.3.62f3'
env=UnityPy.load('/workspace/work/fight3041_v9.plain')
objs=list(env.objects)
tex={}
for o in objs:
    if o.type.name=='Texture2D':
        t=o.read_typetree(); tex[o.path_id]=(t['m_Name'],t['m_Width'],t['m_Height'],t['m_TextureFormat'])
for o in objs:
    if o.type.name=='TextAsset':
        t=o.read_typetree()
        print('=== TEXT',t['m_Name'])
        s=t['m_Script']
        print(s[:1200])
    if o.type.name=='MonoScript':
        t=o.read_typetree(); print('MONO',t['m_ClassName'],t['m_Namespace'],t['m_AssemblyName'])
spr=[]
for o in objs:
    if o.type.name=='Sprite':
        t=o.read_typetree()
        nm,w,h,f=tex.get(t['m_RD']['texture']['m_PathID'],('?',0,0,0))
        spr.append((int(t['m_Name']) if t['m_Name'].isdigit() else -1, t['m_Name'], int(t['m_Rect']['width']), int(t['m_Rect']['height']), nm, w, h))
spr.sort()
print('total sprites',len(spr))
for s in spr[:40]: print('S',s)
print('...')
for s in spr[-20:]: print('S',s)
