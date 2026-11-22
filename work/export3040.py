import sys, os, json
sys.path.insert(0,'/workspace/tools'); sys.path.insert(0,'/workspace/tools/ext/unitypy-1.23.0')
import warnings; warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION='2022.3.62f3'
from PIL import Image
env=UnityPy.load('/workspace/work/fight3041_v9.plain')
objs=list(env.objects)
texs={o.path_id:o for o in objs if o.type.name=='Texture2D'}
os.makedirs('/workspace/work/inspect_img/tex3040',exist_ok=True)
# clip -> sprites order
for o in objs:
    if o.type.name=='AnimationClip':
        t=o.read_typetree()
        name=t['m_Name']
        pptr=t['m_ClipBindingConstant']['pptrCurveMapping']
        print('clip',name,'frames',len(pptr))
        if name in ('3041_1','3041_2'):
            for i,p in enumerate(pptr[:6] if name=='3041_1' else pptr[:3]):
                pid=p['m_PathID']
                sp=[x for x in objs if x.path_id==pid][0]
                st=sp.read_typetree()
                tex=texs[st['m_RD']['texture']['m_PathID']]
                img=tex.image
                out=f'/workspace/work/inspect_img/tex3040/{name}_{i+1}_{tex.path_id}.png'
                img.save(out)
                print('saved',out,img.size)
