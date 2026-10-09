// Same-document trusted module, importing data only. Never evaluate imported code.
let importGeneration=0;
const picker=document.querySelector('#research-bundle');
picker.addEventListener('change',async()=>{
 const version=++importGeneration,file=picker.files?.[0];if(!file)return;++generation;
 try {
  if(file.size>BUNDLE_LIMITS.bytes)throw Error('本地研究数据超过 16 MiB 上限。');
  const candidate=validateResearchBundle(JSON.parse(await file.text()));if(version!==importGeneration)return;
  // Preflight every offered font before replacing an already working document.
  for(const next of candidate.pages)for(const font of [20,24,28]){const layouts=layoutBlocks(next.reader,font,Math.min(390,document.documentElement.clientWidth));if(layouts.reduce((n,b)=>n+Math.ceil(b.width*(window.devicePixelRatio||1))*Math.ceil(b.height*(window.devicePixelRatio||1)),0)>DEFAULT_LAYOUT.maximumCanvasPixels)throw Error('研究数据超出画布预算。');if(next.text_map)for(const layout of layouts)selectionGeometry(next.reader,layout,next.text_map.blocks[layout.index]);}
  await resourceCache.load(candidate.pages[0]);if(version!==importGeneration)return;
  const previousPages=bundle.pages,previousIndex=pageSelect.value,previousOptions=[...pageSelect.options].map(o=>o.cloneNode(true));
  bundle.pages=candidate.pages;pageSelect.replaceChildren(...candidate.pages.map((page,index)=>{const option=document.createElement('option');option.value=String(index);option.textContent=page.label;return option;}));pageSelect.value='0';try{await changePage();}catch(error){if(version===importGeneration){bundle.pages=previousPages;pageSelect.replaceChildren(...previousOptions);pageSelect.value=previousIndex;}throw error;}
 } catch(error){if(version===importGeneration)status.textContent='未载入研究数据：'+error.message;}
 finally {if(version===importGeneration)picker.value='';}
});
