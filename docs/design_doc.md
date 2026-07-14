# 보험상품 AI Knowledge Platform — 프로젝트 설계 문서

버전: v0.2 | 작성일: 2026-07-13
목적: 국내 손해보험사 상품 공시자료를 자동 수집·구조화·AI 가공하여, 단순 자료 저장소가 아닌
**보험상품 AI Knowledge Platform**(FAQ AI / RAG의 지식 기반)을 구축·유지한다.

v0.2 변경사항 요약:
- **AI Knowledge Builder 레이어** 신설 (구조화 JSON → AI 산출물 자동 생성)
- **공통 표준 스키마(Canonical Schema)** 도입 — 전사 비교 질문 대응
- 최종 목표를 "PDF 저장소"에서 "AI Knowledge Platform"으로 재정의, 전체 아키텍처 반영

---

## ① 전체 시스템 아키텍처

시스템을 6개 레이어로 재구성한다. 기존 대비 **Knowledge Builder 레이어**가 신설되어,
Processing(가공) 레이어의 산출물(JSON)을 입력으로 받아 FAQ AI가 바로 활용할 수 있는
2차 지식 산출물을 생성한다. 이 레이어가 이 시스템을 "자료 보관소"가 아닌
"AI Knowledge Platform"으로 만드는 핵심이다.

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Collection Layer (수집)                                    │
│    - Playwright 기반 보험사별 크롤러 (어댑터 패턴)               │
├─────────────────────────────────────────────────────────────┤
│ 2. Ingestion Layer (적재)                                      │
│    - PDF 다운로드 / 무결성 검증(해시) / 원본 저장                 │
├─────────────────────────────────────────────────────────────┤
│ 3. Processing Layer (가공)                                     │
│    - Text/OCR 추출 → 섹션 파싱 → 상품별 JSON 구조화              │
│    - 회사별 원 스키마(raw schema) 생성                          │
├─────────────────────────────────────────────────────────────┤
│ 4. Standardization Layer (표준화) ★ 신설                       │
│    - 회사별 JSON → 공통 표준 스키마(Canonical Schema) 매핑        │
│    - 가입연령/보험기간/납입기간/보장내용/면책/감액/납입면제/갱신여부 등│
├─────────────────────────────────────────────────────────────┤
│ 5. AI Knowledge Builder Layer (AI 지식 생성) ★ 신설             │
│    - 표준화 데이터 → LLM 기반 2차 산출물 자동 생성                │
│    - 요약 / 판매포인트 / 고객FAQ / 설계사FAQ / 경쟁비교 / 개정요약  │
├─────────────────────────────────────────────────────────────┤
│ 6. Knowledge Base & Serving Layer (지식베이스·활용)              │
│    - Metadata DB, Chunk Store, (향후) Vector Store             │
│    - ChatGPT Project export / RAG(Dify, Azure AI Search 등) 연동│
└─────────────────────────────────────────────────────────────┘
```

핵심 설계 원칙 (기존 유지 + 추가):
- 회사별 크롤러는 공통 인터페이스를 구현하는 플러그인으로 취급한다.
- 수집 → 가공 → 표준화 → AI 생성은 **철저히 단계 분리**한다. 특정 단계 실패가 이전 단계 산출물을 훼손하지 않는다.
- **모든 AI 생성물은 "원문 근거(source)"를 함께 저장**한다 — 표준화 스키마 필드 또는 청크 단위로 출처를 추적할 수 있어야 한다 (금융상품 정보이므로 환각(hallucination) 방지가 최우선 원칙).
- **AI 생성물은 별도 산출물로 저장**하고 원본 구조화 데이터(JSON)를 덮어쓰지 않는다 — 재생성/재검수가 언제든 가능하도록.
- 표준화 스키마는 회사 확장(20개사 이상)에도 필드가 깨지지 않도록 **선택적(optional) 필드 + 결측 허용** 구조로 설계한다.

---

## ② 전체 데이터 흐름 (Data Flow)

```
[1] 보험사 공시 페이지 목록 (설정 파일 기반)
        ↓
[2] Playwright 크롤러 실행 (회사별 어댑터)
        ↓
[3] 변경 감지 (신규/변경/동일 판단)
        ↓
[4] PDF 다운로드 → 원본 저장 (Raw Storage)
        ↓
[5] 텍스트/OCR 추출
        ↓
[6] 구조화 파서 → 회사별 Raw JSON 생성
        ↓
[7] ★ 표준화(Standardization) — Raw JSON → Canonical Schema 매핑
        ↓
[8] ★ AI Knowledge Builder 실행
        ├─ 상품 핵심 요약 생성
        ├─ 판매 포인트 생성
        ├─ 예상 고객 질문 FAQ 생성
        ├─ 보험설계사 FAQ 생성
        ├─ 경쟁사 비교 포인트 생성 (동일 카테고리 내 타사 표준 데이터 참조)
        └─ 상품 개정 변경사항 요약 생성 (신·구 버전 diff 기반)
        ↓
[9] Metadata DB 기록 (원본 이력 + AI 산출물 이력 + 생성 모델/프롬프트 버전)
        ↓
[10] Chunking (원문 Chunk + AI 생성 Chunk 분리 저장)
        ↓
[11] Knowledge Base 저장
        ↓
[12] Export (ChatGPT Project / RAG 연동)
```

설계 포인트:
- **[7] 표준화 단계가 [8] AI Knowledge Builder의 입력 품질을 좌우**한다. 표준화가 안 된 상태로 AI에 원문을 통째로 넘기면 비교 질문 품질이 떨어지므로, 표준화 → AI 생성 순서를 반드시 지킨다.
- **경쟁사 비교 포인트**는 AI가 임의로 생성하지 않고, 표준화 스키마상 동일 필드를 가진 타사 데이터를 실제로 조회하여 그 값을 근거로 생성하도록 한다(자유 서술이 아닌 근거 기반 비교).
- **개정 변경사항 요약**은 ⑦ 변경 감지에서 생성되는 신·구 버전 diff를 AI가 자연어로 요약하는 방식 — 자유 생성이 아니라 diff 결과를 입력으로 주는 grounded 생성.

---

## ③ 폴더 구조 (업데이트)

```
insurance-faq-kb/
├── config/
│   ├── companies/                  # 보험사별 설정 (YAML)
│   ├── schema/
│   │   └── canonical_schema.yaml   # ★ 표준 스키마 정의
│   ├── prompts/                    # ★ AI Knowledge Builder 프롬프트 템플릿
│   │   ├── summary_prompt.yaml
│   │   ├── selling_point_prompt.yaml
│   │   ├── customer_faq_prompt.yaml
│   │   ├── agent_faq_prompt.yaml
│   │   ├── comparison_prompt.yaml
│   │   └── revision_summary_prompt.yaml
│   └── settings.yaml
│
├── src/
│   ├── crawlers/ ...
│   ├── downloader/ ...
│   ├── change_detection/ ...
│   ├── extraction/ ...
│   ├── structuring/ ...
│   ├── standardization/            # ★ 신설
│   │   ├── schema_mapper.py        # 회사별 raw → canonical 매핑
│   │   └── field_normalizer.py     # 단위/표현 정규화 (세, 년, 만원 등)
│   ├── knowledge_builder/          # ★ 신설
│   │   ├── summary_generator.py
│   │   ├── selling_point_generator.py
│   │   ├── customer_faq_generator.py
│   │   ├── agent_faq_generator.py
│   │   ├── comparison_generator.py
│   │   ├── revision_summary_generator.py
│   │   └── qa_reviewer.py          # 생성물 품질/근거 검증
│   ├── chunking/ ...
│   ├── metadata/ ...
│   ├── storage/ ...
│   ├── export/ ...
│   └── orchestration/
│       └── pipeline_runner.py
│
├── data/
│   ├── raw/
│   ├── extracted_text/
│   ├── structured/                 # 회사별 Raw JSON
│   ├── standardized/               # ★ Canonical Schema JSON
│   │   └── {category}/{product_id}.json
│   ├── knowledge/                  # ★ AI Knowledge Builder 산출물
│   │   └── {company}/{product_id}/
│   │       ├── summary.json
│   │       ├── selling_points.json
│   │       ├── customer_faq.json
│   │       ├── agent_faq.json
│   │       ├── comparison.json
│   │       └── revision_summary.json
│   ├── chunks/
│   │   ├── source_chunks/          # 원문 기반 chunk
│   │   └── ai_generated_chunks/    # ★ AI 산출물 기반 chunk
│   └── exports/
│
├── db/
│   └── metadata.db
├── logs/
├── tests/
└── docs/
```

---

## ④ 모듈 구조 (업데이트)

기존 모듈에 더해 아래 모듈을 추가한다.

| 모듈 | 책임 | 비고 |
|---|---|---|
| `schema_mapper.py` | 회사별 Raw JSON을 Canonical Schema로 매핑 | 회사마다 용어가 달라 매핑 규칙을 YAML로 관리 |
| `field_normalizer.py` | "만 15세~65세", "15~65세" 등 표현 차이를 표준 값으로 정규화 | 비교 질문 정확도의 핵심 |
| `summary_generator.py` | 상품 핵심 요약(3~5문장) 생성 | 표준화 데이터 + 원문 발췌 근거 기반 |
| `selling_point_generator.py` | 판매 포인트(설계사/마케팅 관점) 생성 | 과장 표현 방지를 위한 가드레일 프롬프트 필요 |
| `customer_faq_generator.py` | 예상 고객 질문 FAQ 생성 | Q&A 쌍 + 근거 페이지 포함 |
| `agent_faq_generator.py` | 보험설계사 관점 FAQ 생성 (인수기준, 감액·면책 조건 등 실무 질문) | 고객용보다 전문적 톤 |
| `comparison_generator.py` | 동일 카테고리 타사 표준 데이터 조회 후 비교 포인트 생성 | 표준화 레이어 없이는 불가능 → ④ 표준화가 선행 조건 |
| `revision_summary_generator.py` | 신·구 버전 diff → 개정 변경사항 자연어 요약 | diff 데이터를 grounding 소스로 사용 |
| `qa_reviewer.py` | AI 생성물의 근거(citation) 존재 여부, 스키마 값과의 정합성 자동 점검 | 불일치 시 human review 큐로 전송 |

---

## ⑤ 필요한 Python 라이브러리 (추가분)

기존 라이브러리(Playwright, PyMuPDF, pdfplumber, pytesseract, pydantic, sqlalchemy 등)에 더해:

| 목적 | 라이브러리 | 비고 |
|---|---|---|
| LLM 호출 (AI Knowledge Builder) | `openai` / `anthropic` SDK | 요약, FAQ, 비교 생성 |
| 프롬프트 템플릿 관리 | `jinja2` | 프롬프트를 코드와 분리하여 YAML+템플릿으로 관리 |
| 구조화 출력 강제 | `pydantic` (기존과 동일 라이브러리, 용도 확장) | LLM 출력의 JSON 스키마 검증 |
| 텍스트 유사도 비교 (근거 검증용) | `rapidfuzz` | 생성 문장이 원문 근거와 얼마나 일치하는지 간이 점검 |
| 배치/재시도 처리 | `tenacity` | LLM API 호출 실패 시 재시도 |

---

## ⑥ ~ ⑧ (기존과 동일 — 변경 없음)

크롤링 전략(⑥), 변경 감지(⑦), PDF 관리 전략(⑧)은 기존 설계를 그대로 유지한다.
다만 ⑦ 변경 감지의 산출물(신·구 버전 diff)이 이제 **AI Knowledge Builder의 입력 데이터**로도
쓰이는 점이 추가된다 (⑧-2 참고, ②의 [8] 참고).

---

## ⑨ JSON 구조 설계 (업데이트 — 표준 스키마 신설)

### 9-1. 회사별 Raw JSON (기존과 동일, v0.1 참고)
회사별 페이지/문서 구조를 그대로 반영한 1차 구조화 결과. 표준화의 입력값 역할만 수행.

### 9-2. 공통 표준 스키마 (Canonical Schema) ★ 신설

모든 보험사·모든 상품이 아래 표준 필드로 매핑된다. 회사마다 존재하지 않는 필드는 `null`로
허용하며, 회사별 표현 차이는 `field_normalizer`가 정규화한다.

```
{
  "product_id": "samsung_fire_health_001",
  "company": "삼성화재",
  "category": "건강보험",
  "version": 3,

  "canonical": {
    "가입연령": { "min_age": 15, "max_age": 65, "unit": "만 나이", "raw_text": "..." },
    "보험기간": { "value": "80세만기", "raw_text": "..." },
    "납입기간": { "options": ["10년납", "20년납", "전기납"], "raw_text": "..." },
    "갱신여부": { "is_renewal": true, "renewal_cycle": "3년" },
    "보장내용": [
      { "담보명": "암진단비", "지급금액": "3000만원", "지급조건": "...", "raw_text": "..." }
    ],
    "면책사항": { "text": "...", "raw_text": "..." },
    "감액지급": { "text": "...", "raw_text": "..." },
    "납입면제": { "조건": "...", "raw_text": "..." }
  },

  "field_mapping_confidence": 0.92,
  "unmapped_fields": ["특약결합조건"],
  "source_ref": {
    "raw_json_path": "structured/samsung_fire/health_001.json",
    "pages": { "가입연령": [2], "보장내용": [3, 4] }
  },
  "created_at": "2026-07-13T10:00:00"
}
```

설계 의도:
- `canonical` 블록만 보면 **회사가 달라도 동일한 필드로 비교 가능** — "DB손보와 삼성화재의 암진단비 차이는?" 같은 질문에 바로 대응.
- `raw_text`를 필드마다 남겨 정규화 과정의 손실을 검증할 수 있게 함.
- `unmapped_fields`로 표준화가 안 된 항목을 추적하여 스키마 보완 대상 파악.
- `field_mapping_confidence`가 낮은 상품은 AI Knowledge Builder 실행 전 검수 큐로 우선 전송.

### 9-3. AI Knowledge Builder 산출물 스키마 ★ 신설

산출물 종류별로 파일을 분리 저장한다 (④ 폴더 구조의 `data/knowledge/` 참고). 공통 포맷:

```
{
  "product_id": "samsung_fire_health_001",
  "type": "customer_faq",              // summary | selling_point | customer_faq |
                                        // agent_faq | comparison | revision_summary
  "generated_at": "2026-07-13T11:00:00",
  "model": "claude-sonnet-4-6",
  "prompt_version": "customer_faq_v1.2",
  "content": [
    {
      "question": "이 보험은 몇 살까지 가입할 수 있나요?",
      "answer": "만 15세부터 65세까지 가입할 수 있습니다.",
      "source_field": "canonical.가입연령",
      "source_page": [2]
    }
  ],
  "review_status": "auto_approved",     // auto_approved | needs_review | approved | rejected
  "confidence": 0.9
}
```

설계 의도:
- `source_field`로 AI 답변이 **표준 스키마의 어느 필드에서 나왔는지 추적** — 환각 여부 검증의 핵심 근거.
- `prompt_version`을 남겨 프롬프트 개선 시 이전/이후 산출물 비교 가능 (A/B 및 회귀 확인).
- `review_status`로 사람 검수 워크플로우 연결 (⑭ 유지보수 전략 참고).
- 경쟁사 비교(`comparison`)의 경우 `content`에 비교 대상 회사·상품 ID를 함께 명시하여 근거 재현 가능하게 함.

---

## ⑩ Metadata 설계 (업데이트)

기존 3개 테이블(`products`, `product_versions`, `crawl_logs`)에 아래 테이블을 추가한다.

**테이블: `standardized_products`**
| 컬럼 | 설명 |
|---|---|
| product_id | FK (products) |
| version_id | FK (product_versions) |
| canonical_json_path | 표준화 JSON 경로 |
| mapping_confidence | 표준화 신뢰도 |
| unmapped_field_count | 미매핑 필드 수 (스키마 보완 우선순위 판단용) |

**테이블: `knowledge_artifacts`** ★ 신설
| 컬럼 | 설명 |
|---|---|
| artifact_id | PK |
| product_id | FK |
| version_id | FK |
| artifact_type | summary / selling_point / customer_faq / agent_faq / comparison / revision_summary |
| file_path | 산출물 파일 경로 |
| model | 사용된 LLM 모델명 |
| prompt_version | 프롬프트 버전 |
| review_status | auto_approved / needs_review / approved / rejected |
| generated_at | 생성 시각 |

**테이블: `review_queue`** ★ 신설
| 컬럼 | 설명 |
|---|---|
| queue_id | PK |
| artifact_id | FK |
| reason | low_confidence / mapping_incomplete / flagged_by_qa_reviewer |
| assigned_to | 검수 담당자 (선택) |
| resolved_at | 처리 완료 시각 |

이 구조로 "AI가 생성한 FAQ 중 아직 사람 검수가 안 된 것", "특정 프롬프트 버전 이후 품질 변화" 등을
쿼리로 추적할 수 있다.

---

## ⑪ FAQ 생성을 고려한 데이터 저장 구조 (업데이트)

Chunk를 **출처 성격에 따라 2종류로 분리 저장**한다.

1. **Source Chunk (원문 기반)**: 기존 v0.1 설계와 동일. PDF 원문 섹션을 그대로 청크화.
2. **AI Generated Chunk (AI 산출물 기반)** ★ 신설: `knowledge_artifacts`의 각 산출물(요약/FAQ/비교/개정요약)을 청크 단위로 변환. 이 chunk가 실제 FAQ 응답 생성 시 1차 검색 대상이 되고, Source Chunk는 근거 보강/검증용으로 함께 조회된다.

```
{"chunk_id": "...", "product_id": "...", "company": "삼성화재",
 "category": "건강보험", "chunk_source": "ai_generated",
 "artifact_type": "customer_faq", "version": 3,
 "text": "Q: 이 보험은 몇 살까지 가입할 수 있나요? A: 만 15세부터 65세까지...",
 "source_field": "canonical.가입연령", "source_page": [2]}
```

비교 질문(전사 비교) 대응은 표준 스키마(⑨-2)를 기준으로 인덱싱하므로, "건강보험 카테고리의
전 보험사 가입연령"과 같은 조회가 별도 AI 호출 없이 구조화 데이터만으로도 가능하다 — AI는
이를 자연어로 다듬는 역할만 수행한다(할루시네이션 위험 최소화).

---

## ⑫ ChatGPT Project / RAG 연동 구조 (업데이트)

- Export 대상이 원문 Chunk뿐 아니라 **AI Knowledge Builder 산출물(요약/FAQ/비교/개정요약)**로 확대된다.
- `chatgpt_export.py`는 회사·카테고리별로 (a) 표준화 스키마 요약본 + (b) AI 생성 FAQ 묶음을 함께 export하여, Knowledge 업로드만으로 비교 질문까지 답변 가능하도록 구성.
- `rag_export.py`는 Source Chunk와 AI Generated Chunk를 **별도 인덱스(또는 메타데이터 필드로 구분)** 로 색인하여, RAG 검색 시 "AI 생성 요약 우선 검색 → 필요 시 원문 근거 보강" 전략을 구현할 수 있게 한다.
- 모든 export 산출물에는 `review_status`가 `approved` 또는 `auto_approved`인 것만 포함하는 것을 기본 정책으로 한다 (미검수 산출물의 외부 노출 방지).

---

## ⑬ 예상되는 기술적 문제 (추가분)

기존 v0.1의 문제 목록에 더해, AI Knowledge Builder 신설에 따른 문제를 추가한다.

| 문제 | 설명 | 대응 방향 |
|---|---|---|
| LLM 환각(Hallucination) | AI가 표준 스키마에 없는 내용을 지어낼 위험 (특히 판매포인트, 비교 포인트) | 모든 생성 프롬프트에 "제공된 데이터 외 내용 생성 금지" 명시 + `qa_reviewer.py`로 근거 필드 존재 여부 자동 검증 |
| 표준화 매핑 오류 | 회사별 용어 차이로 인한 잘못된 필드 매핑 (예: "면책기간"과 "감액기간" 혼동) | 매핑 규칙에 대한 회사별 검토, `mapping_confidence` 낮은 건 AI 생성 이전 단계에서 차단 |
| 판매 포인트의 과장/오인 소지 | 규제 대상 산업 특성상 "판매 포인트"가 불완전판매성 표현이 될 위험 | 보수적 톤 가드레일 프롬프트 + 배포 전 사람 검수 필수화(자동 승인 대상에서 제외 검토) |
| LLM 호출 비용/속도 | 상품 수 × 산출물 6종 × 회사 확장 시 비용 급증 | 변경된 상품만 재생성(버전 변경 시에만 호출), 캐싱 전략 |
| 비교 생성의 데이터 편향 | 특정 회사 데이터가 상세하고 타사가 부실할 경우 비교가 왜곡될 수 있음 | `unmapped_fields` 비교하여 비교 불가능한 항목은 "정보 없음"으로 명시, 억지 비교 금지 |
| 프롬프트 버전 관리 누락 시 회귀 추적 불가 | 프롬프트 수정 후 품질 저하를 알아채기 힘듦 | `prompt_version` 필수 기록 + 샘플 상품에 대한 회귀 테스트 세트 유지 |

---

## ⑭ 유지보수 전략 (추가분)

기존 전략에 더해:

- **Human-in-the-loop 검수 워크플로우**: `review_queue` 테이블 기반으로 낮은 신뢰도/특정 산출물 유형(특히 판매 포인트, 경쟁사 비교)은 기본적으로 `needs_review` 상태로 시작하고, 사람이 승인해야 `approved`로 전환되어 Export 대상에 포함.
- **프롬프트 회귀 테스트 세트**: 대표 상품 10~20개를 고정 샘플로 두고, 프롬프트 변경 시마다 산출물 품질(근거 일치율 등)을 비교.
- **표준 스키마 버전 관리**: 신규 필드가 필요해지면(예: 새로운 담보 유형) `canonical_schema.yaml`에 버전을 부여하여 하위 호환성 유지.
- **모델 교체 대응**: LLM 모델을 교체하더라도 `knowledge_builder` 모듈은 프롬프트/스키마 계약만 지키면 되도록 모델 호출부를 얇게 추상화.

---

## ⑮ 단계별 개발 일정 (WBS, 업데이트)

| 단계 | 기간(예상) | 내용 |
|---|---|---|
| Phase 0. 설계 확정 | 1주 | 본 설계 문서 검토/확정, 표준 스키마 및 산출물 스키마 최종화 |
| Phase 1. 파일럿 구축 | 2~3주 | 3개사 크롤러 + 다운로드 + 원본 저장 |
| Phase 2. 구조화 파이프라인 | 2주 | Text/OCR 추출, 섹션 파서, 회사별 Raw JSON |
| Phase 3. 변경 감지 + Metadata DB | 1~2주 | 해시 비교, 버전 관리, DB 스키마 |
| Phase 4. ★ 표준화 레이어 구축 | 2주 | Canonical Schema 정의, 회사별 매핑 규칙, 정규화 로직 |
| Phase 5. ★ AI Knowledge Builder 구축 | 3~4주 | 6종 산출물 생성기, 프롬프트 설계, `qa_reviewer` 근거 검증 로직 |
| Phase 6. Chunking + 저장 구조 | 1~2주 | Source/AI Chunk 분리 저장, 비교 인덱스 구성 |
| Phase 7. Export 모듈 | 1주 | ChatGPT Project / RAG export (원문+AI 산출물 통합) |
| Phase 8. 나머지 7개사 확장 | 2~3주 | 크롤러 + 표준화 매핑 순차 추가 |
| Phase 9. 자동화/모니터링/검수 워크플로우 | 2주 | 정기 실행, 알림, `review_queue` 운영 프로세스 확립 |
| Phase 10. RAG/Vector Store 고도화 (선택) | 추후 | 임베딩, Dify/Azure AI Search 연동 |

총 파일럿~10개사 + AI Knowledge Builder 완성까지 약 **17~22주** 예상
(v0.1 대비 표준화·AI 생성 레이어 추가로 5~8주 증가, 팀 규모/우선순위에 따라 변동).

---

이 업데이트된 설계에 문제가 없는지 검토해 달라.
