#!/usr/bin/env python3
"""Create a separate verified AVX2 Ovis copy; never modify the source package.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import argparse, datetime, hashlib, json, os, pathlib, platform, shutil, stat, sys
BASE_MANIFEST = '385bed9caa5c868e82ed5325a0060f255602f27588b75511e7cb99674d1b03bb'
BACKEND_SHA = '2826d562a9e9bb51338a43104a952935dc802a5eb799f5e2cdf5d105cadd8d03'
REQUIRED = {'avx','avx2','fma','f16c','sse4_2','bmi2'}
GUARD = '''import pathlib, runpy, sys
required = {'avx','avx2','fma','f16c','sse4_2','bmi2'}
sets = [set(line.split(':',1)[1].split()) for line in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('flags') and ':' in line]
if not sets or any(not required.issubset(flags) for flags in sets):
    sys.exit('CPU lacks required AVX2/FMA/F16C/SSE4.2/BMI2 flags. Use the unchanged original package.')
runpy.run_path(str(pathlib.Path(__file__).resolve().with_name('launch.py')), run_name='__main__')
'''

def digest(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def safe_file(root, rel):
    q=pathlib.PurePosixPath(rel)
    if not rel or q.is_absolute() or '..' in q.parts or '\\' in rel:
        raise ValueError('Unsafe manifest path: '+rel)
    p=root
    for part in q.parts:
        p=p/part
        if p.is_symlink(): raise ValueError('Symlinks are not supported: '+rel)
    if not p.is_file(): raise ValueError('Missing file: '+rel)
    return p

def verify_source(src):
    mf=safe_file(src,'SHA256-MANIFEST.json')
    if digest(mf)!=BASE_MANIFEST: raise ValueError('This updater requires the exact original delivered manifest; source is not modified.')
    manifest=json.loads(mf.read_text())
    entries=manifest['files']; expected=set()
    for e in entries:
        rel=e['path']
        if rel in expected: raise ValueError('Duplicate manifest path')
        expected.add(rel); p=safe_file(src,rel)
        if p.stat().st_size!=e['bytes'] or digest(p)!=e['sha256']:
            raise ValueError('Original file changed: '+rel)
    for directory in ('bin','models','python','scripts'):
        for p in (src/directory).rglob('*'):
            if p.is_symlink() or p.is_file() and p.relative_to(src).as_posix() not in expected:
                raise ValueError('Unlisted runtime file: '+str(p))
    return manifest

def upgrade(src, dst, payload):
    if src.is_symlink(): raise ValueError('Source root must not be a symlink')
    src=src.resolve(strict=True)
    if dst.exists() or dst.is_symlink(): raise ValueError('Destination must not exist')
    parent=dst.parent.resolve(strict=True); dst=parent/dst.name
    if dst==src or src in dst.parents: raise ValueError('Destination must be outside original package')
    manifest=verify_source(src)
    backend=safe_file(payload,'libggml-cpu.so.0')
    if digest(backend)!=BACKEND_SHA: raise ValueError('Optimized backend checksum mismatch')
    needed=sum(e['bytes'] for e in manifest['files'])+backend.stat().st_size+32*1024*1024
    if shutil.disk_usage(parent).free<needed: raise ValueError('Insufficient free disk space for a complete separate copy')
    dst.mkdir() # exclusive reservation; no existing path is ever overwritten
    try:
        for e in manifest['files']:
            p=dst/e['path'];p.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(safe_file(src,e['path']),p)
        shutil.copy2(backend,dst/'bin/libggml-cpu.so.0')
        (dst/'cpu_guard.py').write_text(GUARD)
        receipt=payload/'BACKEND-VALIDATION.json'
        if receipt.is_file(): shutil.copy2(safe_file(payload,'BACKEND-VALIDATION.json'),dst/'BACKEND-VALIDATION.json')
        shell=(dst/'run.sh').read_text()
        if '"$ROOT/launch.py"' not in shell: raise ValueError('Unexpected original launcher')
        (dst/'run.sh').write_text(shell.replace('"$ROOT/launch.py"','"$ROOT/cpu_guard.py"'))
        (dst/'UPGRADE.json').write_text(json.dumps({'format':'ovis-avx2-upgrade/1','baseManifestSha256':BASE_MANIFEST,'backendSha256':BACKEND_SHA,'requiredCpuFlags':sorted(REQUIRED),'originalPreserved':True,'fullOcrSpeedMeasured':False},indent=2)+'\n')
        files=[]
        for p in sorted(dst.rglob('*')):
            if p.is_file(): files.append({'path':p.relative_to(dst).as_posix(),'bytes':p.stat().st_size,'mode':format(stat.S_IMODE(p.stat().st_mode),'04o'),'sha256':digest(p)})
        manifest.update(package='ovis-offline-arch-x86_64-avx2',createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,totalBytes=sum(e['bytes'] for e in files))
        manifest['verification']={'separateCopy':True,'allBytesHashed':True,'originalManifestSha256':BASE_MANIFEST,'fullOcrAccuracyAndSpeed':'not measured by updater'}
        (dst/'SHA256-MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        for e in files:
            if digest(dst/e['path'])!=e['sha256']: raise ValueError('Copy verification failed: '+e['path'])
        print('Created:',dst);print('Manifest SHA256:',digest(dst/'SHA256-MANIFEST.json'))
        print('Original remains unchanged. Next: cd into the new directory; ./run.sh --check')
    except Exception:
        # Keep partial new output for inspection; never remove any user files.
        print('Incomplete new copy retained at '+str(dst)+'; do not run it.',file=sys.stderr)
        raise

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('original',type=pathlib.Path);p.add_argument('new_copy',type=pathlib.Path);a=p.parse_args()
    if platform.system()!='Linux' or platform.machine()!='x86_64': raise ValueError('Linux x86-64 required')
    flags=[set(x.split(':',1)[1].split()) for x in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('flags') and ':' in x]
    if not flags or any(not REQUIRED<=f for f in flags): raise ValueError('Required CPU flags are absent; keep using original package')
    upgrade(a.original,a.new_copy,pathlib.Path(__file__).resolve().parent)
if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as e: sys.exit(str(e))
