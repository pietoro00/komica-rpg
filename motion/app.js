{
const $=id=>document.getElementById(id);
const vid=$('vid'),ov=$('ov'),stage=$('stage'),pill=$('pill'),msg=$('msg');
const W=160;let H=120;
const work=document.createElement('canvas');
const wctx=work.getContext('2d',{willReadFrequently:true});
const octx=ov.getContext('2d');
let prev=null,running=false,stream=null,facing='environment',raf=0,warm=0,lastHit=0,lastT=0,count=0,ac=null,wake=null,fileURL=null;
const EMPTY='<p class="empty">還沒有紀錄。截圖可以長按存到相簿。</p>';

const store={get(k,d){try{const v=localStorage.getItem('md_'+k);return v===null?d:JSON.parse(v)}catch(e){return d}},set(k,v){try{localStorage.setItem('md_'+k,JSON.stringify(v))}catch(e){}}};
for(const id of ['sens','area'])$(id).value=store.get(id,$(id).value);
for(const id of ['snd','vib','shot'])$(id).checked=store.get(id,$(id).checked);
facing=store.get('facing',facing);

function labels(){
  $('sensV').textContent=$('sens').value+' / 10';
  $('areaV').textContent=(+$('area').value).toFixed(1)+'%';
  $('th').style.left=`calc(${Math.min(100,+$('area').value*5)}% - 1px)`;
}
function setPill(state,text){pill.className='pill '+state;pill.lastElementChild.textContent=text}
function showMsg(t,s){
  msg.innerHTML='';const d=document.createElement('div'),b=document.createElement('b');
  b.textContent=t;d.append(b,s||'');msg.append(d);msg.hidden=false;
}

function initAudio(){try{if(!ac)ac=new (window.AudioContext||window.webkitAudioContext)();ac.resume()}catch(e){}}
function beep(){
  if(!ac)return;
  try{const t=ac.currentTime;[0,.2].forEach(dt=>{const o=ac.createOscillator(),g=ac.createGain();o.type='square';o.frequency.value=880;
    g.gain.setValueAtTime(.0001,t+dt);g.gain.exponentialRampToValueAtTime(.3,t+dt+.01);g.gain.exponentialRampToValueAtTime(.0001,t+dt+.15);
    o.connect(g).connect(ac.destination);o.start(t+dt);o.stop(t+dt+.16)})}catch(e){}
}
async function keepAwake(){
  try{if('wakeLock' in navigator&&!wake){wake=await navigator.wakeLock.request('screen');wake.addEventListener('release',()=>{wake=null})}}catch(e){}
}

function stopAll(){
  running=false;cancelAnimationFrame(raf);
  if(stream){stream.getTracks().forEach(t=>t.stop());stream=null}
  vid.pause();vid.srcObject=null;vid.removeAttribute('src');vid.load();
  if(fileURL){URL.revokeObjectURL(fileURL);fileURL=null}
  octx.clearRect(0,0,ov.width,ov.height);
  $('go').textContent='開始偵測';$('go').classList.remove('stop');
  setPill('','待機');stage.classList.remove('hot');
  if(wake){wake.release().catch(()=>{});wake=null}
  $('cover').style.width='100%';$('pct').textContent='0%';
}

async function startCam(){
  stopAll();
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){
    showMsg('這裡無法開啟鏡頭','請用 https 網址開啟這個網頁，或先用影片檔測試。');return;
  }
  try{
    stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:facing,width:{ideal:640},height:{ideal:480}},audio:false});
  }catch(e){
    showMsg('無法開啟鏡頭',e.name==='NotAllowedError'||e.name==='SecurityError'
      ?'鏡頭權限被拒絕，或這個預覽框不允許使用鏡頭。請把網頁放到 https 網址再開，或先用影片檔測試。'
      :'錯誤：'+e.name);
    return;
  }
  vid.srcObject=stream;stage.classList.toggle('mirror',facing==='user');
  begin();
}
function startFile(f){
  stopAll();
  fileURL=URL.createObjectURL(f);vid.src=fileURL;vid.loop=true;stage.classList.remove('mirror');
  begin();
}
async function begin(){
  try{await vid.play()}catch(e){}
  if(!vid.videoWidth)await new Promise(r=>vid.addEventListener('loadedmetadata',r,{once:true}));
  const vw=vid.videoWidth||4,vh=vid.videoHeight||3;
  H=Math.max(1,Math.round(W*vh/vw));
  work.width=ov.width=W;work.height=ov.height=H;
  stage.style.aspectRatio=vw+'/'+vh;
  prev=null;warm=0;running=true;msg.hidden=true;
  $('go').textContent='停止偵測';$('go').classList.add('stop');setPill('on','偵測中');
  keepAwake();
  raf=requestAnimationFrame(loop);
}

function loop(t){
  raf=requestAnimationFrame(loop);
  if(t-lastT<90||vid.readyState<2)return;
  lastT=t;
  wctx.drawImage(vid,0,0,W,H);
  const px=wctx.getImageData(0,0,W,H).data,n=W*H,g=new Float32Array(n);
  for(let i=0,j=0;i<n;i++,j+=4)g[i]=px[j]*.299+px[j+1]*.587+px[j+2]*.114;
  if(!prev||prev.length!==n){prev=g;return}
  const thr=70-6*$('sens').value;
  let md=0;for(let i=0;i<n;i++)md+=g[i]-prev[i];md/=n; // 扣掉整體亮度變化（自動曝光、開燈）
  const out=octx.createImageData(W,H),o=out.data;let changed=0;
  for(let i=0;i<n;i++){
    const d=Math.abs(g[i]-prev[i]-md);
    if(d>thr){changed++;const k=i*4,s=Math.min(1,(d-thr)/60);o[k]=255;o[k+1]=Math.round(220*(1-s));o[k+2]=40;o[k+3]=140+Math.round(115*s)}
    prev[i]=prev[i]*.5+g[i]*.5;
  }
  octx.putImageData(out,0,0);
  const pct=changed/n*100;
  $('pct').textContent=pct.toFixed(1)+'%';
  $('cover').style.width=(100-Math.min(100,pct*5))+'%';
  if(warm<8){warm++;return}
  const now=Date.now();
  if(pct>=+$('area').value){
    stage.classList.add('hot');setPill('hot','有動靜！');
    if(now-lastHit>3000){lastHit=now;hit(pct)}
  }else if(now-lastHit>1200){stage.classList.remove('hot');setPill('on','偵測中')}
}

function hit(pct){
  count++;$('cnt').textContent=count;
  const time=new Date().toLocaleTimeString('zh-TW',{hour12:false});
  $('last').textContent=time;
  if($('snd').checked)beep();
  if($('vib').checked&&navigator.vibrate)try{navigator.vibrate([200,100,200])}catch(e){}
  if($('shot').checked)snap(time,pct);
}
function snap(time,pct){
  const vw=vid.videoWidth||4,vh=vid.videoHeight||3,c=document.createElement('canvas');
  c.width=Math.min(480,vw);c.height=Math.round(c.width*vh/vw);
  const x=c.getContext('2d');
  if(stage.classList.contains('mirror')){x.translate(c.width,0);x.scale(-1,1)}
  x.drawImage(vid,0,0,c.width,c.height);
  x.globalCompositeOperation='screen';x.globalAlpha=.7;x.imageSmoothingEnabled=false;x.drawImage(ov,0,0,c.width,c.height);
  const sh=$('shots');sh.querySelector('.empty')?.remove();
  const f=document.createElement('figure'),im=document.createElement('img'),cap=document.createElement('figcaption');
  im.src=c.toDataURL('image/jpeg',.8);im.alt='觸發時的畫面 '+time;
  cap.textContent=time+' · '+pct.toFixed(1)+'%';
  f.append(im,cap);sh.prepend(f);
  while(sh.children.length>30)sh.lastElementChild.remove();
}

['sens','area'].forEach(id=>$(id).addEventListener('input',()=>{store.set(id,+$(id).value);labels()}));
['snd','vib','shot'].forEach(id=>$(id).addEventListener('change',()=>store.set(id,$(id).checked)));
$('go').addEventListener('click',()=>{if(running||stream){stopAll();return}initAudio();startCam()});
$('flip').addEventListener('click',()=>{facing=facing==='user'?'environment':'user';store.set('facing',facing);if(stream){initAudio();startCam()}});
$('file').addEventListener('change',e=>{const f=e.target.files[0];if(f){initAudio();startFile(f)}e.target.value=''});
$('clr').addEventListener('click',()=>{count=0;$('cnt').textContent='0';$('last').textContent='—';$('shots').innerHTML=EMPTY});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&running)keepAwake()});
labels();
}
