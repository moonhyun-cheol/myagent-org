# myagent-org

**1.0.0-beta.1** · seq **5** · [`moonhyun-cheol/myagent-org`](https://github.com/moonhyun-cheol/myagent-org)

MY Agent 조직 모듈만 다룹니다. 앱 본체는 [`myagent`](https://github.com/moonhyun-cheol/myagent)입니다.

| | |
|---|---|
| 소스 | `agent-module/` (스킬, 컨셉 RA, 시장조사, 브랜드 데이터) |
| 버전 | `manifest.json` · [repo-target.json](repo-target.json) |
| 1.4 보관본 이식 | [PORT.md](PORT.md) |

설정 → 스킬에서 이 저장소 릴리스 zip을 한 번 고르면 설치됩니다. 이후 앱이 켜질 때 seq가 더 큰 모듈 zip만 자동 적용합니다. `.chroma` / Excel / NAS 추출은 git에 넣지 않습니다.

```bash
npm run verify:module-pack
npm run publish:update
```

서명 개인키는 `tools/keys/` (커밋 금지).
