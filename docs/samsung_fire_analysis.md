# 삼성화재 상품공시실 분석 결과 (Phase 2 파일럿)

조사일: 2026-07-13 | 조사 도구: web_search / web_fetch (실제 브라우저 실행 불가 환경)

## 1. 진입 URL
- 메인: `https://www.samsungfire.com/vh/page/VH.HPIF0103.do` (보험상품공시)
- 안내(비JS, 참고용): `https://www.samsungfire.com/v2/html/publication/03/J_030_010_001.html`
- `.co.kr` 도메인도 동일 콘텐츠 응답 확인 — 크롤러는 `.com`으로 고정.

## 2. 페이지 구조
정적 HTML에 `{{item.title}}`, `{{onSaleList.length}}` 등 미해석 템플릿 바인딩이 그대로 노출됨
→ 클라이언트 JS가 별도로 데이터를 채우는 구조. 검색결과 테이블 컬럼:
`상품종류 | 상품명 | 판매개시일 | 사업방법서 | 상품요약서 | 보험약관`
"판매상품" / "판매중지상품" 두 개 탭 존재. Step1~3 다운로드 위저드 UI도 별도로 존재하나
검색결과 테이블과의 관계는 런타임 확인 필요.

## 3. 카테고리 구조
최상위 탭 5개(자동차보험/장기보험/일반보험/퇴직연금/퇴직보험)는 "주관부서 연락처" 표와
정확히 일치 확인. "건강보험/암보험/운전자보험" 등은 최상위가 아니라 장기보험 하위의
`productCategory` 값으로 추정(실제 상품명 "무배당 삼성화재 건강보험 마이핏1640" 확인됨).
→ **크롤러는 이 값을 하드코딩하지 않고 실제 응답의 category 필드를 그대로 사용.**

## 4. PDF 다운로드 방식 — URL 패턴 비일관성 확인
| 패턴 | 예시 | 비고 |
|---|---|---|
| 현재(추정) | `/download/product/P_P02_14_07_000_{1,2}.pdf` | 2024년 상품에서 확인, 접미사 의미 불명 |
| 레거시 | `/product/leaflet/P02_03_08_096_20210107.pdf` | 2021년 상품 |
| 구버전 | `/publication/pdf/95394_0_20090801_file1.pdf` | 2009년 자료 |

→ URL을 코드로 조립하지 않고, 반드시 페이지/응답에서 실제 링크를 그대로 추출해야 함.

## 5. JavaScript 사용 여부
사용함 (필수). 카테고리 탭도 `javascript:;` 핸들러로 처리됨. "상품요약서" 셀의 실제
다운로드 트리거도 단순 `<a href>`가 아니라 JS 함수일 가능성이 높음(정적 조사로 확정 불가).

## 6. Pagination 여부
런타임 확인 필요 (정적 조사로 페이지네이션 UI 요소 자체가 렌더링되지 않음).

## 7. robots.txt
`www.samsungfire.com/robots.txt` 원문을 이 조사 환경에서는 확보하지 못함(검색엔진에
별도 색인되어 있지 않음). → 코드가 실제 실행 시점에 직접 fetch하여 확인하도록 구현
(`insurance_kb.utils.robots_util`), 최초 1회만 확인 후 프로세스 내 캐시.

## 8. API 존재 여부 (Phase 2 개정 요구사항 #1)
이 개발 환경은 네트워크가 차단되어 있어 실제 브라우저의 Network/XHR 탭을 확인하는
Playwright 실행이 불가능했다. 따라서 **API 존재 여부는 아직 미확정**이다.
`scripts/discover_samsung_fire_api.py`를 실제 네트워크가 있는 환경에서 최초 1회
실행하여 XHR/Fetch 트래픽을 캡처하고, 그 결과에 따라
`config/companies/samsung_fire.yaml`의 `api_endpoint`를 채우거나 비워두는 절차를
코드에 내장했다. `SamsungFireCrawler`는:
- `api_endpoint`가 설정되어 있으면 `httpx`만으로 수집 (Playwright 미사용)
- 비어 있으면 Playwright DOM 스크래핑으로 폴백

## 예상 변경 위험 요소 (요약)
PDF URL 패턴 비일관성, JS 프레임워크 의존 셀렉터, 검색결과 테이블 vs Step 위저드
이중 UI 경로, 카테고리 세부값 미확정, 판매상품/판매중지상품 이중 목록, AJAX 엔드포인트
미확인, `.com`/`.co.kr` 도메인 중복.
