/** Exact nonzero-alpha intersection; bounding boxes alone never authorize merging. */
export function inkContact(a,b,width,height,maximumPixels=32000000){
 if(!Number.isInteger(width)||!Number.isInteger(height)||width<=0||height<=0||width*height>maximumPixels)throw Error('ink-contact canvas budget');
 if(!(a instanceof Uint8Array||a instanceof Uint8ClampedArray)||!(b instanceof Uint8Array||b instanceof Uint8ClampedArray)||a.length!==width*height*4||b.length!==a.length)throw Error('ink-contact RGBA dimensions');
 let aPixels=0,bPixels=0,overlapPixels=0;
 for(let i=3;i<a.length;i+=4){const x=a[i]>0,y=b[i]>0;aPixels+=Number(x);bPixels+=Number(y);overlapPixels+=Number(x&&y);}
 return {a_pixels:aPixels,b_pixels:bPixels,overlap_pixels:overlapPixels,nonempty_support:aPixels>0&&bPixels>0,disjoint_nonzero_alpha:aPixels>0&&bPixels>0&&overlapPixels===0,automatic_merge_authorized:false};
}
