(function(root){
  'use strict';
  const MAX_FILE_BYTES=250_000_000,MAX_ASSETS=1000;
  const validImage=image=>typeof image==='string'&&/^data:image\/(png|jpeg|webp);base64,/.test(image);
  const cleanAsset=a=>!!(a&&typeof a==='object'&&typeof a.id==='string'&&typeof a.name==='string'&&['Carimbado','Ejetor','Com aplique','Tradicional'].includes(a.kind)&&(!a.image||validImage(a.image)));

  function validateProject(s){
    if(!s||typeof s!=='object'||Array.isArray(s)||s.schema!==1)throw Error('Este arquivo não é um projeto Docito compatível.');
    if(!Array.isArray(s.cells)&&Array.isArray(s.library))throw Error('Este arquivo é uma biblioteca. Use “Importar biblioteca”.');
    if(![[7,7],[10,5],[10,10]].some(([c,r])=>s.cols===c&&s.rows===r)||!Array.isArray(s.cells)||s.cells.length!==s.cols*s.rows)throw Error('A caixa do projeto está inválida ou incompleta.');
    if(!Array.isArray(s.library)||s.library.length>MAX_ASSETS)throw Error('A biblioteca do projeto deve conter até '+MAX_ASSETS+' artes.');
    if(!s.library.every(cleanAsset)||!s.cells.every(c=>c===null||cleanAsset(c)))throw Error('O projeto contém um doce ou uma arte inválida.');
    if(!Number.isInteger(s.quantity)||s.quantity<1||s.quantity>1000)throw Error('Quantidade inválida.');
    for(const key of ['client','theme','extra'])if(s[key]!==undefined&&typeof s[key]!=='string')throw Error('Os dados de cliente ou tema do projeto estão inválidos.');
    return s;
  }

  // A imagem é armazenada uma única vez, mesmo quando aparece em toda a caixa.
  function packAssets(groups){
    const images=[],refs=new Map();
    const pack=a=>{
      if(a===null)return null;
      const copy={...a};
      delete copy.imageRef;
      if(a.image){
        if(!refs.has(a.image)){refs.set(a.image,images.length);images.push(a.image);}
        copy.imageRef=refs.get(a.image);delete copy.image;
      }
      return copy;
    };
    return {images,groups:groups.map(group=>group.map(pack))};
  }

  function unpackAssets(d,groups){
    if(!Array.isArray(d.images)||d.images.length>MAX_ASSETS+100||!d.images.every(validImage))throw Error('As imagens do arquivo estão inválidas.');
    return groups.map(group=>{
      if(!Array.isArray(group)||group.length>MAX_ASSETS)throw Error('A lista de artes do arquivo está inválida.');
      return group.map(a=>{
        if(a===null)return null;
        if(!a||typeof a!=='object'||Array.isArray(a))throw Error('O arquivo contém uma arte inválida.');
        const copy={...a};
        if(Object.hasOwn(a,'imageRef')){
          if(!Number.isInteger(a.imageRef)||a.imageRef<0||a.imageRef>=d.images.length)throw Error('Uma imagem do arquivo está ausente.');
          copy.image=d.images[a.imageRef];delete copy.imageRef;
        }
        return copy;
      });
    });
  }

  function openProject(d){
    let s=d;
    if(d?.schema===2){
      if(!Array.isArray(d.cells)&&Array.isArray(d.library))throw Error('Este arquivo é uma biblioteca. Use “Importar biblioteca”.');
      const [cells,library]=unpackAssets(d,[d.cells,d.library]);
      s={...d,schema:1,cells,library};delete s.images;
    }
    validateProject(s);
    return {...s,client:s.client??'',theme:s.theme??'',extra:s.extra??''};
  }

  function packProject(s){
    validateProject(s);
    const {images,groups:[cells,library]}=packAssets([s.cells,s.library]);
    return {...s,schema:2,cells,library,images};
  }

  function openLibrary(d){
    let library=d?.library;
    if(d?.schema===2)[library]=unpackAssets(d,[library]);
    if(![1,2].includes(d?.schema)||!Array.isArray(library)||library.length>MAX_ASSETS||!library.every(cleanAsset))throw Error('Biblioteca inválida.');
    return library;
  }

  function packLibrary(library){
    openLibrary({schema:1,library});
    const {images,groups:[assets]}=packAssets([library]);
    return {schema:2,library:assets,images};
  }

  function stringify(d){
    const text=JSON.stringify(d);
    if(new TextEncoder().encode(text).length>MAX_FILE_BYTES)throw Error('O arquivo ultrapassa 250 MB. Reduza a biblioteca antes de salvar.');
    return text;
  }

  function parse(text){
    try{return JSON.parse(text.replace(/^\uFEFF/,''));}
    catch{throw Error('Não foi possível ler o JSON. Escolha o arquivo de projeto original baixado pela Docito.');}
  }

  const api={MAX_FILE_BYTES,MAX_ASSETS,cleanAsset,validateProject,openProject,packProject,openLibrary,packLibrary,stringify,parse};
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.DocitoProjectFiles=api;
})(typeof window==='undefined'?globalThis:window);
