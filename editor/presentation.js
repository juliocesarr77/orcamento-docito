/* Apresentação A4 Docito. Coordenadas em 1055 × 1492; saída 3720 × 5262.
   Fontes locais e asset de cabeçalho completo, sem recorte em runtime. */
window.DocitoPresentation=(()=>{
 const C={brown:'#482319',muted:'#a5654a',line:'#efb99f',peach:'#f7dccb',accent:'#d38b68'};
 const asset=name=>(window.DOCITO_ASSETS&&window.DOCITO_ASSETS[name])||name;
 let ready;
 function resources(){return ready||(ready=(async()=>{
  for(const [family,file,weight] of [['DocitoSerif','NimbusRoman-Regular.otf','400'],['DocitoSerif','NimbusRoman-Bold.otf','700'],['DocitoSans','NimbusSans-Regular.otf','400'],['DocitoSans','NimbusSans-Bold.otf','700'],['DocitoScript','Z003-MediumItalic.otf','400']]){
   const f=new FontFace(family,`url(${asset('fonts/'+file)})`,{weight});document.fonts.add(await f.load());
  }
  const logo=new Image();logo.src=asset('logo-header.png');await logo.decode();return {logo};
 })().catch(e=>{ready=null;throw e;}));}
 function text(ctx,s,x,y,size=14,family='DocitoSerif',weight='400',color=C.brown,align='left',spacing=0){ctx.save();ctx.font=`${weight} ${size}px ${family}`;ctx.fillStyle=color;ctx.textAlign=align;ctx.textBaseline='alphabetic';ctx.letterSpacing=spacing+'px';ctx.fillText(s,x,y);ctx.restore();}
 function line(ctx,x,y,x2,y2,color=C.line,width=1){ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.moveTo(x,y);ctx.lineTo(x2,y2);ctx.stroke();}
 function box(ctx,x,y,w,h,r,fill='rgba(255,255,255,.22)',stroke=true){ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fillStyle=fill;ctx.fill();ctx.strokeStyle=C.line;ctx.lineWidth=1;if(stroke)ctx.stroke();}
 function heart(ctx,x,y,s=9,stroke=false){ctx.save();ctx.translate(x,y);ctx.scale(s,s);ctx.beginPath();ctx.moveTo(0,.8);ctx.bezierCurveTo(-.25,.55,-1.25,-.25,-.72,-.7);ctx.bezierCurveTo(-.3,-1,0,-.5,0,-.3);ctx.bezierCurveTo(.2,-1,.85,-1,1,-.45);ctx.bezierCurveTo(1.2,.05,.4,.65,0,.8);ctx.fillStyle=C.accent;ctx.strokeStyle=C.accent;ctx.lineWidth=.12;stroke?ctx.stroke():ctx.fill();ctx.restore();}
 function divider(ctx,x,y,w){line(ctx,x-w,y,x-24,y);line(ctx,x+24,y,x+w,y);heart(ctx,x,y,9);}
 function icon(ctx,type,x,y,r=40){ctx.save();ctx.translate(x,y);ctx.fillStyle=C.peach;ctx.beginPath();ctx.arc(0,0,r,0,7);ctx.fill();ctx.strokeStyle='#895035';ctx.lineWidth=1.6;ctx.beginPath();
 if(type==='client'){ctx.arc(0,-9,10,0,7);ctx.moveTo(-17,20);ctx.bezierCurveTo(-17,-3,17,-3,17,20);}
 if(type==='gift'){ctx.rect(-16,-8,32,27);ctx.rect(-17,-12,34,6);ctx.moveTo(-2,-12);ctx.lineTo(-2,19);ctx.moveTo(3,-12);ctx.lineTo(3,19);ctx.moveTo(0,-12);ctx.bezierCurveTo(-22,-35,-18,-1,0,-12);ctx.bezierCurveTo(22,-35,18,-1,0,-12);}
 if(type==='box'){ctx.moveTo(0,-17);ctx.lineTo(15,-8);ctx.lineTo(15,9);ctx.lineTo(0,18);ctx.lineTo(-15,9);ctx.lineTo(-15,-8);ctx.closePath();ctx.moveTo(-15,-8);ctx.lineTo(0,1);ctx.lineTo(15,-8);ctx.moveTo(0,1);ctx.lineTo(0,18);}
 if(type==='grid'){ctx.rect(-13,-13,26,26);for(let i=-4;i<13;i+=9){ctx.moveTo(i,-13);ctx.lineTo(i,13);ctx.moveTo(-13,i);ctx.lineTo(13,i);}}
 if(type==='order'){ctx.moveTo(-10,-16);ctx.lineTo(10,-16);ctx.lineTo(10,16);ctx.lineTo(-10,16);ctx.closePath();for(let i=-7;i<13;i+=5){ctx.moveTo(-6,i);ctx.lineTo(6,i);}}
 ctx.stroke();ctx.restore();}
 // Prefer two complete lines. Keep shrinking until both lines and every word fit;
 // never discard words, truncate or horizontally stretch text.
 function fit(ctx,value,width,start=28){
 ctx.font=`700 ${start}px DocitoSans`;const whole=ctx.measureText(String(value)).width;const single=start*Math.min(1,width/Math.max(1,whole));
 if(single>=Math.min(22,start*.85))return {size:single,lines:[String(value)]};
 const words=String(value).trim().split(/\s+/);let size=start;
 for(let attempt=0;attempt<1000;attempt++,size*=.96){ctx.font=`700 ${size}px DocitoSans`;let lines=[''];for(const word of words){const i=lines.length-1,test=lines[i]?lines[i]+' '+word:word;if(lines[i]&&ctx.measureText(test).width>width)lines.push(word);else lines[i]=test;}
 if(lines.length<=2&&lines.every(s=>ctx.measureText(s).width<=width))return {size,lines};}
 throw Error('Não foi possível ajustar o texto.');}
 function field(ctx,value,x,y,width){const f=fit(ctx,value,width,20);const step=f.size*1.15;f.lines.forEach((s,i)=>text(ctx,s,x,y-(f.lines.length-1)*step/2+i*step+f.size*.33,f.size,'DocitoSans','700'));return f;}
 function decorations(ctx){
  const bg=ctx.createLinearGradient(0,0,1055,1492);bg.addColorStop(0,'#fff5ec');bg.addColorStop(.48,'#fffaf5');bg.addColorStop(1,'#fff2e7');ctx.fillStyle=bg;ctx.fillRect(0,0,1055,1492);
  for(const [color,off] of [['#fce2d1',22],['#f4c4a8',0]]){ctx.save();ctx.translate(0,off);ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(365,0);ctx.bezierCurveTo(270,106,233,4,160,19);ctx.bezierCurveTo(78,20,59,99,0,120);ctx.closePath();ctx.fill();ctx.restore();}
  for(const [color,off] of [['#fce2d1',-25],['#f8d3bc',0]]){ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(700,1492);ctx.bezierCurveTo(826,1451+off,902,1349+off,1055,1316+off);ctx.lineTo(1055,1492);ctx.closePath();ctx.fill();}
  ctx.fillStyle='#fce9dc';ctx.beginPath();ctx.moveTo(0,1107);ctx.bezierCurveTo(75,1059,116,1113,0,1218);ctx.lineTo(0,1492);ctx.lineTo(222,1492);ctx.bezierCurveTo(93,1446,149,1330,0,1380);ctx.closePath();ctx.fill();
  ctx.strokeStyle=C.accent;ctx.lineWidth=1.3;
  ctx.beginPath();ctx.moveTo(927,190);ctx.bezierCurveTo(1000,198,1033,169,1055,115);ctx.stroke();heart(ctx,1000,161,12,true);
  ctx.beginPath();ctx.moveTo(0,1400);ctx.bezierCurveTo(85,1438,110,1341,60,1378);ctx.bezierCurveTo(38,1324,48,1463,114,1490);ctx.stroke();
  ctx.beginPath();ctx.moveTo(1040,1492);ctx.bezierCurveTo(1040,1451,1003,1430,992,1377);ctx.stroke();for(const [x,y,s]of [[977,1384,6],[1016,1394,5],[1023,1414,6],[1006,1440,7]])heart(ctx,x,y,s,true);
 }
 async function render(state,tile){const {logo}=await resources();const c=document.createElement('canvas');c.width=3720;c.height=5262;const ctx=c.getContext('2d');ctx.scale(c.width/1055,c.height/1492);ctx.imageSmoothingQuality='high';decorations(ctx);
 // All ornaments and typography follow the approved composition.
 ['DOCES','PERSONALIZADOS','PARA HISTÓRIAS','INCRÍVEIS'].forEach((s,i)=>text(ctx,s,90,110+i*20,11,'DocitoSerif','400',C.muted,'left',3));line(ctx,90,184,121,184);heart(ctx,140,185,7);
 text(ctx,'Mais',844,68,37,'DocitoScript','400',C.muted);text(ctx,'do que doces,',837,102,30,'DocitoScript','400',C.muted);text(ctx,'momentos',866,131,30,'DocitoScript','400',C.muted);
 // Contain the complete header asset (transparent margins included), no source crop.
 const scale=Math.min(345/logo.width,205/logo.height);ctx.drawImage(logo,(1055-logo.width*scale)/2,-26,logo.width*scale,logo.height*scale);
 divider(ctx,527.5,180,96);
 const title='PROJETO DE DOCES PERSONALIZADOS';let titleSize=35;ctx.font=`700 ${titleSize}px DocitoSerif`;while(ctx.measureText(title).width>930){titleSize-=.25;ctx.font=`700 ${titleSize}px DocitoSerif`;}
 text(ctx,title,527.5,220,titleSize,'DocitoSerif','700',C.brown,'center');text(ctx,'Detalhes que encantam. Sabores que ficam na memória.',527.5,250,17,'DocitoSerif','400',C.muted,'center',2);divider(ctx,527.5,270,169);
 box(ctx,41,292,973,72,16);line(ctx,527,304,527,352);icon(ctx,'client',85,328,24);icon(ctx,'gift',571,328,24);
 text(ctx,'CLIENTE',128,312,11,'DocitoSans','400',C.muted);text(ctx,'TEMA',614,312,11,'DocitoSans','400',C.muted);
 const client=field(ctx,(state.client||'Projeto').toUpperCase(),128,338,375);const theme=field(ctx,(state.theme||'Tema personalizado').toUpperCase(),614,338,376);
 const labels=[`Caixa ${state.cols} x ${state.rows}`,`${state.cells.filter(Boolean).length} posições preenchidas`,`Pedido: ${state.quantity} doces`];
 for(let i=0;i<3;i++){const x=41+i*330.5;box(ctx,x,376,312,48,13);icon(ctx,['box','grid','order'][i],x+32,400,20);text(ctx,labels[i],x+184,405,16,'DocitoSerif','700',C.brown,'center');}
 box(ctx,41,438,973,857,21);text(ctx,'PRÉVIA DA MONTAGEM',65,474,26,'DocitoSerif','700');line(ctx,65,484,148,484,C.accent,3);
 ['PEQUENOS DETALHES','GRANDES EMOÇÕES'].forEach((s,i)=>text(ctx,s,900,461+i*16,9,'DocitoSerif','400',C.muted,'center',2));line(ctx,866,487,922,487);heart(ctx,940,487,6);
 ctx.save();ctx.translate(65,765);['Doce','é fazer','parte de','momentos','especiais'].forEach((s,i)=>text(ctx,s,0,i*29,20,'DocitoScript','400',C.muted));heart(ctx,39,145,10,true);ctx.restore();
 heart(ctx,947,796,9);['SONHOS','TAMBÉM','TÊM SABOR'].forEach((s,i)=>text(ctx,s,947,826+i*20,10,'DocitoSerif','400',C.muted,'center',1.2));
 const area={x:177.5,y:510,w:700,h:700};if(state.rows===5){area.x=157.5;area.w=740;}
 const unit=Math.min(area.w/state.cols,area.h/state.rows),gw=unit*state.cols,gh=unit*state.rows,gx=area.x+(area.w-gw)/2,gy=area.y+(area.h-gh)/2;
 // Um único traço sai de trás da caixa, desenha o coração e segue até a lateral.
 ctx.save();ctx.strokeStyle=C.accent;ctx.lineWidth=1.3;ctx.lineCap='round';ctx.lineJoin='round';
 ctx.beginPath();ctx.moveTo(gx+gw-10,gy+gh*.86);
 ctx.bezierCurveTo(914,1140,930,1131,944,1118);
 ctx.bezierCurveTo(932,1107,917,1090,929,1080);
 ctx.bezierCurveTo(937,1073,943,1084,944,1090);
 ctx.bezierCurveTo(950,1069,970,1074,964,1089);
 ctx.bezierCurveTo(960,1100,950,1114,944,1118);
 ctx.bezierCurveTo(974,1126,1007,1056,1055,1026);ctx.stroke();ctx.restore();
 ctx.save();ctx.shadowColor='rgba(119,74,46,.12)';ctx.shadowBlur=14;ctx.shadowOffsetY=5;box(ctx,gx-17,gy-17,gw+34,gh+34,19,'#fff3e9');ctx.restore();
 // Renderiza cada célula na resolução final e libera o buffer após compor.
 for(let i=0;i<state.cells.length;i++){const t=await tile(state.cells[i],Math.ceil(unit*c.width/1055));ctx.drawImage(t,gx+(i%state.cols)*unit,gy+Math.floor(i/state.cols)*unit,unit,unit);t.width=1;t.height=1;}
 box(ctx,153,1241,749,40,17,'#fbe8da',false);ctx.fillStyle=C.accent;ctx.beginPath();ctx.arc(184,1261,15,0,7);ctx.fill();ctx.save();C.accent='#fffaf7';heart(ctx,184,1261,7,true);C.accent='#d38b68';ctx.restore();
 text(ctx,'Prévia ilustrativa para aprovação. Cores e detalhes podem variar discretamente na produção artesanal.',216,1266,13.5);
 line(ctx,123,1329,932,1329);text(ctx,'Docito Doceria  •  Instagram: @docitodoceria_123  •  Projeto preparado com carinho para você',527.5,1365,14,'DocitoSerif','700',C.brown,'center');divider(ctx,527.5,1390,96);
 const now=new Date(),date=now.toLocaleDateString('pt-BR',{timeZone:'America/Sao_Paulo'}),time=now.toLocaleTimeString('pt-BR',{timeZone:'America/Sao_Paulo',hour:'2-digit',minute:'2-digit'});text(ctx,`Gerado em: ${date} às ${time}`,527.5,1421,12,'DocitoSans','400',C.muted,'center');
 ['A VIDA','FICA MAIS DOCE','COM DOCITO'].forEach((s,i)=>text(ctx,s,89,1415+i*17,10,'DocitoSerif','400',C.muted,'left',2.5));line(ctx,90,1463,121,1463);
 ['DOCES','QUE CRIAM','BOAS LEMBRANÇAS'].forEach((s,i)=>text(ctx,s,942,1421+i*16,9,'DocitoSerif','400',C.muted,'center',2));line(ctx,968,1464,1000,1464);
 c.docitoLayout={client,theme,grid:{x:gx,y:gy,width:gw,height:gh,unit},resolution:[c.width,c.height]};return c;
 }
 return {render,fit,resources};
})();
