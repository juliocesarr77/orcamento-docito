'use strict';
// Pure image-mask operations shared by the importer and sample stamps.
const DocitoImages = (() => {
  function bounds(data, width, height, cutoff=8) {
    let left=width,top=height,right=-1,bottom=-1;
    for(let y=0;y<height;y++) for(let x=0;x<width;x++) {
      if(data[(y*width+x)*4+3]>cutoff) {
        left=Math.min(left,x);top=Math.min(top,y);
        right=Math.max(right,x);bottom=Math.max(bottom,y);
      }
    }
    return right<left?null:{x:left,y:top,width:right-left+1,height:bottom-top+1};
  }
  function cleanMask(data,width,height,radius=2,minArea=6) {
    let mask=Uint8Array.from({length:width*height},(_,i)=>data[i*4+3]>32?1:0);
    // Close only tiny gaps caused by metallic highlights, preserving real openings.
    const morph=(src,dilate)=>{
      const out=new Uint8Array(src.length);
      for(let y=0;y<height;y++) for(let x=0;x<width;x++) {
        let value=dilate?0:1;
        search: for(let dy=-radius;dy<=radius;dy++) for(let dx=-radius;dx<=radius;dx++) {
          if(dx*dx+dy*dy>radius*radius)continue;
          const xx=x+dx,yy=y+dy;
          const hit=xx>=0&&xx<width&&yy>=0&&yy<height?src[yy*width+xx]:0;
          if((dilate&&hit)||(!dilate&&!hit)){value=dilate?1:0;break search;}
        }
        out[y*width+x]=value;
      }
      return out;
    };
    if(radius>0) mask=morph(morph(mask,true),false);
    const seen=new Uint8Array(mask.length);
    for(let i=0;i<mask.length;i++) if(mask[i]&&!seen[i]) {
      const queue=[i];seen[i]=1;
      for(let k=0;k<queue.length;k++) {
        const pos=queue[k],x=pos%width,y=Math.floor(pos/width);
        for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++) {
          const xx=x+dx,yy=y+dy,n=yy*width+xx;
          if(xx>=0&&xx<width&&yy>=0&&yy<height&&mask[n]&&!seen[n]){seen[n]=1;queue.push(n);}
        }
      }
      if(queue.length<minArea)for(const n of queue)mask[n]=0;
    }
    for(let i=0;i<mask.length;i++){data[i*4]=255;data[i*4+1]=255;data[i*4+2]=255;data[i*4+3]=mask[i]?255:0;}
    return data;
  }
  function tintSelection(data,mask,color){
    let sum=0,weight=0;
    for(let i=0;i<data.length;i+=4){const a=mask[i+3]/255*data[i+3]/255;sum+=Math.max(data[i],data[i+1],data[i+2])*a;weight+=a;}
    if(!weight)return false;
    const average=sum/weight;
    for(let i=0;i<data.length;i+=4){
      if(!mask[i+3]||!data[i+3])continue;
      const strength=mask[i+3]/255,shade=Math.min(1.12,Math.max(.35,Math.max(data[i],data[i+1],data[i+2])/Math.max(1,average)));
      for(let c=0;c<3;c++)data[i+c]=Math.round(data[i+c]*(1-strength)+Math.min(255,color[c]*shade)*strength);
    }
    return true;
  }
  function simplifyEditable(data,width,height,maxColors=4){
    const k=Math.max(2,Math.min(8,Math.trunc(maxColors)||4));
    const total=width*height,step=Math.max(1,Math.ceil(Math.sqrt(total/70000))),hist=new Map();
    for(let y=0;y<height;y+=step)for(let x=0;x<width;x+=step){
      const i=(y*width+x)*4;if(data[i+3]<24)continue;
      const key=((data[i]>>4)<<8)|((data[i+1]>>4)<<4)|(data[i+2]>>4),h=hist.get(key)||[0,0,0,0];
      h[0]+=data[i];h[1]+=data[i+1];h[2]+=data[i+2];h[3]++;hist.set(key,h);
    }
    let seeds=[...hist.values()].sort((a,b)=>b[3]-a[3]).map(h=>[h[0]/h[3],h[1]/h[3],h[2]/h[3],h[3]]);
    const centers=[];
    for(const s of seeds){
      if(centers.every(c=>(c[0]-s[0])**2+(c[1]-s[1])**2+(c[2]-s[2])**2>28**2))centers.push(s.slice(0,3));
      if(centers.length===k)break;
    }
    for(const s of seeds){if(centers.length===k)break;centers.push(s.slice(0,3));}
    if(!centers.length)return {colors:[],counts:[],masks:[]};
    const nearest=(r,g,b)=>{let best=0,dist=Infinity;for(let c=0;c<centers.length;c++){const d=(r-centers[c][0])**2+(g-centers[c][1])**2+(b-centers[c][2])**2;if(d<dist){dist=d;best=c;}}return best;};
    for(let pass=0;pass<4;pass++){
      const sums=centers.map(()=>[0,0,0,0]);
      for(let y=0;y<height;y+=step)for(let x=0;x<width;x+=step){const i=(y*width+x)*4;if(data[i+3]<24)continue;const c=nearest(data[i],data[i+1],data[i+2]),a=sums[c];a[0]+=data[i];a[1]+=data[i+1];a[2]+=data[i+2];a[3]++;}
      sums.forEach((a,i)=>{if(a[3])centers[i]=[a[0]/a[3],a[1]/a[3],a[2]/a[3]];});
    }
    const assignments=new Uint8Array(total),counts=new Array(centers.length).fill(0);
    for(let p=0;p<total;p++){const i=p*4;if(data[i+3]<24){assignments[p]=255;continue;}const c=nearest(data[i],data[i+1],data[i+2]);assignments[p]=c;counts[c]++;data[i]=Math.round(centers[c][0]);data[i+1]=Math.round(centers[c][1]);data[i+2]=Math.round(centers[c][2]);}
    const order=counts.map((count,i)=>({count,i})).filter(x=>x.count).sort((a,b)=>b.count-a.count),masks=[];
    for(const item of order){const mask=new Uint8ClampedArray(data.length);for(let p=0;p<total;p++)if(assignments[p]===item.i){const j=p*4;mask[j]=mask[j+1]=mask[j+2]=255;mask[j+3]=255;}masks.push(mask);}
    return {colors:order.map(x=>centers[x.i].map(v=>Math.round(v))),counts:order.map(x=>x.count),masks};
  }
  return {bounds,cleanMask,tintSelection,simplifyEditable};
})();
if(typeof module!=='undefined')module.exports=DocitoImages;
