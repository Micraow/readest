import json, os, pathlib, re, resource, subprocess, time
B=pathlib.Path(__file__).resolve().parent
S=B/'source/libk2pdfopt-64aa9ccfcd55921c596458cb8a7197339d5f32c3'
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
files=re.search(r'add_library\(k2pdfopt\s+(.*?)\n\)',(S/'lib/CMakeLists.txt').read_text(),re.S).group(1).split()
inc=['-I'+str(p) for p in [S/'lib',S/'k2pdfoptlib',S/'willuslib',B/'deps/root/usr/include',B/'deps/root/usr/include/leptonica']]
common=['-O2','-fPIC','-DBUILDING_LIBK2PDFOPT','-DNO_FILELIST','-DHAVE_TESSERACT_LIB']+inc
commands=[]; start=time.monotonic(); objects=[]
for i,rel in enumerate(files):
    src=(S/'lib'/rel).resolve(); obj=B/'build'/f'{i:02d}-{src.stem}.o'
    cmd=['c++' if src.suffix=='.cpp' else 'cc']+common
    if src.name=='setting.c':cmd+=['-Dk2pdfopt_settings_init_from_koptcontext=k2pdfopt_settings_init_from_koptcontext_upstream']
    cmd+=['-c',str(src),'-o',str(obj)]; commands.append(cmd)
    print(i,src.name,flush=True); subprocess.run(cmd,check=True);objects.append(str(obj))
for name in ['settings_override','harness']:
    obj=B/'build'/f'{name}.o'; cmd=['cc']+common+['-c',str(B/(name+'.c')),'-o',str(obj)]
    commands.append(cmd); subprocess.run(cmd,check=True); objects.append(str(obj))
cmd=['c++']+objects+['-o',str(B/'build/k2-reflow-harness'),'-Wl,-z,defs','-l:libtesseract.so.5','-l:libleptonica.so.6','-lm','-pthread']
commands.append(cmd);subprocess.run(cmd,check=True)
(B/'build/commands.json').write_text(json.dumps(commands,indent=2))
(B/'build/build-metrics.json').write_text(json.dumps({'seconds':time.monotonic()-start,'compiler_child_max_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'source_file_count':len(files),'cpu_affinity':list(os.sched_getaffinity(0))},indent=2))
print('BUILD OK',time.monotonic()-start,flush=True)
