// Every word and geometric element below was created for this test.
// No PDF, extracted paper text, external URL, or private corpus is used.
export const asset = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<rect width="600" height="800" fill="white"/>
<text x="24" y="45" font-size="25">Synthetic source page</text>
<rect x="30" y="100" width="240" height="90" fill="#dbeafe" stroke="#2563eb"/>
<text x="42" y="150" font-size="26">x + y = z</text>
<rect x="30" y="260" width="500" height="140" fill="#dcfce7" stroke="#16a34a"/>
<text x="44" y="320" font-size="24">Synthetic figure</text>
<text x="300" y="150" font-size="16">Unused region</text>
</svg>`;
const run = (text, item = 1) => ({kind:'text', text, source:{itemIndices:[item]}});
const textBlock = (text, item = 1) => ({kind:'text', role:'body', atomIds:[item], runs:[run(text,item)]});
const sourceBlock = (label, box) => ({kind:'source', label, box});
export const pages = [
  {
    key:'Synthetic-page-A', asset:'synthetic.svg', width:600, height:800,
    warnings:['Synthetic fixture only. Browser behavior is not PDF semantic acceptance.'],
    metrics:{reflowTextChars:200, sourceChars:250, reflowFraction:0.8},
    blocks:[
      {kind:'text',role:'heading',atomIds:[0],runs:[run('Synthetic heading',0)]},
      textBlock('Selectable synthetic body text. '.repeat(12)),
      {kind:'text',role:'body',atomIds:[2],runs:[
        run('An inline source follows: ',2),
        {kind:'source',fontSize:30,baseline:165,source:{boxes:[{x:30,y:100,width:240,height:90}]}},
        run(' and selectable text continues after it.',3),
      ]},
      sourceBlock('Synthetic block crop',{x:30,y:260,width:500,height:140}),
    ],
    floats:[sourceBlock('Synthetic float',{x:30,y:260,width:500,height:140})],
    notes:[textBlock('Synthetic note.',4)], margins:[],
  },
  {
    key:'Synthetic-page-B', asset:'synthetic.svg', width:600, height:800,
    warnings:['Synthetic second page.'],
    metrics:{reflowTextChars:40, sourceChars:40, reflowFraction:1},
    blocks:[textBlock('Second page selectable content.',5)],
    floats:[],notes:[],margins:[],
  },
];
