# MY Agent 관리자 — 업데이트 채널 이전 안내 (운영자용)

**대상 독자:** MY Agent 관리자(코드명 `WorkKitLauncher`)를 이미 설치해 운영 중인 담당자.
**요약:** 관리자 프로그램의 배포·자동업데이트 채널이 앱 본체 저장소에서 조직 저장소(`moonhyun-cheol/myagent-org`)로 이전됐습니다. **구 설치분은 이 채널로 자동 이전되지 않으므로 1회 재설치가 필요합니다.**

## 왜 재설치가 필요한가

- 구 설치분은 예전 피드(앱 본체 `moonhyun-cheol/myagent`의 launcher 채널)를 바라봅니다.
- 신규 채널은 조직 저장소의 `manager/channels/launcher-stable.json`이며, 구 설치분은 이 새 피드로 **자동 전환되지 않습니다.**
- 따라서 자동 업데이트로는 신규 릴리즈(v1.0.10 / sequence 5)를 받을 수 없고, **새 install-zip으로 한 번 재설치**해야 이후부터 정상적으로 자동 업데이트가 이어집니다.

## 신규 배포 정보 (현재 릴리즈)

| 항목 | 값 |
|------|------|
| 저장소 | `moonhyun-cheol/myagent-org` |
| 릴리즈 태그 | `launcher-update-5` |
| 버전 / 시퀀스 | `1.0.10` / `5` |
| 설치 파일 | `WorkKitLauncher-v1.0.10-install.zip` |
| 업데이트 파일 | `WorkKitLauncher-v1.0.10-update-5.zip` |
| 업데이트 zip SHA-256 | `69cddfadf46af85359e08dde7699d54007218c4c2a7aff0b4d54638e71833103` |
| 서명 알고리즘 | RSA-PSS-SHA256 |
| 피드 URL | `https://raw.githubusercontent.com/moonhyun-cheol/myagent-org/main/manager/channels/launcher-stable.json` |

> 서명 검증은 설치된 MY Agent 본체의 `core/config/defaults/update-public.pem` 공개키로 이뤄집니다.

## 재설치 절차 (운영자)

1. 실행 중인 기존 MY Agent 관리자를 종료합니다.
2. 신규 릴리즈에서 `WorkKitLauncher-v1.0.10-install.zip`을 내려받습니다.
   - `https://github.com/moonhyun-cheol/myagent-org/releases/tag/launcher-update-5`
3. 압축을 풀고 설치(또는 기존 설치 위치에 덮어쓰기)합니다.
4. 관리자를 실행하면 신규 채널을 바라보게 되며, 이후 업데이트는 자동 적용됩니다.
5. (선택) 무결성 확인: 내려받은 zip의 SHA-256이 위 표의 값과 일치하는지 검증합니다.

```powershell
Get-FileHash .\WorkKitLauncher-v1.0.10-update-5.zip -Algorithm SHA256
# 기대값: 69cddfadf46af85359e08dde7699d54007218c4c2a7aff0b4d54638e71833103
```

## 로컬 API 전제

- 관리자 프로그램은 별도 서버 없이 로컬 MY Agent Core(`127.0.0.1`, 기본 포트 `10200`, `/profiles`·`/organization-module`)를 재사용합니다.
- 따라서 MY Agent 본체가 동일 PC에 정상 설치·기동돼 있어야 합니다.

## 주의

- 이 이전은 **운영자용 관리자 프로그램** 트랙입니다. 코어 제품(`myagent`)의 「관리자→설정 합치기」 방향과는 별개이며, 코어에 런처를 재도입하지 않습니다.
- 조직 모듈/작업 키트 카탈로그 피드 병합은 이 작업 범위 밖입니다.
