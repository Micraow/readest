/** Bounded formula children; predecessor glyph/image painter is unchanged. */
import {layoutBlocks as ordinaryLayout,DEFAULT_LAYOUT} from '../../generic-reflow-v2-paragraph-vector/code/reader_engine.mjs';
export {glyphPath,compileResources,drawBlock,DEFAULT_LAYOUT} from '../../generic-reflow-v2-paragraph-vector/code/reader_engine.mjs';
/** @typedef {{minimumChildGapEm:number,followingNumberGapEm:number}} FormulaLayoutConfig */
/** @type {Readonly<FormulaLayoutConfig>} */
export const FORMULA_LAYOUT=Object.freeze({minimumChildGapEm:1,followingNumberGapEm:.15});
export function layoutBlocks(data,font,width,cfg=DEFAULT_LAYOUT,formula=FORMULA_LAYOUT){
 const layouts=ordinaryLayout(data,font,width,cfg),usable=width-2*cfg.paddingCssPx;
 for(let index=0;index<data.blocks.length;index++){
  const block=data.blocks[index];if(block.kind!=='formula')continue;
  if(block.tokens.length!==2||block.tokens[0].formula_role!=='core'||block.tokens[1].formula_role!=='label')throw Error('invalid formula hierarchy');
  const [core,label]=block.tokens;let y=cfg.paddingCssPx;const requestedCore=core.width_em*font,labelWidth=label.width_em*font,labelHeight=label.height_em*font,gap=formula.minimumChildGapEm*font;
  if(labelWidth>usable)throw Error('formula label exceeds viewport');
  const side=requestedCore+gap+labelWidth<=usable,coreFont=side?font:Math.min(font,usable/core.width_em),coreWidth=core.width_em*coreFont,coreHeight=core.height_em*coreFont;
  const coreX=cfg.paddingCssPx+(usable-(side?labelWidth+gap:0)-coreWidth)/2,labelX=width-cfg.paddingCssPx-labelWidth;
  let labelY=side?y+block.label_anchor_em*coreFont-(label.height_em+label.vertical_em)*font:y+coreHeight+formula.followingNumberGapEm*font;
  if(labelY<y){y+=cfg.paddingCssPx-labelY;labelY=cfg.paddingCssPx;}
  const placements=[{token:core,x:coreX,y,width:coreWidth,height:coreHeight,fontScale:coreFont},{token:label,x:labelX,y:labelY,width:labelWidth,height:labelHeight,fontScale:font}];
  layouts[index]={index,kind:'formula',width,height:Math.ceil(Math.max(y+coreHeight,labelY+labelHeight)+cfg.paragraphGapEm*font),placements,fontCss:font,source_token_count:2,formula_layout:{mode:side?'side_by_side':'number_following_row',core_scale_ratio:coreFont/font,core_and_label_native_geometry_preserved:true}};
 }
 return layouts;
}
