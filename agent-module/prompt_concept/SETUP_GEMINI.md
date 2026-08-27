# Gemini 설정 (1분)



1. [Google AI Studio](https://aistudio.google.com) → **Build** → **Create Gem**

2. Name: `CQR Brand Image Concierge`

3. **Instructions**에 `MY_prompt_gemini.md` **전체 붙여넣기**

4. Knowledge 파일 첨부 **하지 않음** (중복 충돌 방지)

5. 저장 후 새 채팅



## 테스트



```

CQ-TLP125-SGN 촬영 컨셉

```



```

TLP710-ONV .art

```



```

(listing 이미지 2장 첨부) B0CFQ571ND .art PT01 PT02만

```



```

(AI 결과 업로드) QC — CQR 브랜드에 맞나?

```



## Imagen



`.art` 답변의 **📝 EN prompt**를 Imagen에 붙이거나, Gem에서 "PT02 EN prompt로 이미지 생성" 요청.



## 갱신



```powershell

python scripts/build_platform_prompts.py

```



→ `MY_prompt_gemini.md` 다시 붙여넣기

