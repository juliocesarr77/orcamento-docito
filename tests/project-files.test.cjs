const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const files=require('../editor/project-files.js');
const image='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jw1sAAAAASUVORK5CYII=';
const asset={id:'art',name:'Arte',kind:'Carimbado',image,decoration:true,base:'#f4b7c9',scale:80,rotation:45,offsetX:12,offsetY:-8,flip:true};
function project(cols=10,rows=5){return {schema:1,id:'project',client:'Cliente',theme:'Jardim',budget:123,cols,rows,quantity:100,extra:'2 separados',cells:Array.from({length:cols*rows},(_,i)=>i%3===0?null:{...asset,locked:i===2}),library:[{...asset}]};}

test('todos os formatos preservam posições, imagens, ajustes, travas e dados do pedido',()=>{
  for(const [cols,rows] of [[7,7],[10,5],[10,10]]){
    const original=project(cols,rows),snapshot=JSON.stringify(original);
    const packed=files.packProject(original);
    assert.equal(packed.images.length,1);
    assert.equal(packed.schema,2);
    assert.deepEqual(files.openProject(files.parse(files.stringify(packed))),original);
    assert.equal(JSON.stringify(original),snapshot);
  }
});

test('projetos antigos e arquivos com BOM continuam aceitos',()=>{
  const original=project();
  assert.deepEqual(files.openProject(files.parse('\uFEFF'+JSON.stringify(original))),original);
});

test('variações do mesmo cadastro mantêm imagens distintas',()=>{
  const original=project(),variation=image.replace('image/png','image/webp');
  original.cells[1]={...asset,image:variation};
  assert.equal(files.packProject(original).images.length,2);
  assert.deepEqual(files.openProject(files.packProject(original)),original);
});

test('bibliotecas antigas e novas preservam artes e ejetores',()=>{
  const library=[asset,{...asset,id:'ejetor',kind:'Ejetor',decoration:false}];
  assert.deepEqual(files.openLibrary({schema:1,library}),library);
  assert.deepEqual(files.openLibrary(files.packLibrary(library)),library);
});

test('erros de formato e referências quebradas são rejeitados',()=>{
  for(const bad of [null,[],{}, {...project(),cells:[]},{...project(),quantity:0},{...project(),schema:3}])assert.throws(()=>files.openProject(bad));
  const packed=files.packProject(project());packed.cells[1].imageRef=9;
  assert.throws(()=>files.openProject(packed),/imagem.*ausente/);
  assert.throws(()=>files.openProject(files.packLibrary([asset])),/Importar biblioteca/);
  assert.throws(()=>files.parse('{quebrado'),/JSON/);
  assert.throws(()=>files.openProject({...project(),library:[{...asset,image:'https://example.com/image.png'}]}));
});

test('bibliotecas com mais de 300 artes podem ser salvas e reabertas',()=>{
  const original=project();original.library=Array.from({length:301},(_,i)=>({...asset,id:'art-'+i}));
  assert.deepEqual(files.openProject(files.packProject(original)),original);
});

function editorHarness(){
  const elements=new Map(),events=[],window={parent:{postMessage(){}},addEventListener(){}};
  function element(id){
    if(!elements.has(id))elements.set(id,{value:'',textContent:'',files:[],style:{},classList:{toggle(){}},setAttribute(){},getAttribute(){return null;},addEventListener(){},querySelectorAll(){return [];}});
    return elements.get(id);
  }
  const context=vm.createContext({DocitoProjectFiles:files,document:{getElementById:element,querySelectorAll(){return [];},body:{}},window,crypto:{randomUUID(){return 'uuid';}},requestAnimationFrame(){return 1;},setTimeout,TextEncoder,Map,Set,Promise,localStorage:{getItem(){return '[]';},setItem(){}},events});
  vm.runInContext(fs.readFileSync(require.resolve('../editor/editor.js'),'utf8'),context);
  vm.runInContext("library=async()=>events.push('library');renderBrush=async()=>events.push('brush');render=async()=>events.push('render');loadImage=async()=>{};",context);
  return {context,element,events,state:()=>JSON.parse(vm.runInContext('JSON.stringify(state)',context))};
}

test('arquivo antigo acima de 25 MB passa no carregamento corrigido e é salvo sem repetir imagens',async()=>{
  const original=project(10,10);
  original.cells=original.cells.map(a=>a&&({...a,image:'data:image/png;base64,'+'A'.repeat(400000)}));
  original.library=[];
  const text=JSON.stringify(original),size=Buffer.byteLength(text);
  assert.ok(size>25_000_000);
  const input={files:[{size,text:async()=>text}]};
  const h=editorHarness();h.element('open').files=input.files;
  await h.element('open').onchange();
  assert.equal(h.element('notice').textContent,'Projeto aberto. Seus uploads foram mantidos na biblioteca.');
  assert.deepEqual(h.state().cells,original.cells);
  assert.ok(files.stringify(files.packProject(h.state())).length<text.length/20);
  assert.deepEqual(h.events,['library','brush','render']);
  assert.equal(h.element('open').value,'');
});

test('uma imagem quebrada mantém a montagem atual e permite nova tentativa',async()=>{
  const h=editorHarness(),before=h.state(),incoming=project();
  h.element('open').files=[{size:1000,text:async()=>JSON.stringify(incoming)}];
  vm.runInContext("loadImage=async()=>{throw Error('quebrada');};",h.context);
  await h.element('open').onchange();
  assert.deepEqual(h.state(),before);
  assert.match(h.element('notice').textContent,/montagem atual foi mantida/);
  vm.runInContext('loadImage=async()=>{};',h.context);
  await h.element('open').onchange();
  assert.equal(h.state().client,incoming.client);
});

test('ao reabrir, a arte salva no projeto tem prioridade e os demais uploads são mantidos',async()=>{
  const h=editorHarness(),incoming=project();
  vm.runInContext('state.library='+JSON.stringify([{...asset,name:'Versão alterada no navegador'},{...asset,id:'other',name:'Outro upload'}]),h.context);
  h.element('open').files=[{size:1000,text:async()=>JSON.stringify(incoming)}];
  await h.element('open').onchange();
  assert.equal(h.state().library.find(a=>a.id==='art').name,'Arte');
  assert.equal(h.state().library.find(a=>a.id==='other').name,'Outro upload');
});

test('cancelar a substituição preserva a montagem e avisa o usuário',async()=>{
  const h=editorHarness();
  vm.runInContext('state='+JSON.stringify(project())+';confirmProjectOpen=async()=>false;',h.context);
  const before=h.state();h.element('open').files=[{size:1000,text:async()=>JSON.stringify(project(7,7))}];
  await h.element('open').onchange();
  assert.deepEqual(h.state(),before);
  assert.match(h.element('notice').textContent,/cancelada/);
});

test('confirmar a abertura permite desfazer e recuperar a montagem anterior',async()=>{
  const h=editorHarness(),original=project(),incoming=project(7,7);
  vm.runInContext('state='+JSON.stringify(original)+';confirmProjectOpen=async()=>true;',h.context);
  h.element('open').files=[{size:1000,text:async()=>JSON.stringify(incoming)}];
  await h.element('open').onchange();
  assert.equal(h.state().cols,7);
  h.element('undo').onclick();
  assert.deepEqual(h.state(),original);
});

test('sucesso só é informado após concluir a atualização do projeto',async()=>{
  const h=editorHarness();let finishRender;
  h.context.renderPending=new Promise(resolve=>finishRender=resolve);
  vm.runInContext('render=()=>renderPending;',h.context);
  h.element('open').files=[{size:1000,text:async()=>JSON.stringify(project())}];
  const opening=h.element('open').onchange();
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(h.element('notice').textContent,/Abrindo projeto/);
  finishRender();await opening;
  assert.match(h.element('notice').textContent,/Projeto aberto/);
});
