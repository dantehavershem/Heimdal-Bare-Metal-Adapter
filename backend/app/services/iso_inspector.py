from __future__ import annotations
import pathlib, struct
SECTOR=2048
class IsoError(Exception): pass

def le32(b): return struct.unpack('<I', b)[0]
def read_sector(f,lba):
    f.seek(lba*SECTOR); d=f.read(SECTOR)
    if len(d)!=SECTOR: raise IsoError(f"short read at LBA {lba}")
    return d

def parse_dir_record(rec):
    if not rec or rec[0] < 34: return None
    extent=le32(rec[2:6]); size=le32(rec[10:14]); flags=rec[25]; nlen=rec[32]
    name=rec[33:33+nlen]
    if name==b'\x00': name='.'
    elif name==b'\x01': name='..'
    else:
        name=name.decode('ascii','replace').split(';',1)[0]
    return {'extent':extent,'size':size,'is_dir':bool(flags&2),'name':name}

def read_dir(f,extent,size):
    f.seek(extent*SECTOR); data=f.read(size); pos=0; out=[]
    while pos < len(data):
        ln=data[pos]
        if ln==0:
            pos=((pos//SECTOR)+1)*SECTOR; continue
        rec=parse_dir_record(data[pos:pos+ln]); pos+=ln
        if rec: out.append(rec)
    return out

def walk(f,extent,size,base='/',depth=0,max_depth=9):
    if depth>max_depth: return []
    paths=[]
    for e in read_dir(f,extent,size):
        if e['name'] in ('.','..'): continue
        p=(base.rstrip('/')+'/'+e['name']).upper(); paths.append((p,e))
        if e['is_dir']: paths.extend(walk(f,e['extent'],e['size'],p,depth+1,max_depth))
    return paths

def inspect(path: pathlib.Path):
    result={'file':str(path),'size':path.stat().st_size,'iso9660':False,'eltorito':False,
            'paths':{},'detected':{},'recommended_adapter':'unknown','evidence':[]}
    with path.open('rb') as f:
        root=None
        for lba in range(16,64):
            d=read_sector(f,lba)
            if d[1:6]!=b'CD001': continue
            typ=d[0]
            if typ==1:
                result['iso9660']=True; root=parse_dir_record(d[156:190]); result['volume_id']=d[40:72].decode('ascii','ignore').strip()
            elif typ==0 and d[7:39].rstrip(b'\x00 ').upper()==b'EL TORITO SPECIFICATION':
                result['eltorito']=True; result['boot_catalog_lba']=le32(d[71:75])
            elif typ==255: break
        if not root: return result
        pset={p for p,_ in walk(f,root['extent'],root['size'])}
        interesting=['/SETUP.EXE','/EFI/BOOT/BOOTX64.EFI','/EFI/BOOT/BOOTAA64.EFI','/CASPER/VMLINUZ','/CASPER/INITRD','/CASPER/INITRD.LZ','/BOOT/GRUB/GRUB.CFG','/ISOLINUX/ISOLINUX.CFG','/SOURCES/BOOT.WIM']
        result['paths']={p:True for p in interesting if p in pset}
        if '/SOURCES/BOOT.WIM' in pset:
            result['detected']['family']='windows'; result['evidence'].append('Windows boot.wim present')
        if '/CASPER/VMLINUZ' in pset and ('/CASPER/INITRD' in pset or '/CASPER/INITRD.LZ' in pset):
            result['detected'].update({'family':'linux','linux_layout':'casper','architecture':'x86_64'})
            result['recommended_adapter']='linux-kernel-initrd'; result['evidence'].append('Casper kernel and initrd present')
        elif '/EFI/BOOT/BOOTX64.EFI' in pset:
            result['detected']['architecture']='x86_64'; result['recommended_adapter']='uefi-chainload'; result['evidence'].append('Fallback x64 EFI loader present')
        elif '/EFI/BOOT/BOOTAA64.EFI' in pset:
            result['detected']['architecture']='aarch64'; result['recommended_adapter']='uefi-chainload'; result['evidence'].append('Fallback ARM64 EFI loader present')
        elif '/BOOT/GRUB/GRUB.CFG' in pset:
            result['recommended_adapter']='grub'; result['evidence'].append('GRUB config present')
        elif '/ISOLINUX/ISOLINUX.CFG' in pset:
            result['recommended_adapter']='isolinux'; result['evidence'].append('ISOLINUX config present')
        if result['eltorito']: result['evidence'].append('El Torito boot catalog present')
    return result
