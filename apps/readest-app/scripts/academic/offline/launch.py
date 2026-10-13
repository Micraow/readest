#!/usr/bin/env python3
"""Local, fixed-resource PDF OCR launcher. No downloads or system installation."""
import argparse,hashlib,importlib.util,json,math,os,pathlib,platform,signal,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent

def parser():
 p=argparse.ArgumentParser(description='离线 Ovis PDF 识别；CPU-only，保留原始 OCR 与可导入 Readest 的结果。')
 p.add_argument('pdf',nargs='?',type=pathlib.Path,help='待识别 PDF，原文件不会修改')
 p.add_argument('output',nargs='?',type=pathlib.Path,help='新的结果目录；父目录需存在，不覆盖已有结果')
 p.add_argument('--check',action='store_true',help='仅校验文件/依赖与 CLI 版本，不运行模型')
 p.add_argument('--low-memory',action='store_true',help='1024 图像 tokens；小字/图表细节可能下降；仍需至少3GiB可用内存')
 p.add_argument('--threads',type=int,default=2,help='CPU线程数，默认2，允许1–8')
 p.add_argument('--page-timeout',type=int,default=900,help='每页秒数上限，默认900')
 p.add_argument('--wall-timeout',type=int,default=21600,help='全任务秒数上限，默认21600（6小时）')
 return p

def check_integrity():
 manifest=json.loads((ROOT/'SHA256-MANIFEST.json').read_text())
 for item in manifest['files']:
  rel=pathlib.PurePosixPath(item['path'])
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('非法清单路径')
  p=ROOT.joinpath(*rel.parts)
  if p.is_symlink() or not p.is_file() or p.stat().st_size!=item['bytes']:raise ValueError('文件缺失/类型/大小不符：'+str(rel))
  with p.open('rb') as source:
   if hashlib.file_digest(source,'sha256').hexdigest()!=item['sha256']:raise ValueError('SHA256不符：'+str(rel))
 expected={x['path'] for x in manifest['files']}
 for name in ('bin','models','python','scripts'):
  for p in (ROOT/name).rglob('*'):
   if p.is_symlink() or p.is_file() and p.relative_to(ROOT).as_posix() not in expected:raise ValueError('运行目录存在清单外文件：'+str(p.relative_to(ROOT)))
 return len(manifest['files'])

def memory_available_mib():
 for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
  if line.startswith('MemAvailable:'):return int(line.split()[1])//1024
 raise ValueError('无法读取可用内存，拒绝盲目启动')

def main():
 a=parser().parse_args()
 if not a.check and (a.pdf is None or a.output is None):parser().error('请提供 PDF 与新的结果目录，或使用 --check')
 if platform.system()!='Linux' or platform.machine()!='x86_64':raise ValueError('仅支持Linux x86_64')
 libc,version=platform.libc_ver()
 if libc!='glibc' or tuple(map(int,version.split('.')[:2]))<(2,38):raise ValueError('需要glibc >=2.38；实际 '+libc+' '+version)
 if not 1<=a.threads<=8 or not 1<=a.page_timeout<=3600 or not 1<=a.wall_timeout<=86400:raise ValueError('线程需1–8；每页上限1–3600秒；总上限1–86400秒')
 n=check_integrity()
 import fitz
 result=subprocess.run([str(ROOT/'bin/llama-mtmd-cli'),'--version'],cwd=ROOT/'bin',capture_output=True,text=True,timeout=20,check=True)
 print('文件校验通过：',n,'；Python',sys.version.split()[0],'；PyMuPDF',fitz.VersionBind,flush=True)
 print((result.stdout+result.stderr).strip(),flush=True)
 mem=memory_available_mib();print('当前系统可见可用内存：',mem,'MiB（不保证等于容器实际限额）',flush=True)
 if a.check:
  print('静态/依赖检查通过；未运行模型，不代表此机器推理或GPU已验证。');return 0
 floor=3072 if a.low_memory else 6144
 if mem<floor:raise ValueError(f'当前可见内存不足：本配置启动门槛{floor}MiB，建议先关闭自己不需的应用；不自动终止其他进程。')
 spec=importlib.util.spec_from_file_location('ovis_fixed_runner',ROOT/'scripts/run-ovis-pdf.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
 args=runner.parser().parse_args(['--pdf',str(a.pdf.absolute()),'--output-dir',str(a.output.absolute()),'--cli',str(ROOT/'bin/llama-mtmd-cli'),'--model',str(ROOT/'models/OvisOCR2-Q3_K_M.gguf'),'--mmproj',str(ROOT/'models/mmproj-OvisOCR2-Q8_0.gguf'),'--prompt',str(ROOT/'prompt.txt'),'--runtime-revision','5266f24da75dc449bd56cbed7addb9c8e4a6a73e','--threads',str(a.threads),'--dpi','144','--flash-attn','on','--image-max-tokens','1024' if a.low_memory else '2048','--max-rss-mib','2048' if a.low_memory else '4096','--page-timeout-seconds',str(a.page_timeout),'--wall-timeout-seconds',str(a.wall_timeout)])
 signal.signal(signal.SIGINT,runner.cancel);signal.signal(signal.SIGTERM,runner.cancel);signal.signal(signal.SIGCHLD,signal.SIG_DFL)
 print('开始顺序识别全部页面；Ctrl+C取消并回收自己的子进程。不会下载资源或自动上传文件。',flush=True)
 receipt=runner.run(args);print('完成：',str(a.output/'result/bundle.json'),'；覆盖',receipt['coverage']['coveredPages']);print('仍请核对原PDF：进程成功不能证明OCR无遗漏或已到EOS。');return 0
if __name__=='__main__':
 try:sys.exit(main())
 except (ValueError,OSError,RuntimeError,subprocess.SubprocessError) as e:print('未完成：'+str(e),file=sys.stderr);sys.exit(2)
