/** Reuse decoded resources only for the same immutable in-memory page object. */
export function createPageResourceCache(compile,decode) {
 const pages=new WeakMap();
 return {
  load(page) {
   if(pages.has(page))return pages.get(page);
   const request=Promise.resolve().then(async()=>{
    const paths=compile(page.reader),images=new Map();
    for(const block of page.reader.blocks)for(const token of block.tokens)if(token.kind==='native_image'&&!images.has(token.id))images.set(token.id,await decode(token));
    return {paths,images};
   });
   pages.set(page,request);
   request.catch(()=>{if(pages.get(page)===request)pages.delete(page);});
   return request;
  },
 };
}
