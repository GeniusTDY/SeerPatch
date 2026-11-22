import sys, os, json, struct, base64, hashlib, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0,'/workspace/tools'); sys.path.insert(0,'/workspace/tools/ext/unitypy-1.23.0')
import UnityPy, seer
UnityPy.config.FALLBACK_UNITY_VERSION='2022.3.62f3'

ROOT='/workspace/patch_v1.1.31'
AND=ROOT+'/assets/aa/Android'
fails=[]
def chk(cond,msg):
    if not cond: fails.append(msg); print('FAIL',msg)

def load_enc(p):
    raw=open(p,'rb').read()
    plain,salt=seer.decrypt_bytes(raw)
    assert plain[:7]==b'UnityFS', plain[:16]
    return raw,plain,salt

def walk_pptrs(node, path, out):
    if isinstance(node,dict):
        if 'm_FileID' in node and 'm_PathID' in node and len(node)==2:
            out.append((path,node['m_FileID'],node['m_PathID'])); return
        for k,v in node.items(): walk_pptrs(v,path+'/'+str(k),out)
    elif isinstance(node,list):
        for i,v in enumerate(node): walk_pptrs(v,path+'[%d]'%i,out)

def audit_bundle(p):
    name=os.path.basename(p)
    raw,plain,salt=load_enc(p)
    env=UnityPy.load(plain)
    bf=env.files[list(env.files.keys())[0]]
    sfs=[k for k in bf.files if not k.endswith('.resS')]
    chk(len(sfs)==1,(name,'serialized file count %d'%len(sfs)))
    sf=bf.files[sfs[0]]
    pids=list(sf.objects.keys())
    chk(pids==sorted(pids),(name,'object table not ascending'))
    resS=[k for k in bf.files if k.endswith('.resS')]
    ab=[o for o in sf.objects.values() if o.type.name=='AssetBundle']
    chk(len(ab)==1,(name,'AB count %d'%len(ab)))
    at=ab[0].read_typetree() if ab else {'m_PreloadTable':[],'m_Container':[]}
    # PPtr check
    bad=[]
    for o in sf.objects.values():
        try: tt=o.read_typetree()
        except Exception as e: bad.append((o.path_id,'read',str(e))); continue
        refs=[]; walk_pptrs(tt,'',refs)
        for path,fid,pid in refs:
            if fid==0 and pid!=0 and pid not in sf.objects:
                bad.append((o.path_id,path,pid))
    chk(not bad,(name,'unresolved PPtrs %r'%bad[:3]))
    chk(all(x['m_PathID'] in sf.objects or x['m_PathID']==0 for x in at['m_PreloadTable']),
        (name,'preload unresolved'))
    chk((name, sum(1 for x in at['m_Container'] if x[1]['asset']['m_PathID'] not in sf.objects and x[1]['asset']['m_PathID']!=0))==(name,0),
        (name,'container unresolved'))
    return dict(name=name,raw=raw,plain=plain,sf=sf,ab=at,resS=resS,nobj=len(pids),salt=salt)

print('=== bundles ===')
info={}
for f in sorted(os.listdir(AND)):
    p=AND+'/'+f
    r=audit_bundle(p)
    info[f]=r
    print('%-58s objs=%3d resS=%d salt=%s' % (f[:58], r['nobj'], len(r['resS']), r['salt'].hex()[:8]))

# fight 3042/3043 细节
for pid in ('3042','3043'):
    f=[k for k in info if k.startswith('fight%s_'%pid)][0]
    sf=info[f]['sf']; at=info[f]['ab']
    chk(len(info[f]['resS'])==0,(f,'still has .resS'))
    trims={}
    anims=[]
    bad=0
    for o in sf.objects.values():
        if o.type.name=='TextAsset':
            t=o.read_typetree()
            if t['m_Name'].endswith('.trim'):
                js=json.loads(t['m_Script'].lstrip('\ufeff'))
                trims[js['animKey']]=js
        elif o.type.name=='AnimationClip':
            anims.append(o.read_typetree()['m_Name'])
    chk(sorted(anims)==sorted(['%s_%d'%(pid,n) for n in (1,2,3,4)]),(f,'anims %r'%anims))
    chk(sorted(trims)==sorted(['%s_%d'%(pid,n) for n in (1,2,3,4)]),(f,'trims %r'%sorted(trims)))
    want={'1':21,'2':88,'3':53,'4':56}
    for k,js in trims.items():
        n=k.split('_')[1]
        chk(js['frameCount']==want[n] and len(js['frames'])==want[n],(f,k,'frameCount %s'%js['frameCount']))
        f0=js['frames'][0]
        chk(all(fr['spriteName'].isdigit() for fr in js['frames']),(f,k,'spriteName'))
        if n=='1':
            chk(all(fr['sourceW']==586 and fr['sourceH']==625 for fr in js['frames']),(f,k,'idle dims'))
    # container 8 条
    chk(len(at['m_Container'])==8,(f,'container %d'%len(at['m_Container'])))
    # sprite/texture 解码
    nsp=ntx=0; empty=[]
    for o in sf.objects.values():
        if o.type.name=='Sprite':
            nsp+=1
            try:
                im=o.read().image
                if im is None or im.getbbox() is None: empty.append(o.read_typetree()['m_Name'])
            except Exception as e: empty.append('ERR:'+str(e))
        elif o.type.name=='Texture2D': ntx+=1
    chk(not empty,(f,'empty sprites %r'%empty))
    print('%s: sprites=%d textures=%d trims=%s' % (pid,nsp,ntx,{k:v['frameCount'] for k,v in sorted(trims.items())}))

# pettypebig atlas
f=[k for k in info if k.startswith('pettypebig_')][0]
sf=info[f]['sf']
atl=[o for o in sf.objects.values() if o.type.name=='SpriteAtlas'][0].read_typetree()
names=atl['m_PackedSpriteNamesToIndex']
chk(len(atl['m_PackedSprites'])==len(names)==len(atl['m_RenderDataMap'])==63,(f,'atlas counts'))
for x in ('30','59','69'):
    chk(x in names,(f,'missing type icon '+x))
    spr=[o for o in sf.objects.values() if o.type.name=='Sprite' and o.read_typetree()['m_Name']==x]
    chk(len(spr)==1,(f,'sprite count '+x))
    if spr:
        im=spr[0].read().image
        chk(im is not None and im.getbbox() is not None,(f,'icon empty '+x))
        print('type %s bbox %s size %s' % (x, im.getbbox(), im.size))
print('pettypebig: objects=%d atlas=%d' % (info[f]['nobj'], len(names)))

# catalog 一致性
print('=== catalog ===')
CAT=ROOT+'/assets/aa/catalog.json'
d=json.load(open(CAT,encoding='utf-8'))
kb=base64.b64decode(d['m_KeyDataString']); bb=base64.b64decode(d['m_BucketDataString'])
eb=base64.b64decode(d['m_EntryDataString']); xb=base64.b64decode(d['m_ExtraDataString'])
nk=struct.unpack('<i',kb[:4])[0]; nb=struct.unpack('<i',bb[:4])[0]; ne=struct.unpack('<i',eb[:4])[0]
def parse_key(kb,off):
    t=kb[off]
    if t==0:
        n=struct.unpack('<i',kb[off+1:off+5])[0]; return kb[off+5:off+5+n].decode('ascii'),off+5+n
    if t==1:
        n=struct.unpack('<i',kb[off+1:off+5])[0]; return kb[off+5:off+5+n].decode('utf-16le'),off+5+n
    if t==2: return struct.unpack('<H',kb[off+1:off+3])[0],off+3
    if t==3: return struct.unpack('<I',kb[off+1:off+5])[0],off+5
    if t==4: return struct.unpack('<i',kb[off+1:off+5])[0],off+5
    if t==5:
        n=kb[off+1]; return kb[off+2:off+2+n].decode('ascii'),off+2+n
    if t==6:
        n=kb[off+1]; return ('type',kb[off+2:off+2+n]),off+2+n
    if t==7:
        a=kb[off+1]; p=off+2+a; c=kb[p]; p=p+1+c; n=struct.unpack('<i',kb[p:p+4])[0]
        return json.loads(kb[p+4:p+4+n].decode('utf-16le')),p+4+n
    raise SystemExit('bad key')
keys=[]; p=4; off2i={}
for i in range(nk):
    o=p; k,p=parse_key(kb,p); keys.append(k); off2i[o]=i
chk(p==len(kb),'key blob trailing')
chk((nk,nb,ne)==(23789,23789,14397),(nk,nb,ne))
chk(len(d['m_InternalIds'])==13072,len(d['m_InternalIds']))
q=4; buckets=[]
for _ in range(nb):
    off=struct.unpack('<i',bb[q:q+4])[0]; c=struct.unpack('<i',bb[q+4:q+8])[0]
    ents=struct.unpack('<%di'%c,bb[q+8:q+8+4*c]) if c else ()
    buckets.append((off,ents)); q+=8+4*c
chk(q==len(bb),'bucket trailing')
rows=[struct.unpack('<7i',eb[4+i*28:4+(i+1)*28]) for i in range(ne)]
chk(len(eb)==4+28*ne,'entry blob size')

# 所有 bundle key 指向存在的文件
bundles=[k for k in keys if isinstance(k,str) and k.endswith('.bundle')]
missing=[b for b in bundles if not os.path.exists(AND+'/'+b)]
chk(not missing,'missing bundle files %r'%missing[:5])
print('bundle keys',len(bundles),'all present',not missing)

for pid in ('3042','3043'):
    f='fight%s_assets_all_%s.bundle'%(pid,hashlib.md5(('seer-fight-%s-v1.1.31'%pid).encode()).hexdigest())
    chk(f in keys,'catalog missing bundle key '+f)
    chk(os.path.exists(AND+'/'+f),'file missing '+f)
    # extra 大小
    ei=[i for i,(o,e) in enumerate(buckets) if keys[off2i[o]]==f][0]
    for e in buckets[ei][1]:
        r=rows[e]
        p=xb[r[4]+1]; a=xb[r[4]+1+p] if False else None
    # 解 extra
    off=rows[buckets[ei][1][0]][4]
    assert xb[off]==7
    pp=off+1; a=xb[pp]; pp+=1+a; c=xb[pp]; pp+=1+c; n=struct.unpack('<i',xb[pp:pp+4])[0]; pp+=4
    js=json.loads(xb[pp:pp+n].decode('utf-16le'))
    chk(js['m_BundleSize']==info[f]['plain'].__len__(),(f,'bundleSize %d vs %d'%(js['m_BundleSize'],len(info[f]['plain']))))
    chk(js['m_Hash']==f.split('_')[-1][:-7],(f,'hash mismatch'))
    # 4 动画 key + 待机 trim key 存在
    for path in ['Assets/PetAnimation/FightAnimation/%s/%s_%d.anim'%(pid,pid,n) for n in (1,2,3,4)]:
        chk(path in keys,'missing anim key '+path)
    chk('FightAnimTrim/%s_1'%pid in keys,'missing idle trim key '+pid)
    # trim entry 指向 bundle key/index
    print('%s catalog ok, bundleSize=%d'%(pid,js['m_BundleSize']))

print()
print('FAILS',len(fails))
for x in fails: print(' -',x)
