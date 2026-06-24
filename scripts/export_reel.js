// 하루 여행기 → 인스타 릴스용 세로(9:16) MP4 녹화
// 사용법: node scripts/export_reel.js [port] [outfile]
//   (stroll 미리보기 서버가 떠 있어야 함. 기본 포트 4611)
// 흐름: 시스템 Chrome(헤드리스)로 ?export=1 페이지를 녹화(webm) → ffmpeg로 1080x1920 mp4 변환
const puppeteer = require('puppeteer-core');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const PORT = process.argv[2] || '4611';
const OUT = path.resolve(process.argv[3] || 'stroll/exports/sydney-reel.mp4');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const URL = `http://localhost:${PORT}/?export=1`;

(async () => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  const webm = OUT.replace(/\.mp4$/, '.webm');

  console.log('▶ Chrome 실행 (headless)…');
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--autoplay-policy=no-user-gesture-required', '--hide-scrollbars',
           '--mute-audio', '--no-sandbox'],
  });
  const page = await browser.newPage();
  // 9:16 네이티브 1080x1920로 캡처 (screencast는 CSS 크기로 캡처 → 처음부터 1080으로)
  // dsf 1: 네이티브 1080이라 이미 또렷 + 타일 부담을 줄여 팬 중 끊김 방지
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });

  console.log(`▶ 페이지 로드: ${URL}`);
  await page.goto(URL, { waitUntil: 'load', timeout: 60000 });
  await new Promise(r => setTimeout(r, 1500));            // 초기 타일 로드
  console.log('▶ 경로 타일 프리로드(블럭팝 방지)…');
  try { await page.evaluate(() => window.__preloadRoute && window.__preloadRoute()); }
  catch (e) { console.log('  프리로드 건너뜀:', e.message); }
  await new Promise(r => setTimeout(r, 500));             // 시작 뷰 안정화

  console.log('● 녹화 시작…');
  const recorder = await page.screencast({ path: webm });
  // 녹화가 실제로 돌기 시작한 뒤 훅을 트리거 → Beat1(타이틀)부터 온전히 캡처
  await new Promise(r => setTimeout(r, 500));
  await page.evaluate(() => { window.__exportDone = false; window.__startReel && window.__startReel(); });

  console.log('… 애니메이션 진행 중 (끝나면 자동 종료)');
  await page.waitForFunction('window.__exportDone === true', { timeout: 240000, polling: 500 });
  await new Promise(r => setTimeout(r, 400));
  await recorder.stop();
  await browser.close();
  console.log('■ 녹화 완료:', webm);

  console.log('▶ ffmpeg 변환 → 인스타 규격 mp4 (1080x1920, H.264 고화질)…');
  // 캡처가 이미 1080x1920이므로 업스케일 없음 — 고화질 재인코딩만
  // 훅 구간(t<=3.0s, 인트로 단축)에만 밝기/채도 보정 → 히어로·칩 쨍하게 (지도/다른 사진은 그대로)
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', webm,
    '-vf', "scale=1080:1920:flags=lanczos,eq=gamma=1.4:saturation=1.25:contrast=1.05:enable='lte(t\\,3.0)',eq=saturation=1.13:contrast=1.04:enable='gt(t\\,3.0)',fps=30",
    '-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-crf', '17',
    '-preset', 'slow', '-movflags', '+faststart', OUT], { stdio: 'inherit' });
  fs.unlinkSync(webm);

  const mb = (fs.statSync(OUT).size / 1024 / 1024).toFixed(1);
  console.log(`\n✅ 완성 → ${OUT}  (${mb} MB)`);
})().catch(e => { console.error('실패:', e); process.exit(1); });
