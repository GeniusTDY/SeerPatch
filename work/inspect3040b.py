import sys, collections
sys.path.insert(0,'/workspace/tools'); sys.path.insert(0,'/workspace/tools/ext/unitypy-1.23.0')
import warnings; warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION='2022.3.62f3'
env=UnityPy.load('/workspace/work/fight3041_v9.plain')
objs=list(env.objects)
for o in objs:
    if o.type.name=='AnimationClip':
        t=o.read_typetree()
        print('=== CLIP',o.path_id,t['m_Name'],'keys:',list(t.keys()))
        print('  curves float',len(t['m_FloatCurves']),'pptr',len(t['m_PPtrCurves']),'events',len(t.get('m_Events',[])))
        print('  sampleRate',t.get('m_SampleRate'),'animCompression',t.get('m_AnimationClipSettings',{}))
        for pc in t['m_PPtrCurves']:
            print('   pptr path',pc.get('path'),'attr',pc.get('attribute'),'classID',pc.get('classID'),'nkeys',len(pc.get('curve',[])))
            for k in pc.get('curve',[])[:200]:
                print('     t',k['time'],'pid',k['value']['m_PathID'])
        for fc in t['m_FloatCurves'][:10]:
            print('   float',fc.get('path'),fc.get('attribute'),len(fc.get('curve',{}).get('m_Curve',[])))
    if o.type.name=='Sprite':
        t=o.read_typetree()
        print('SPR',o.path_id,repr(t['m_Name']),'rect',t['m_Rect'],'pivot',t['m_Pivot'],'tex',t['m_RD']['texture']['m_PathID'])
