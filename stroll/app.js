/* 오늘 하루, 시드니 한 바퀴 — 애니메이션 엔진
   경로는 data.json의 legs[].geom(실제 도로 스냅 / 페리·기차 곡선)을 따라 그린다.
   지도 베이스는 현재 Leaflet/OSM. Google Maps 키가 오면 base layer만 교체. */

const MODE = {
  start: { emoji:'📍', cls:'',      zoom:16 },
  walk:  { emoji:'🚶', cls:'',      zoom:16 },
  run:   { emoji:'🏃', cls:'',      zoom:16 },
  ferry: { emoji:'⛴️', cls:'ferry', zoom:14.5 },
  tram:  { emoji:'🚊', cls:'train', zoom:13.8 },
  train: { emoji:'🚆', cls:'train', zoom:13.5 },
  ride:  { emoji:'🚗', cls:'ride',  zoom:15 },
  flight:{ emoji:'✈️', cls:'flight',zoom:2.4 },   // 대륙 간 — 줌 확 빼서 한국↔호주가 다 보이게
};

function tintFor(hm){
  const h = parseInt(hm.split(':')[0],10) + parseInt(hm.split(':')[1],10)/60;
  if (h < 11)  return 'rgba(173,196,222,0.13)';
  if (h < 13)  return 'rgba(255,255,245,0.03)';
  if (h < 15)  return 'rgba(255,224,178,0.11)';
  return 'rgba(255,183,128,0.18)';
}

const el = s => document.querySelector(s);
const lerp = (a,b,t) => a + (b-a)*t;
const ease = t => t<.5 ? 2*t*t : 1-Math.pow(-2*t+2,2)/2;
const sleep = ms => new Promise(r=>setTimeout(r,ms));
// 현재 뷰 타일이 다 로드될 때까지 대기(헤드리스 녹화에서 지도 깨짐 방지). max까지만.
const waitTiles = max => new Promise(res=>{ if(!tiles) return res(); let done=false;
  const fin=()=>{ if(done) return; done=true; tiles.off('load',fin); res(); };
  tiles.on('load',fin); setTimeout(fin,max); });
function dist(a,b){ const dx=a[0]-b[0],dy=a[1]-b[1]; return Math.hypot(dx,dy); }

let DATA, map, tiles, trail, planned, traveler, running=false, cancelToken=0;
const EXPORT = new URLSearchParams(location.search).has('export');  // 릴스 세로영상 녹화 모드
const MK = EXPORT ? 2 : 1;   // export(1080x1920)에선 지도 마커도 2배로
const ZB = EXPORT ? 1 : 0;   // export는 뷰포트가 2배라 줌을 +1 당겨 같은 프레이밍 유지

// 카피 주입: brief의 copy{}로 훅·인트로·아웃트로 문구를 덮어쓴다(없으면 HTML 기본=시드니 유지)
function setText(sel, val){ if(val==null) return; const n=document.querySelector(sel); if(n) n.textContent=val; }
function applyCopy(){
  const c = DATA.copy || {};
  if(DATA.date) setText('#intro .date', DATA.date.replace(/\./g,' · '));
  setText('#hook-title .c-main', c.hook_title_en);
  setText('#hook-title .c-kr',   c.hook_title_kr);
  setText('#hook-title .hook-meta', c.hook_meta);
  setText('#intro h1', c.intro_title);
  setText('#intro .kr-line', c.intro_kr);
  setText('#intro .hint', c.intro_hint);
  setText('#start', c.intro_btn);
  setText('#outro .oj-hello', c.outro_hello || 'Hello,');
  setText('#outro .oj-syd', c.outro_big || 'SYDNEY');
  setText('#o-tag', c.outro_tag);
}

async function boot(){
  DATA = await (await fetch('data.json')).json();
  applyCopy();
  // 테마 강조색: 경로선·칩·점 등에 반영
  if(DATA.accent) document.documentElement.style.setProperty('--coral', DATA.accent);

  map = L.map('map',{ zoomControl:false, attributionControl:false, zoomSnap:0.25 });
  tiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    {maxZoom:19, keepBuffer:8, updateWhenZooming:false}).addTo(map);   // keepBuffer↑: 팬 중 타일 유지(블럭팝 완화)

  // full planned route = all legs concatenated
  const full = [];
  DATA.legs.forEach(lg => lg.geom.forEach(p=>full.push(p)));
  map.fitBounds(L.latLngBounds(full).pad(0.15));

  const ACC = DATA.accent || '#ff6b5e';
  planned = L.polyline(full,{color:ACC,weight:3,opacity:.16,dashArray:'2 9',lineCap:'round'}).addTo(map);
  trail   = L.polyline([],{color:ACC,weight:5,opacity:.95,lineCap:'round',lineJoin:'round'}).addTo(map);

  // number real (non-waypoint) stops in visit order; track dots only for real stops
  let n=0;
  DATA.stops.forEach(s=>{ if(!s.waypoint){ n++; s.num=n; } });
  const track = el('#track');
  DATA.stops.filter(s=>!s.waypoint).forEach(()=>{ const d=document.createElement('div'); d.className='t'; track.appendChild(d); });

  el('#o-km').textContent = Math.round(DATA.total_km).toLocaleString();
  el('#o-stops').textContent = new Set(DATA.stops.filter(s=>!s.waypoint).map(s=>s.name)).size;
  el('#o-photos').textContent = DATA.n_photos;
  const _r=el('#o-route'); if(_r) _r.innerHTML = uniqueRouteNames().join('<span class="arrow">→</span>');
  const _m=el('#o-modes'); if(_m){
    const MODE_EN={walk:'Walk',run:'Run',tram:'Tram',train:'Train',ferry:'Ferry',ride:'Ride',flight:'Flight'};
    _m.innerHTML = (DATA.modes||[]).map(m=>{const emoji=(MODE[m.mode]||MODE.walk).emoji;
      return `<span class="mchip"><i>${emoji}</i> ${MODE_EN[m.mode]||m.mode} ${m.km}km<span class="kr">${m.label}</span></span>`;}).join('');
  }
  // ----- Journey Card 아웃트로: 오늘 수집한 스탬프(COLLECTED TODAY) + Sydney Collection 진행 -----
  const got = DATA.stops.filter(s=>!s.waypoint && s.icon);
  const sk=el('#o-stickers');
  if(sk){ sk.innerHTML = got.map((s,i)=>{
      const rot=((i%2)?1:-1)*(2.5+(i%3)*1.5); const d=(0.5+i*0.34).toFixed(2);  // 페이드인 후 쾅...쾅
      return `<figure class="oj-stmp" style="--d:${d}s;--rot:${rot}deg"><span class="oj-new">NEW!</span><img src="assets/icons/${s.icon}.png" alt=""><figcaption>${s.name}</figcaption></figure>`;
    }).join(''); }
  const grid=el('#o-collgrid');
  if(grid){
    let html=''; got.forEach((s,i)=>{ const d=(0.6+i*0.34).toFixed(2);
      html+=`<div class="oj-cell on" style="--d:${d}s;--rot:${(((i%2)?1:-1)*2.2).toFixed(1)}deg"><img src="assets/icons/${s.icon}.png" alt=""></div>`; });
    for(let i=got.length;i<6;i++) html+='<div class="oj-cell off">?</div>';
    grid.innerHTML=html;
  }
  const COLL_TOTAL = DATA.collection_total || 86;
  if(el('#o-collt')) el('#o-collt').textContent = COLL_TOTAL;
  if(el('#o-colln')) el('#o-colln').textContent = got.length;

  if(EXPORT){                          // 릴스 녹화: 녹화기가 트리거할 때까지 대기 → 훅 → 재생
    document.body.classList.add('export');
    el('#intro').classList.add('hide');
    const ph=el('#hook-photo');          // 히어로를 즉시 표시(정적 → 압축 뭉갬 없이 선명)
    if(DATA.hook && DATA.hook.hero){ ph.style.backgroundImage=`url("${DATA.hook.hero}")`; }
    el('#hook').classList.remove('hide');
    let started=false;
    window.__startReel = async()=>{ if(started) return; started=true; await hookSequence(); play(); };
    setTimeout(()=>{ if(!window.__recorder) window.__startReel(); }, 30000);   // 폴백(수동 열람 전용). 녹화기(__recorder)는 명시 트리거만 — 레이스 차단
    // 녹화 전 경로 타일을 미리 받아 캐시(팬 중 블럭팝 방지). 녹화기가 호출.
    window.__preloadRoute = async()=>{
      const tileWait = max => new Promise(res=>{ let done=false;
        const fin=()=>{ if(done)return; done=true; tiles.off('load',fin); res(); };
        tiles.on('load',fin); setTimeout(fin,max); });
      for(const lg of (DATA.legs||[])){
        const z=Math.round((MODE[lg.mode]||MODE.walk).zoom+ZB), g=lg.geom||[];
        const step=Math.max(1,Math.floor(g.length/8));
        for(let i=0;i<g.length;i+=step){ map.setView(g[i],z,{animate:false}); await tileWait(500); }
      }
      const f=(DATA.stops||[])[0];
      if(f){ map.setView([f.lat,f.lon],Math.round(MODE.start.zoom+ZB),{animate:false}); await tileWait(500); }
    };
  }
}

// 오프닝 훅: 히어로 셀카 → 스탯 티저 → 사진 플래시 → 지도로 전환
function buildHookStats(){
  const stops=new Set(DATA.stops.filter(s=>!s.waypoint).map(s=>s.name)).size;
  // 이동수단 줄: data.modes에서 동적 생성 (러닝/도보/기차/페리 무엇이든 자동)
  const modeStr=(DATA.modes||[]).map(m=>{
    const e=(MODE[m.mode]||MODE.walk).emoji;
    return `${e} ${m.label}${m.count>1?' ×'+m.count:''}`;
  }).join(' · ');
  const cells=[[DATA.total_km,'KM'],[stops,'곳 STOPS'],[DATA.n_photos,'컷 MOMENTS']];
  el('#hook-stats').innerHTML =
    `<div class="hk-pill">` + cells.map(c=>`<div class="hk"><b>${c[0]}</b><span>${c[1]}</span></div>`).join('') + `</div>` +
    `<div class="hk-modes">${modeStr}</div>`;
}
async function hookSequence(){
  // 인트로는 ~2.4초로 짧게: 히어로+타이틀만 보여주고 바로 지도로(차별점=지도 미디어를 3초 안에).
  // 스탯 티저·플래시 몽타주는 마무리에서 다시 나오므로 인트로에선 생략.
  const hook=el('#hook'), H=DATA.hook||{};
  if(!H.hero) return;
  await sleep(400);
  el('#hook-title').classList.add('go');
  await sleep(1400);
  el('#hook-title').classList.add('out');
  await sleep(150);
  hook.classList.add('zoomout');   // 지도로 전환
  await sleep(500);
  hook.classList.add('hide');
}

function uniqueRouteNames(){
  const out=[]; DATA.stops.forEach(s=>{ if(out[out.length-1]!==s.name) out.push(s.name); });
  return out;
}

function mediaSrc(m){ return (m.type==='video'?'assets/posters/':'assets/photos/')+m.file; }

// 밝은 모자 여행자 — 청록 몸 + 노랑 모자, 흰 외곽선. 표정 최소화 + 어른 비율
const MASCOT = `<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
  <rect x="20.2" y="34.5" width="3.3" height="7.6" rx="1.65" fill="#0e9e90"/>
  <rect x="24.5" y="34.5" width="3.3" height="7.6" rx="1.65" fill="#0e9e90"/>
  <path d="M17 37 q0 -13 7 -13 q7 0 7 13 z" fill="#16c2ae"/>
  <circle cx="24" cy="18.8" r="7.1" fill="#ffe2c9"/>
  <circle cx="21.6" cy="19.2" r="1" fill="#3a3330"/>
  <circle cx="26.4" cy="19.2" r="1" fill="#3a3330"/>
  <path d="M17 13.4 q7 -4.3 14 0 q-4 -5.8 -7 -5.8 q-3 0 -7 5.8z" fill="#ffce3a"/>
  <path d="M13.4 16 q10.6 -4.9 21.2 0 q-2.2 2.2 -10.6 2.2 q-8.4 0 -10.6 -2.2z" fill="#ffd84f"/>
  <path d="M17.9 14.2 q6.1 -2.8 12.2 0" stroke="#16c2ae" stroke-width="1.4" fill="none" stroke-linecap="round"/>
</svg>`;

// 시드니 트레인 (실버 바디 + 노란 앞/문), 오른쪽 진행 기준
const TRAIN_SVG = `<svg viewBox="0 0 66 34" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="26" width="50" height="4" rx="2" fill="#6f777d"/>
  <circle cx="18" cy="30" r="2.6" fill="#39424a"/><circle cx="48" cy="30" r="2.6" fill="#39424a"/>
  <rect x="4" y="6" width="50" height="21" rx="6.5" fill="#d3d8dc"/>
  <path d="M50 6 h2.5 q7.5 0 7.5 8.5 v4 q0 8.5 -7.5 8.5 h-2.5 z" fill="#f4c01f"/>
  <path d="M53 9.5 q4.5 1 5 6 h-5 z" fill="#27343d"/>
  <rect x="8" y="9.5" width="40" height="7.5" rx="2" fill="#27343d"/>
  <rect x="16" y="10.5" width="6" height="14.5" rx="1" fill="#f4c01f"/>
  <rect x="33" y="10.5" width="6" height="14.5" rx="1" fill="#f4c01f"/>
  <circle cx="58" cy="22.5" r="1.7" fill="#fff"/>
</svg>`;
// 시드니 페리 (그린 선체 + 크림 상부), 오른쪽 진행 기준
const FERRY_SVG = `<svg viewBox="0 0 60 42" xmlns="http://www.w3.org/2000/svg">
  <path d="M4 26 h52 l-5 9 q-1.2 2 -3.4 2 h-35.2 q-2.2 0 -3.4 -2 z" fill="#1f5c39"/>
  <rect x="6" y="23.5" width="48" height="3" fill="#f4c01f"/>
  <rect x="9" y="14" width="42" height="10" fill="#efe3c2"/>
  <g fill="#23323b"><rect x="12" y="16" width="5" height="5"/><rect x="19" y="16" width="5" height="5"/><rect x="26" y="16" width="5" height="5"/><rect x="33" y="16" width="5" height="5"/><rect x="40" y="16" width="5" height="5"/></g>
  <rect x="15" y="7" width="27" height="7" fill="#efe3c2"/>
  <g fill="#23323b"><rect x="18" y="8.5" width="4" height="4"/><rect x="24" y="8.5" width="4" height="4"/><rect x="30" y="8.5" width="4" height="4"/><rect x="36" y="8.5" width="4" height="4"/></g>
  <rect x="24" y="2.5" width="9" height="5" rx="1" fill="#efe3c2"/>
  <rect x="28.3" y="-1" width="1.4" height="4" fill="#8a6a3a"/>
  <path d="M2 38 q6 2.6 11 0 q6 2.6 12 0 q6 2.6 12 0 q5 2.6 10 0" fill="none" stroke="#a7d8e0" stroke-width="2.6" stroke-linecap="round"/>
</svg>`;

// 시드니 경전철(트램) — 빨강 바디 + 검정 창띠 + 흰 스트라이프, 팬터그래프. 오른쪽 진행 기준
const TRAM_SVG = `<svg viewBox="0 0 66 34" xmlns="http://www.w3.org/2000/svg">
  <rect x="7" y="27" width="52" height="3.2" rx="1.6" fill="#6f777d"/>
  <circle cx="19" cy="30.4" r="2.3" fill="#39424a"/><circle cx="47" cy="30.4" r="2.3" fill="#39424a"/>
  <path d="M50 6 l5 -3.5" stroke="#2b2f36" stroke-width="1.3" stroke-linecap="round"/>
  <rect x="4" y="7.5" width="56" height="19.5" rx="6.5" fill="#d6232e"/>
  <path d="M55 7.5 q5 0 5 6 v7.5 q0 6 -5 6 z" fill="#23272d"/>
  <rect x="9" y="11" width="45" height="7.5" rx="2.2" fill="#23272d"/>
  <rect x="6.5" y="20" width="51" height="2.4" fill="#f2f2f2"/>
  <rect x="21" y="12" width="5.5" height="13.5" rx="1" fill="#ffd84f"/>
  <rect x="37" y="12" width="5.5" height="13.5" rx="1" fill="#ffd84f"/>
  <circle cx="57.5" cy="23.5" r="1.5" fill="#fff"/>
</svg>`;

// 드라이브 — 코랄 바디 해치백(오른쪽 진행 기준). 라이드 모드 마커.
const CAR_SVG = `<svg viewBox="0 0 64 34" xmlns="http://www.w3.org/2000/svg">
  <circle cx="18" cy="27.5" r="5.4" fill="#2b2f36"/><circle cx="18" cy="27.5" r="2.2" fill="#cfd4d8"/>
  <circle cx="46" cy="27.5" r="5.4" fill="#2b2f36"/><circle cx="46" cy="27.5" r="2.2" fill="#cfd4d8"/>
  <path d="M4.5 25 v-5 q0 -2 2.2 -2.6 l5.6 -1.5 q3 -6.6 9.2 -6.6 h12.6 q5.6 0 9.1 4.3 l5.6 3 q6 0.6 7 4 l0.4 1.9 q0.3 2.5 -2.4 2.5 z" fill="#ff6b5e"/>
  <path d="M16.4 16.6 q2.5 -4.7 6.7 -4.7 h10.5 q3.9 0 6.5 3.5 l1.5 2 z" fill="#bfe6f2"/>
  <rect x="27.6" y="11.9" width="1.8" height="6" fill="#ff6b5e"/>
  <rect x="6" y="20.2" width="50" height="2" fill="#ffffff" opacity="0.45"/>
  <circle cx="55.6" cy="19.6" r="1.7" fill="#ffe08a"/>
</svg>`;

// 국제선 — 대한항공 도장(스카이블루+화이트+태극). 노즈 오른쪽 기준, CSS로 우하향 기울임.
const KAL_TAEGEUK = (cx,cy,r)=>`
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="#fff"/>
    <path d="M${cx} ${cy-r} a${r} ${r} 0 0 1 0 ${2*r} a${r/2} ${r/2} 0 0 1 0 ${-r} a${r/2} ${r/2} 0 0 0 0 ${-r} z" fill="#d22730"/>
    <path d="M${cx} ${cy+r} a${r} ${r} 0 0 1 0 ${-2*r} a${r/2} ${r/2} 0 0 1 0 ${r} a${r/2} ${r/2} 0 0 0 0 ${r} z" fill="#0b3d91"/>`;
const PLANE_SVG = `<svg viewBox="0 0 84 60" xmlns="http://www.w3.org/2000/svg">
  <g stroke="#cdd6df" stroke-width="0.7" stroke-linejoin="round">
    <!-- tail fin (sky blue) -->
    <path d="M9 33 L5 9 Q4.4 6 8 7.5 L25 30 Z" fill="#8fc3ec" stroke="none"/>
    <!-- swept wing (grey) -->
    <path d="M34 35 L20 53 Q19 55 23 53.6 L47 36 Z" fill="#aeb9c4"/>
    <!-- fuselage white -->
    <path d="M9 37 Q6.5 31 15 30 L62 26.5 Q76 26.5 81 32.5 Q83 34.5 81 36.5 Q75 41 61 40 L17 40.5 Q10 40.5 9 37 Z" fill="#ffffff"/>
    <!-- sky-blue top cheatline -->
    <path d="M15 30 L62 26.7 Q73 26.7 79 31 L17 33.4 Q11 33.4 15 30 Z" fill="#8fc3ec" stroke="none"/>
    <!-- engine -->
    <ellipse cx="44" cy="40.6" rx="8.5" ry="3.6" fill="#9aa6b3"/>
  </g>
  <!-- windows -->
  <g fill="#41525f">${[26,30,34,38,42,46,50,54,58].map(x=>`<rect x="${x}" y="31.6" width="2.1" height="1.7" rx="0.7"/>`).join('')}</g>
  <!-- cockpit -->
  <path d="M75 31.5 Q80 32.4 81 34.4 L74.5 33.6 Z" fill="#41525f"/>
  <!-- taegeuk on tail -->
  ${KAL_TAEGEUK(12.5,17,4.4)}
  <!-- taegeuk on engine -->
  ${KAL_TAEGEUK(40,40.6,2.4)}
</svg>`;

function travelerIcon(mode, flip){
  const f = flip ? ' flip' : '';
  if(mode==='flight') return L.divIcon({className:'',html:`<div class="vehicle"><div class="veh-inner flight">${PLANE_SVG}</div></div>`,iconSize:[72*MK,72*MK],iconAnchor:[36*MK,36*MK]});
  if(mode==='ride') return L.divIcon({className:'',html:`<div class="vehicle${f}"><div class="veh-inner ride">${CAR_SVG}</div></div>`,iconSize:[64*MK,34*MK],iconAnchor:[32*MK,28*MK]});
  if(mode==='train') return L.divIcon({className:'',html:`<div class="vehicle${f}"><div class="veh-inner train">${TRAIN_SVG}</div></div>`,iconSize:[66*MK,34*MK],iconAnchor:[33*MK,28*MK]});
  if(mode==='tram') return L.divIcon({className:'',html:`<div class="vehicle${f}"><div class="veh-inner train">${TRAM_SVG}</div></div>`,iconSize:[66*MK,34*MK],iconAnchor:[33*MK,28*MK]});
  if(mode==='ferry') return L.divIcon({className:'',html:`<div class="vehicle${f}"><div class="veh-inner ferry">${FERRY_SVG}</div></div>`,iconSize:[60*MK,42*MK],iconAnchor:[30*MK,34*MK]});
  return L.divIcon({className:'',html:`<div class="traveler">${MASCOT}</div>`,iconSize:[50*MK,50*MK],iconAnchor:[25*MK,25*MK]});
}
function placeTraveler(latlng,mode,flip){
  if(traveler){ traveler.setIcon(travelerIcon(mode,flip)); traveler.setLatLng(latlng); }
  else traveler=L.marker(latlng,{icon:travelerIcon(mode,flip),zIndexOffset:1000}).addTo(map);
}

// animate marker along a polyline geom (arc-length parameterized), growing the trail
function travelLeg(geom, mode, dur, tok){
  return new Promise(res=>{
    const flip = geom[geom.length-1][1] < geom[0][1];   // 서쪽으로 가면 좌우 반전
    placeTraveler(geom[0],mode,flip);
    // cumulative lengths
    const cum=[0]; let total=0;
    for(let i=1;i<geom.length;i++){ total+=dist(geom[i-1],geom[i]); cum.push(total); }
    if(total===0){ res(); return; }
    const base=trail.getLatLngs().slice();
    let t0=null;
    function frame(ts){
      if(tok!==cancelToken) return res();
      if(t0===null) t0=ts;
      const t=Math.min(1,(ts-t0)/dur), e=ease(t);
      const target=e*total;
      // find segment
      let k=1; while(k<cum.length && cum[k]<target) k++;
      const segT=(target-cum[k-1])/((cum[k]-cum[k-1])||1);
      const lat=lerp(geom[k-1][0],geom[k][0],segT);
      const lon=lerp(geom[k-1][1],geom[k][1],segT);
      const pos=[lat,lon];
      traveler.setLatLng(pos);
      trail.setLatLngs(base.concat(geom.slice(0,k)).concat([pos]));
      if(mode!=='flight') map.panTo(pos,{animate:false});   // 비행은 arc 전체를 고정해 보여줌(팬 안 함)
      if(t<1) requestAnimationFrame(frame); else res();
    }
    requestAnimationFrame(frame);
  });
}

function dropRailStations(leg){
  (leg.rail_stations||[]).forEach(st=>{
    const icon=L.divIcon({className:'',html:`<div class="railtick" title="${st.name}"></div>`,iconSize:[11*MK,11*MK],iconAnchor:[5.5*MK,5.5*MK]});
    L.marker([st.lat,st.lon],{icon,interactive:false}).addTo(map);
  });
}
function dropStopDot(stop){
  if(stop.waypoint){
    const icon=L.divIcon({className:'',html:`<div class="waydot">${stop.icon||'🚉'}</div>`,iconSize:[24*MK,24*MK],iconAnchor:[12*MK,12*MK]});
    L.marker([stop.lat,stop.lon],{icon}).addTo(map); return;
  }
  // 랜드마크 일러스트 아이콘(Sydney Icon Pack 슬러그)이 있으면 지도에 핀처럼 톡 등장
  if(stop.icon && /[a-z]/.test(stop.icon)){
    const html=`<div class="map-sticker"><img src="assets/icons/${stop.icon}.png" alt=""><span class="ms-pin"></span></div>`;
    const icon=L.divIcon({className:'',html,iconSize:[104*MK,98*MK],iconAnchor:[52*MK,92*MK]});
    L.marker([stop.lat,stop.lon],{icon,zIndexOffset:600,interactive:false}).addTo(map);
    return;
  }
  // numbered by visit order among real stops
  const icon=L.divIcon({className:'',html:`<div class="stopdot">${stop.num}</div>`,iconSize:[26*MK,26*MK],iconAnchor:[13*MK,13*MK]});
  L.marker([stop.lat,stop.lon],{icon}).addTo(map);
}

async function showStop(stop, tok){
  const stage=el('#stage');
  // 연출 룰: 출발·결승 등 feature stop = 여러 장 느긋하게 / 러닝 구간 = 1장 빠르게
  const P=DATA.pace||{feature:9,route:1,photo:760,video:3000};
  const isFeat=!!stop.feature;
  const cap=isFeat?(P.feature||9):(P.route||1);
  let photos;
  if(stop.media.length<=cap) photos=stop.media;
  else if(isFeat){            // 시간축 고르게 샘플 → 도착(트램)·중간(어항/식사)·후식까지 다 포함
    photos=[]; for(let k=0;k<cap;k++) photos.push(stop.media[Math.round(k*(stop.media.length-1)/(cap-1))]);
  } else photos=stop.media.slice(0,cap);
  // 핀 미디어(꼭 보여줄 영상 등) 보장 — 스프레드에서 빠졌으면 추가하고 시간순 유지
  const pins=(DATA.pin||[]);
  if(pins.length){
    stop.media.forEach(m=>{ const id=(m.video||m.file||'');
      if(pins.some(p=>id.includes(p.replace(/\.[^.]+$/,''))) && !photos.includes(m)) photos.push(m); });
    photos.sort((a,b)=>stop.media.indexOf(a)-stop.media.indexOf(b));
  }
  for(let i=0;i<photos.length;i++){
    if(tok!==cancelToken) return;
    const m=photos[i];
    const isVid=m.type==='video';
    const dwell=EXPORT
      ? (isVid?(P.video||3000):(isFeat?(P.photo||780):560))   // 테마 페이싱(영상은 끝까지)
      : (isVid?3000:(isFeat?1300:1100));
    const rot=(Math.sin(stop.id*3+i*1.7)*4).toFixed(1);
    const card=document.createElement('div');
    card.className='polaroid';
    card.style.transform=`translateY(24px) rotate(${rot}deg) scale(.96)`;
    const inner = isVid
      ? `<video src="${m.video}" poster="${mediaSrc(m)}" muted playsinline loop autoplay></video><div class="vtag">▶ 2x</div>`
      : `<img src="${mediaSrc(m)}" alt="">`;
    card.innerHTML=`<div class="badge">${stop.name} · ${m.time}</div>${inner}<div class="cap">${stop.name}</div>`;
    stage.appendChild(card);
    if(isVid){ const v=card.querySelector('video'); if(v){ v.playbackRate=2; v.play().catch(()=>{}); } }
    requestAnimationFrame(()=>{ card.style.opacity='1'; card.style.transform=`translateY(0) rotate(${rot}deg) scale(1)`; });
    await sleep(dwell);
    if(tok!==cancelToken){ card.remove(); return; }
    card.style.opacity='0'; card.style.transform=`translateY(-18px) rotate(${rot}deg) scale(.97)`;
    setTimeout(()=>card.remove(),500);
  }
}

function markTrack(i){
  document.querySelectorAll('#track .t').forEach((d,j)=>{
    d.classList.toggle('done', j<=i); d.classList.toggle('cur', j===i);
  });
}
function setChip(stop, mode){
  const m=MODE[mode]||MODE.walk;
  el('#chip .mode').textContent=m.emoji;
  el('#chip .place').textContent=stop.name;
  el('#chip .time').textContent=stop.t0;
  el('#tint').style.background=tintFor(stop.t0);
}

async function play(){
  if(running) return; running=true;
  const tok=++cancelToken;
  el('#intro').classList.add('hide'); el('#outro').classList.add('hide');
  el('#bar').classList.add('show'); el('#chip').classList.add('show');
  trail.setLatLngs([]); el('#stage').innerHTML='';

  const stops=DATA.stops, legs=DATA.legs;
  const first=stops[0];
  placeTraveler([first.lat,first.lon], 'start');
  trail.setLatLngs([[first.lat,first.lon]]);
  const firstWp=first.waypoint;     // 비행 출발지 등 미디어 없는 경유지면 오프닝 짧게(죽은 시간 제거)
  const firstFly=DATA.legs[0] && DATA.legs[0].mode==='flight';
  if(firstWp && firstFly){          // 비행 출발: 줌아웃 애니메이션(가장자리 타일 깨짐) 대신 항로 전체로 컷
    map.fitBounds(L.latLngBounds(DATA.legs[0].geom), {paddingTopLeft:[90,150], paddingBottomRight:[90,230], animate:false});
  } else {
    map.flyTo([first.lat,first.lon], MODE.start.zoom+ZB, {duration:firstWp?0.8:1.2});
  }
  await sleep(firstWp?(EXPORT?450:600):1300);
  if(EXPORT) await waitTiles(1800);   // 출발 뷰 타일 로드 완료 후 진행(헤드리스 깨짐 방지)
  if(tok!==cancelToken) return;
  setChip(first,'start'); markTrack(first.num-1); dropStopDot(first);
  if(first.icon && /[a-z]/.test(first.icon)) await sleep(EXPORT?800:650);
  await showStop(first, tok); if(tok!==cancelToken) return;

  for(let i=0;i<legs.length;i++){
    if(tok!==cancelToken) return;
    const lg=legs[i], B=stops[i+1];
    const z=(MODE[lg.mode]||MODE.walk).zoom+ZB;
    const isFly=lg.mode==='flight';
    const framed=(i===0 && firstWp && firstFly);   // 출발지 establish가 이미 항로 전체를 잡음
    if(isFly){ if(!framed) map.fitBounds(L.latLngBounds(lg.geom), {paddingTopLeft:[90,150], paddingBottomRight:[90,230], animate:false}); }
    else map.flyTo(lg.geom[0], z, {duration:.6});
    await sleep(EXPORT?(isFly?(framed?250:700):300):(isFly?800:450));
    if(isFly && EXPORT && !framed) await waitTiles(1500);
    if(tok!==cancelToken) return;
    if(lg.mode==='train') dropRailStations(lg);
    const dur = lg.mode==='flight' ? (EXPORT?3200:3800)
              : (lg.mode==='train'||lg.mode==='tram') ? (EXPORT?2200:3200)
              : lg.mode==='ferry' ? (EXPORT?1800:2800)
              : (EXPORT?Math.min(1500,700+lg.geom.length*9):Math.min(2600,1100+lg.geom.length*14));
    await travelLeg(lg.geom, lg.mode, dur, tok);
    if(tok!==cancelToken) return;
    if(isFly && !B.waypoint){                              // 비행 후엔 arc 줌 → 도착 도시로 '컷'(애니메이션 줌은 트레일이 번져서 과함 → 스냅)
      map.setView([B.lat,B.lon], 12+ZB, {animate:false});
      if(EXPORT) await waitTiles(1800);                    // 도착 도시 타일 로드 완료까지(깨짐 방지)
      await sleep(EXPORT?250:500); if(tok!==cancelToken) return; }
    if(!B.waypoint) placeTraveler([B.lat,B.lon],'walk');   // 도착하면 내려서 사람으로
    setChip(B, lg.mode); dropStopDot(B);
    if(B.waypoint){ await sleep(EXPORT?550:900); }          // 환승역 등은 잠깐 지나감
    else {
      markTrack(B.num-1);
      if(B.icon && /[a-z]/.test(B.icon)) await sleep(EXPORT?800:650);   // 랜드마크 아이콘이 톡 등장하는 순간을 보여줌
      await showStop(B, tok);
    }
  }
  if(tok!==cancelToken) return;
  running=false; await sleep(400);
  el('#chip').classList.remove('show'); el('#bar').classList.remove('show');
  const oc=el('#outro'); oc.classList.remove('hide');
  oc.classList.remove('go'); void oc.offsetWidth; oc.classList.add('go');   // 아웃트로 뜰 때 스탬프·컬렉션 쾅쾅 재생
  if(EXPORT){ await sleep(3200); window.__exportDone = true; }   // 녹화 종료 신호
}

let paused=false;
el('#start').onclick=()=>play();
el('#replay').onclick=()=>location.reload();
el('#playpause').onclick=()=>{
  paused=!paused; el('#playpause').textContent=paused?'▶':'❚❚';
  if(paused){ cancelToken++; running=false; } else { play(); }
};

boot();
