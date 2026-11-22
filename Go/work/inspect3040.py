import sys, json, collections
sys.path.insert(0,'/workspace/tools'); sys.path.insert(0,'/workspace/tools/ext/unitypy-1.23.0')
import warnings; warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION='2022.3.62f3'
p=sys.argv[1] if len(sys.argv)>1 else '/workspace/work/fight3041_v9.plain'
env=UnityPy.load(p)
objs=list(env.objects)
print('objects',len(objs))
c=collections.Counter(o.type.name for o in objs)
print(c)
for o in objs:
    if o.type.name=='AssetBundle':
        t=o.read_typetree()
        print('AB',t['m_Name'],'|',t['m_AssetBundleName'],'|deps',t['m_Dependencies'])
        print('container',[x for x,_ in t['m_Container']])
    if o.type.name=='AnimationClip':
        t=o.read_typetree()
        print('CLIP',o.path_id,t['m_Name'],'legacy',t.get('m_Legacy'),'curves',len(t['m_FloatCurves']),'pptr',len(t['m_PPtrCurves']),'sampleRate',t['m_SampleRate'],'range',t['m_StartTime'],t['m_StopTime'])
    if o.type.name=='Texture2D':
        t=o.read_typetree()
        print('TEX',o.path_id,t['m_Name'],t['m_Width'],'x',t['m_Height'],'fmt',t['m_TextureFormat'],'size',t['m_CompleteImageSize'],'stream',t['m_StreamData'].get('size'))
    if o.type.name=='TextAsset':
        t=o.read_typetree(); print('TEXT',o.path_id,t['m_Name'],len(t['m_Script']))
    if o.type.name in ('GameObject','MonoBehaviour','Mesh','Material'):
        pass
sp=[o for o in objs if o.type.name=='Sprite']
print('sprites',len(sp))
for o in sp[:15]:
    t=o.read_typetree()
    print('SPR',o.path_id,t['m_Name'],t['m_Rect'],'tex',t['m_RD']['texture']['m_PathID'])
