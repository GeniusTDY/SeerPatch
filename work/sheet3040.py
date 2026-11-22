import sys, os
sys.path.insert(0,'/workspace/tools'); sys.path.insert(0,'/workspace/tools/ext/unitypy-1.23.0')
import warnings; warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION='2022.3.62f3'
from PIL import Image
env=UnityPy.load('/workspace/work/fight3041_v9.plain')
objs=list(env.objects)
texs={o.path_id:o for o in objs if o.type.name=='Texture2D'}
byid={o.path_id:o for o in objs}
imgs=[]
for o in objs:
    if o.type.name=='AnimationClip':
        t=o.read_typetree(); name=t['m_Name']; pptr=t['m_ClipBindingConstant']['pptrCurveMapping']
        sel=[0,1,2,len(pptr)//2,len(pptr)-1] if len(pptr)>5 else range(len(pptr))
        for i in sel:
            sp=byid[pptr[i]['m_PathID']]; st=sp.read_typetree()
            tex=texs[st['m_RD']['texture']['m_PathID']]
            im=tex.read().image.convert('RGBA')
            im.thumbnail((300,300))
            imgs.append((f'{name}#{i+1}',im))
W=310*5; H=320*((len(imgs)+4)//5)
sheet=Image.new('RGBA',(W,H),(30,30,30,255))
from PIL import ImageDraw
d=ImageDraw.Draw(sheet)
for i,(label,im) in enumerate(imgs):
    x=(i%5)*310; y=(i//5)*320
    sheet.alpha_composite(im,(x+5,y+18))
    d.text((x+5,y+2),label,fill=(255,255,0,255))
sheet.save('/workspace/work/inspect_img/sheet3040.png')
print('saved',sheet.size,len(imgs))
