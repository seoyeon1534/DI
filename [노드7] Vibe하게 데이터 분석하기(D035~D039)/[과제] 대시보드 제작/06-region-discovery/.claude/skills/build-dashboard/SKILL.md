---
name: build-dashboard
description: data/의 주문 CSV를 분석해, templates/reference.html과 동일한 퀄리티의 State 투자기회 발견 대시보드(5-STEP 스토리 구조)를 output/에 생성하는 스킬. "대시보드 만들어줘", "/build-dashboard" 시 사용.
argument-hint: "[CSV 경로 — 생략 시 data/superstore_orders.csv]"
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Write, Bash
---

# build-dashboard — State 투자기회 발견 대시보드 자동 생성

수강생이 이 명령 하나만 치면, 강사 퀄리티의 5-STEP State 탐색형 대시보드가 자기 주문 데이터로 나온다.
**반드시 아래 5단계를 순서대로 수행한다. 단계를 건너뛰지 않는다.**

## STEP 1 — 데이터 읽기 (EDA)
- 인자로 받은 CSV(없으면 `data/superstore_orders.csv`)를 Read/Bash로 로드.
- 컬럼·행 수·State 개수·연도 범위·Category/Segment 목록을 한 줄로 요약해 사용자에게 보여준다.
- 필수 컬럼 확인: `Order ID, Order Date(또는 Order Year), State/Province, Region, Country/Region, Category, Segment, Sales, Quantity, Discount, Profit`.
  - 컬럼명이 다르면 가장 가까운 것에 매핑하고, 매핑 결과를 알려준다.
  - `Order Date`만 있으면 `Order Year`를 파생시킨다.
  - 컬럼이 없으면 **여기서 멈추고** 사용자에게 알린다.

## STEP 2 — 전체 요약 지표 계산 (실제 숫자, 사용자 확인용)
- `CLAUDE.md`의 계산식대로 **필터 없음(전체) 기준** 총매출·총이익·이익률·평균할인율·State 수를 계산해 표로 보여준다.
- 최근 2개 연도의 전년비(%)도 계산해 보여준다 (STEP 1 KPI 뱃지가 맞게 나올지 사전 점검용).
- State별 매출·이익률·주문건수(Order ID nunique)를 한 번 집계해서 사분면·Top3·랭킹 결과가 말이 되는지 확인한다.
- 계산은 Bash(python)로 실제 수행. **추정·반올림 임의값 금지.**
- 주의: 이 계산은 "미리보기 확인용"이다. **실제 대시보드의 모든 집계·전년비·Top3 판정은 브라우저 JS(`recompute()`)가
  필터 변경 시마다 직접 수행**하므로, 여기서 계산한 숫자를 차트에 직접 박아넣지 않는다.

## STEP 3 — 레퍼런스 구조 흡수
- `templates/reference.html`을 **반드시 Read** 한다.
- STEP 1~5 섹션 구조, 필터 바, KPI 카드+뱃지, Region 추이 라인차트, 사분면+Top3 콜아웃, State별 기회/개선 지도,
  랭킹 테이블, 할인-이익 산점도, Category 막대, 요약+caveat 순서를 파악한다.
- 교체 대상 범위는 `// ORDERS_SAMPLE_START` 줄과 `// ORDERS_SAMPLE_END` 줄 **사이**뿐이다.
  이 두 마커 줄 자체와, 그 바깥의 모든 HTML/CSS/JS는 **한 글자도 건드리지 않는다.**
  (State별 기회/개선 지도용 `US_STATE_PATHS` 좌표 데이터도 마커 바깥의 정적 값이므로 절대 건드리지 않는다.)
- 스키마: `{orderId, state, region, country, year, category, segment, sales, quantity, discount, profit}`.
- State별 기회/개선 지도: 사분면과 같은 stateAgg 데이터를 기반으로 "기회 점수"를
  0~1로 정규화한 뒤, 파란색 하나의 명도 단계로만 표시한다 (진할수록 기회, 옅을수록
  개선 필요). 빨간색은 쓰지 않는다. 데이터 없는 State만 회색(--gridline)으로 표시.

## STEP 4 — 데이터 주입해서 렌더 (반드시 스크립트로 처리 — 직접 타이핑 금지)
- **절대 모델이 10,000행 넘는 배열을 직접 손으로 다시 쓰지 않는다.** 대신 Bash로 짧은 Python 스크립트를 실행해서 처리한다:
  1. `templates/reference.html`을 텍스트로 읽는다.
  2. `// ORDERS_SAMPLE_START`와 `// ORDERS_SAMPLE_END` 줄의 위치를 정확히 찾는다 (문자열 검색, 정규식 아님).
  3. CSV를 읽어 각 행을 `{orderId:"...", state:"...", ...}` 형식의 JS 객체 리터럴 문자열로 변환하고,
     **파이썬 코드로 각 줄 끝에 확실하게 콤마를 붙인다** (마지막 원소도 trailing comma 허용되므로 상관없음).
  4. `START 마커 줄까지의 원본 내용 + 새 배열 텍스트 + END 마커 줄부터의 원본 내용`을 그대로 이어붙여 새 파일을 만든다.
     (마커 바깥 내용은 원본과 **바이트 단위로 동일**해야 한다.)
  5. `output/region_discovery_dashboard.html`로 저장한다.

### ⚠️ 중요: STEP 4 체크리스트 (데이터 미표시 문제 방지)

**파일 생성 직후, 반드시 다음을 확인해야 한다. 하나라도 빠지면 데이터가 브라우저에 안 보인다!**

1. **마커 구조 검증**
   ```bash
   grep -c "// ORDERS_SAMPLE_START" output/region_discovery_dashboard.html
   grep -c "// ORDERS_SAMPLE_END" output/region_discovery_dashboard.html
   grep -A 1 "// ORDERS_SAMPLE_START" output/region_discovery_dashboard.html
   ```
   - ✅ START 마커는 정확히 1개, END 마커도 정확히 1개
   - ✅ **START 마커 다음 줄에 반드시 `const ORDERS_SAMPLE = [` 이 있어야 함** (이 줄이 없으면 JS 문법 에러)

2. **배열 내용 검증**
   ```bash
   grep -c 'orderId:' output/region_discovery_dashboard.html
   ```
   - ✅ 개수가 CSV의 데이터 행 개수와 정확히 일치
   - ✅ 각 항목이 `{orderId:"...", state:"...", ...}` 형식 유지
   - ✅ 배열이 `];`로 정확히 닫혀있는지 확인 (trailing comma는 있어도 문제 없음 — 굳이 지우지 않는다)

3. **구조 검증**
   ```bash
   grep -c 'class="step-tag"' output/region_discovery_dashboard.html
   grep -c '<canvas' output/region_discovery_dashboard.html
   grep -c 'id="usMapSvg"' output/region_discovery_dashboard.html
   grep -c 'caveat' output/region_discovery_dashboard.html
   ```
   - ✅ step-tag 5개, canvas 4개, usMapSvg 1개, caveat 1개 이상

4. **문법 검증**
   - `node --check`로 `<script>...</script>` 내부 파싱 (아래 본문의 필수 검증과 동일, 가장 확실한 방법)

**만약 하나라도 실패하면:**
- ❌ START 마커 다음에 `const ORDERS_SAMPLE = [` 이 없으면 → **즉시 재생성** (가장 흔한 에러!)
- ❌ 배열 개수가 안 맞으면 → 마커 범위 재확인 후 재생성
- ❌ `node --check` 에러 → 콤마 누락 등 재확인 후 재생성

- **저장 직후 반드시 검증한다**: Bash로 `node --check`(또는 동등한 방법)를 돌려서 `<script>...</script>` 내부가
  문법 오류 없이 파싱되는지 확인한다. 에러가 있으면 **여기서 멈추고** 사용자에게 알린다 — 조용히 넘어가지 않는다.
- `Math.random()` 등으로 데이터를 생성하지 않는다. 모든 값은 CSV에서 온 실제 데이터거나, 그 데이터로부터 JS가 계산한 값이어야 한다.

## STEP 5 — 전달 + 인사이트 권고
- 저장 경로의 **절대경로 file:// 링크**를 안내한다.
- "이번 데이터(전체 필터) 기준 투자 검토 후보"를 3줄 이내로 요약 출력 — **대시보드 STEP 3의 Top3 콜아웃과 같은 기준**으로:
  - **숨은 기회 후보**: 매출 대비 이익률이 높은 State 상위 몇 곳 + 주문건수(표본) 명시
  - **구조개선 필요 후보**: 매출은 크지만 이익률이 낮은 State
  - **표본 주의**: 주문건수가 적어 해석에 유의해야 할 State가 있으면 별도 언급
- 끝에 한 줄: "data/의 CSV를 본인 데이터로 바꾸고 다시 `/build-dashboard` 하면 같은 퀄로 재생성됩니다."

## 핵심 원칙
- reference = 품질 기준선. 결과가 그보다 단순/다른 톤이면, 혹은 STEP 5개 중 하나라도 빠지면 다시 만든다.
- 복붙이 아니라 "구조 재사용 + 데이터(원본 행) 교체". 집계·전년비·Top3 로직은 전부 레퍼런스의 JS를 그대로 쓴다.
- 표본이 작은 State를 근거 없이 "기회"로 단정하지 않는다. 항상 주문건수(표본 크기)를 함께 보여준다.
