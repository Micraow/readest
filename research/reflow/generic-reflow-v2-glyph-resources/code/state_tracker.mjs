/** Capture explicit canvas state changes, not potentially stale backend getters. */
export function matrix(ctx) { const m=ctx.getTransform(); return [m.a,m.b,m.c,m.d,m.e,m.f]; }
export function trackState(ctx, Path2D) {
  const stack=[];let state={fillStyle:ctx.fillStyle,alpha:ctx.globalAlpha,blend:ctx.globalCompositeOperation,filter:ctx.filter,clips:[],affine:[],absoluteTransform:false};
  const properties={fillStyle:'fillStyle',globalAlpha:'alpha',globalCompositeOperation:'blend',filter:'filter'};
  for(const [property,key] of Object.entries(properties)) {
    let p=ctx,descriptor;while(p&&!descriptor){descriptor=Object.getOwnPropertyDescriptor(p,property);p=Object.getPrototypeOf(p);}
    if(!descriptor?.set||!descriptor?.get)throw Error('unsupported canvas state descriptor: '+property);
    Object.defineProperty(ctx,property,{configurable:true,get(){return descriptor.get.call(ctx);},set(value){descriptor.set.call(ctx,value);state[key]=descriptor.get.call(ctx);}});
  }
  for(const name of ['translate','scale','rotate','transform']){const original=ctx[name].bind(ctx);ctx[name]=(...args)=>{state.affine=[...state.affine,{name,args:[...args]}];return original(...args);};}
  for(const name of ['setTransform','resetTransform']){const original=ctx[name].bind(ctx);ctx[name]=(...args)=>{const result=original(...args);state.affine=[{name:'setTransform',args:matrix(ctx)}];state.absoluteTransform=true;return result;};}
  const save=ctx.save.bind(ctx),restore=ctx.restore.bind(ctx),clip=ctx.clip.bind(ctx);
  ctx.save=()=>{stack.push({...state,clips:[...state.clips],affine:[...state.affine]});return save();};
  ctx.restore=()=>{const value=restore();if(stack.length)state=stack.pop();return value;};
  ctx.clip=(...args)=>{
    if(!(args[0] instanceof Path2D))throw Error('implicit current-path clipping is outside this probe');
    state.clips=[...state.clips,{path:new Path2D(args[0]),svg:args[0].toSVGString(),rule:args[1]??'nonzero',transform:matrix(ctx),affine:[...state.affine],absoluteTransform:state.absoluteTransform}];return clip(...args);
  };
  ctx.__readestState=()=>({...state,clips:[...state.clips],affine:[...state.affine]});return ctx;
}
