# Claude 설정 (1분)

1. [claude.ai](https://claude.ai) → **Projects** → **New project**
2. Name: `CQR Concept Concierge`
3. **Project instructions**에 `MY_prompt_claude.md` **전체 붙여넣기**
4. Project Knowledge 첨부 **불필요** (본문에 embed됨)
5. 프로젝트 안에서 새 채팅

## 테스트

```
TLP125-SGN .ff
```

```
(listing 이미지 첨부) CQ-TLP125-SGN .art
```

```
Covert urban pant 신규 .dev
```

## 이미지 생성

Claude는 **이미지를 그리지 않음**. **📝 EN prompt**를 Midjourney / DALL-E / Flux / Gemini Imagen에 복사.

## 갱신

```powershell
python scripts/build_platform_prompts.py
```

→ `MY_prompt_claude.md` 다시 붙여넣기
