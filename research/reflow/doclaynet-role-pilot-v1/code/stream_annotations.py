"""Stream official COCO JSON without materializing its 565MB training document."""
import io,json,zlib,pathlib,struct,hashlib,time
from remote_zip import B,get_range
class Inflate(io.RawIOBase):
 def __init__(self,path):self.f=open(path,'rb');self.z=zlib.decompressobj(-15);self.pending=b'';self.total=0;self.crc=0
 def readable(self):return True
 def readinto(self,buf):
  n=len(buf);out=b''
  while not out:
   if not self.pending:self.pending=self.f.read(65536)
   if not self.pending:return 0
   out=self.z.decompress(self.pending,n);self.pending=self.z.unconsumed_tail
  buf[:len(out)]=out;self.total+=len(out);self.crc=zlib.crc32(out,self.crc);return len(out)
 def close(self):self.f.close();super().close()
class Items:
 def __init__(self,stream):self.f=stream;self.s='';self.i=0;self.done=False;self.decoder=json.JSONDecoder()
 def more(self):
  self.s=self.s[self.i:];self.i=0;chunk=self.f.read(65536);self.s+=chunk
  if not chunk:self.done=True
 def peek(self):
  while True:
   while self.i<len(self.s) and self.s[self.i].isspace():self.i+=1
   if self.i<len(self.s):return self.s[self.i]
   if self.done:return ''
   self.more()
 def take(self,c):
  if self.peek()!=c:raise RuntimeError('Unexpected JSON delimiter')
  self.i+=1
 def value(self):
  self.peek()
  while True:
   try:x,end=self.decoder.raw_decode(self.s,self.i);self.i=end;return x
   except json.JSONDecodeError:
    if self.done:raise
    self.more()
 def __iter__(self):
  self.take('{')
  while self.peek()!='}':
   key=self.value();self.take(':')
   if self.peek()=='[':
    self.take('[')
    while self.peek()!=']':
     yield key,self.value()
     if self.peek()==',':self.take(',')
     else:break
    self.take(']')
   else:yield key,self.value()
   if self.peek()==',':self.take(',')
   else:break
  self.take('}')
  if self.peek():raise RuntimeError('Unexpected trailing JSON')
def ensure_compressed(split):
 entry=f'COCO/{split}.json';d=json.loads((B/'metadata/core-entries.json').read_text());info=d[entry];dest=B/'metadata'/f'{split}.deflate'
 if not dest.exists():
  raw=get_range('core',info['offset'],info['compressed']+65566);h=struct.unpack_from('<4s5H3L2H',raw);name=raw[30:30+h[-2]].decode();assert name==entry;start=30+h[-2]+h[-1];comp=raw[start:start+info['compressed']];assert len(comp)==info['compressed'];dest.write_bytes(comp)
 return dest,info
def iterate(split):
 path,info=ensure_compressed(split);r=Inflate(path)
 with io.TextIOWrapper(io.BufferedReader(r),encoding='utf8') as f:
  yield from Items(f)
  if r.total!=info['expanded'] or r.crc!=info['crc32']:raise RuntimeError('Uncompressed annotation size/CRC mismatch')
def selftest():
 sample={'meta':{'test':'original'},'images':[{'id':i,'text':'escaped \\" and unicode 数学 '+('x'*100)} for i in range(1000)],'annotations':[{'bbox':[1,2,3,4],'id':i} for i in range(1000)]};expected=[(k,x) for k,v in sample.items() for x in (v if isinstance(v,list) else [v])];assert list(Items(io.StringIO(json.dumps(sample,ensure_ascii=False))))==expected
if __name__=='__main__':
 selftest()
 for split in ['train','val','test']:
  images={};counts={};categories={};start=time.monotonic()
  for key,item in iterate(split):
   if key=='images':images[item['id']]=item
   elif key=='categories':categories[item['id']]=item['name']
   elif key=='annotations':
    if item.get('precedence',0)!=0:continue
    d=counts.setdefault(item['image_id'],{});k=str(item['category_id']);d[k]=d.get(k,0)+1
  rows=[]
  for i,r in images.items():
   if r.get('precedence',0)==0:rows.append({**r,'class_counts':counts.get(i,{})})
  (B/'metadata'/f'{split}-page-index.json').write_text(json.dumps({'categories':categories,'images':rows},separators=(',',':')))
  print(json.dumps({'split':split,'pages':len(rows),'categories':categories,'seconds':time.monotonic()-start}),flush=True)
