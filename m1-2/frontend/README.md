# 프런트엔드

의존성 없는 ES Module 기반 정적 화면입니다. 브라우저 번들에는 공개 `API_BASE_URL`만 들어갑니다.

```powershell
node --test
$env:API_BASE_URL="http://localhost:8000"
node scripts/build.mjs
```

일반 Node/npm 환경에서는 `npm test`, `npm run build`를 사용합니다. Vercel의 Root Directory는 `m1-2/frontend`, Output Directory는 `dist`입니다.
