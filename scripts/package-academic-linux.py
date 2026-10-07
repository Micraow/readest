#!/usr/bin/env python3
"""Assemble verified CI ELF + pinned CEF runtime without compiling application code."""
import argparse, hashlib, json, pathlib, shutil, struct, subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--native', type=pathlib.Path, required=True)
parser.add_argument('--cef', type=pathlib.Path, required=True)
parser.add_argument('--output', type=pathlib.Path, required=True)
args = parser.parse_args()
NATIVE, CEF, OUT = args.native.resolve(), args.cef.resolve(), args.output.resolve()
P = json.loads((NATIVE/'provenance.json').read_text())
assert P['sourceIntegrity']['passed'], 'Quarantined build: source integrity failed'
OUT.mkdir(exist_ok=False)

def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def elf(data):
    assert data[:6] == b'\x7fELF\x02\x01'
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    ph = [struct.unpack_from('<IIQQQQQQ',data,h[5]+i*h[9]) for i in range(h[10])]
    sh = [struct.unpack_from('<IIQQQQIIQQ',data,h[6]+i*h[11]) for i in range(h[12])]
    names = sh[h[13]]; strings = data[names[4]:names[4]+names[5]]
    sections = {}
    for s in sh:
        if s[2] & 2:
            n = strings[s[0]:].split(b'\0',1)[0].decode()
            sections[n] = {'type':s[1], 'flags':s[2], 'address':s[3], 'size':s[5], 'alignment':s[8], 'data': b'' if s[1]==8 else data[s[4]:s[4]+s[5]]}
    return h, ph, sections

def verify_elf(before,after):
    a,b = before.read_bytes(),after.read_bytes()
    ha,pa,sa = elf(a); hb,pb,sb = elf(b)
    assert pa == pb, 'Program headers changed'
    assert sa == sb, 'Allocated sections changed'
    aa,bb=bytearray(a),bytearray(b)
    # strip may change only ELF section-header table metadata in loaded headers.
    for start,end in [(40,48),(58,64)]: aa[start:end]=b'\0'*(end-start);bb[start:end]=b'\0'*(end-start)
    for p in pa:
        if p[0]==1:
            offset,size=p[2],p[5]
            assert aa[offset:offset+size]==bb[offset:offset+size], 'Loaded bytes changed'
    return {'allocatedSectionCount':len(sa),'loadSegmentCount':sum(p[0]==1 for p in pa), 'allocatedSectionsUnchanged':True,'loadBytesUnchangedExceptSectionTableMetadata':True,'beforeSha256':sha(before),'afterSha256':sha(after),'beforeBytes':len(a),'afterBytes':len(b)}

report = {'sourceCommit':P['sourceCommit'],'sourceTree':P['sourceTree'],'runtimeVerified':{},'strippedElfVerification':{}}
shutil.copy2(NATIVE/'readest',OUT/'readest')
assert sha(OUT/'readest')==P['binarySha256']
for name, expected in P['cefRuntimeSha256'].items():
    relative = pathlib.PurePosixPath(name)
    assert not relative.is_absolute() and '..' not in relative.parts, 'Unsafe runtime path'
    src=CEF/name;dst=OUT/name
    assert src.resolve().is_relative_to(CEF) and src.is_file(), name
    assert sha(src)==expected,name
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    report['runtimeVerified'][name]=expected
for name in ['readest','libcef.so']:
    dst=OUT/name;src=(NATIVE if name=='readest' else CEF)/name
    subprocess.run(['strip','--strip-unneeded',str(dst)],check=True)
    report['strippedElfVerification'][name]=verify_elf(src,dst)
shutil.copy2(NATIVE/'LICENSE',OUT/'LICENSE')
shutil.copy2(CEF/'LICENSE.txt',OUT/'CEF_LICENSE.txt')
shutil.copy2(NATIVE/'provenance.json',OUT/'build-provenance.json')
(OUT/'Readest').write_text('#!/bin/sh\nset -eu\nHERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexport LD_LIBRARY_PATH="$HERE${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\nexec "$HERE/readest" "$@"\n')
(OUT/'Readest').chmod(0o755);(OUT/'readest').chmod(0o755)
(OUT/'package-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'directory':str(OUT),'runtimeFiles':len(report['runtimeVerified']),'elf':report['strippedElfVerification']},indent=2))
