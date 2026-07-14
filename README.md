# Insurance AI Knowledge Platform

삼성화재 상품요약서(PDF)를 자동 수집하여, 사람이 읽기 좋은 Markdown으로 변환하고,
ChatGPT/Claude/Gemini 등 어떤 AI에도 업로드해 질문할 수 있는 Knowledge Package로
만드는 프로젝트입니다.

> **현재 단계: Phase 3 (MVP)** — "삼성화재 PDF를 Markdown으로 변환해 AI가 읽을 수
> 있게 만드는 것"이 목표입니다. Canonical Schema / Knowledge Builder / FAQ Generator /
> LLM 연동 / OCR은 이번 단계에 포함되지 않습니다.

**개발 환경은 GitHub Codespaces를 기준으로 합니다. 로컬 PC 설치 과정은 다루지
않습니다.** 아래 모든 명령은 Codespaces 터미널(브라우저 또는 GitHub 모바일 앱에서
접속 가능)에서 실행합니다.

---

## 빠른 시작 (GitHub Codespaces)

### 1. Codespace 열기
GitHub repository 페이지 → **Code** 버튼 → **Codespaces** 탭 → **Create codespace on main**
(PC/태블릿/모바일 브라우저 어디서든 가능합니다.)

Codespace가 열리면 `.devcontainer/devcontainer.json` 설정에 따라 Python 3.12
환경과 의존성이 **자동으로 설치**됩니다 (`postCreateCommand`가 자동 실행). 별도
설치 명령을 직접 칠 필요는 없지만, 확인/재설치가 필요하면 아래를 실행하세요.

```bash
pip install -r requirements.txt
pip install -e .
playwright install --with-deps chromium
```

### 2. 전체 파이프라인 실행 (터미널에서 순서대로)

```bash
# ① 삼성화재 상품공시실에서 상품요약서 PDF 다운로드 (SamsungFireCrawler → PdfDownloader)
python scripts/crawl.py --company samsung_fire

# ② PDF 분석 + Markdown 변환 + QA Report 생성 (PyMuPDF, OCR 없음)
python scripts/analyze_and_extract.py

# ③ Markdown들을 AI 독립적 Knowledge Package로 묶기
python scripts/build_knowledge_package.py
```

### 3. 결과물 다운로드해서 AI에 업로드

Codespaces 파일 탐색기(왼쪽 사이드바)에서 `data/exports/knowledge_package.zip`을
찾아 **우클릭 → Download**하면 브라우저(태블릿 포함)로 zip 파일이 다운로드됩니다.
압축을 풀어 그 안의 `.md` 파일들을 ChatGPT Project / Claude Project / Gemini /
Dify 등에 업로드한 뒤, 다음과 같은 질문을 해보세요.

- 가입연령은?
- 주요보장은?
- 보험기간은?
- 납입기간은?
- 면책사항은?

---

## 전체 흐름

```
python scripts/crawl.py --company samsung_fire
        ↓ (SamsungFireCrawler: 상품명/카테고리/게시일/PDF URL 수집)
        ↓ (PdfDownloader: 실제 PDF 다운로드, 변경감지, metadata.json)
data/raw/SamsungFire/{category}/*.pdf + *.metadata.json
        ↓
python scripts/analyze_and_extract.py
        ↓ (PdfAnalyzer: 페이지수/텍스트·이미지PDF/OCR필요/표존재/암호화/추천Parser)
data/raw/SamsungFire/{category}/*.analysis.json
        ↓ (PyMuPdfTextExtractor: 텍스트 추출 → Markdown, 제목/표/페이지 유지)
data/extracted_text/SamsungFire/{category}/*.md
        ↓ (QaReport: 페이지수/문자수/추출성공률/표개수/OCR필요/추천Parser/오류페이지)
data/qa_reports/SamsungFire/{category}/*.qa_report.json
        ↓
python scripts/build_knowledge_package.py
        ↓
data/exports/knowledge_package/  (+ INDEX.md)
data/exports/knowledge_package.zip   ← 이 파일을 다운로드해서 AI에 업로드
```

---

## 폴더 구조

```
insurance-ai-knowledge-platform/
├── .devcontainer/devcontainer.json   # Codespaces 자동 환경설정
├── config/
│   ├── settings.yaml
│   ├── schema/canonical_schema.yaml     # 아직 미사용 (Phase 4 예정)
│   └── companies/
│       ├── sample_company.yaml          # Phase 1 예시 (실제 보험사 아님)
│       └── samsung_fire.yaml            # 실제 대상: 삼성화재
│
├── src/insurance_kb/
│   ├── core/                # Config Loader, Logger, Exceptions (Phase 1)
│   ├── models/               # Company/Product/... + PdfDocumentMetadata(P2)
│   │                         # + PdfAnalysisResult, QaReport (Phase 3, 신규)
│   ├── utils/                 # hash/file/date/text/retry(P1) + robots_util(P2)
│   ├── crawlers/samsung_fire_crawler.py   # Phase 2 — API 우선, Playwright 폴백
│   ├── downloader/pdf_downloader.py       # Phase 2 — httpx 기반, 변경감지
│   ├── extraction/
│   │   ├── base_extractor.py              # Phase 1 (ABC, 변경 없음)
│   │   ├── pdf_analyzer.py                # Phase 3, 신규 — PyMuPDF 구조 진단
│   │   ├── pymupdf_text_extractor.py      # Phase 3, 신규 — 텍스트+Markdown
│   │   └── qa_report_generator.py         # Phase 3, 신규 — QA Report 생성
│   ├── standardization/ / knowledge_builder/ / export/
│   │                          # Phase 1 BaseClass만 존재, 아직 미구현
│   └── storage/ / repositories/ / container/ / orchestration/
│                              # Phase 1 그대로 (Architecture Freeze)
│
├── scripts/
│   ├── run_pipeline.py               # Phase 1 Hello Pipeline
│   ├── crawl.py                      # Phase 2 — 실제 삼성화재 수집 CLI
│   ├── discover_samsung_fire_api.py  # Phase 2 — 1회성 Network/XHR 분석 도구
│   ├── analyze_and_extract.py        # Phase 3, 신규 — PDF → Markdown + QA Report
│   └── build_knowledge_package.py    # Phase 3, 신규 — AI 독립적 패키지 생성
│
├── data/
│   ├── raw/SamsungFire/{category}/          # PDF + metadata.json + analysis.json
│   ├── extracted_text/SamsungFire/{category}/  # *.md
│   ├── qa_reports/SamsungFire/{category}/       # *.qa_report.json
│   └── exports/knowledge_package(.zip)          # 최종 산출물
│
├── tests/                    # Unit + Mock 테스트 (Live는 별도 마커)
└── docs/
    ├── design_doc.md              # 전체 아키텍처 설계 (v0.2, 참고용)
    └── samsung_fire_analysis.md   # 삼성화재 홈페이지 분석 결과
```

---

## 테스트

```bash
pytest                      # Unit + Mock만 실행 (기본, 네트워크 불필요)
pytest -m live                # 실제 삼성화재 홈페이지 대상 (네트워크 필요, 명시적 실행)
pytest --cov=insurance_kb --cov-report=term-missing
```

## 아직 구현되지 않은 것 (의도적으로 제외)
Canonical Schema 매핑, AI Knowledge Builder(요약/FAQ/비교 자동생성), LLM API 연동,
OCR(스캔 PDF 처리). `PdfAnalyzer`가 `needs_ocr=true`로 표시한 PDF는 텍스트 추출이
불완전할 수 있습니다 — Markdown/QA Report에서 확인 가능합니다.

## 개발 원칙
- Python 3.12 / PEP8 / Type Hint / Google Style Docstring
- Pydantic 기반 Domain Model 우선
- ABC 기반 인터페이스 + SOLID / Clean Architecture / Repository Pattern
- **Phase 1 Architecture Freeze**: 기존 구조/Base Class/DI Container는 변경하지
  않고, 새 기능은 항상 새 파일 추가로 확장
