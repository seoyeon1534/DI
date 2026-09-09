# CLAUDE.md — State 투자기회 발견 대시보드

## 이 프로젝트의 목표
`data/superstore_orders.csv`(주문 단위 원본 데이터)를 받아, State(주) 단위로 매출·이익 구조를 뜯어보는
**탐색형 대시보드** HTML을 `output/`에 만든다.
"예쁜 화면"이 아니라 "경영진이 스스로 필터를 조작하며 어디에 투자 여지가 있는지 찾아내고,
왜 그런지까지 이해할 수 있는 화면"을 만든다. 경영진은 데이터 분석 배경이 없을 수 있으므로,
**차트를 던져주고 알아서 해석하게 하지 않는다** — 질문형 스토리 순서로 안내한다.

---

## 가장 중요한 규칙 (반드시 먼저 읽을 것)
**처음부터 새로 디자인하지 않는다.** 항상 `templates/reference.html`을 먼저 Read 하고,
그 **구조·레이아웃·색상·차트 종류·STEP 순서를 그대로 재사용**한 뒤, **숫자와 인사이트만 새 데이터로 교체**한다.

- 레퍼런스는 **"품질 기준선"**이다. 결과물이 레퍼런스보다 단순하거나 STEP이 빠지면 실패다.
- 레퍼런스에 박힌 수치·State명은 전부 **디자인용 예시**다. `⚠ SAMPLE` 마커가 붙은 블록은 **전량 교체 대상**이다.
- 단, **복붙이 아니다.** 데이터는 반드시 새로 집계해서 실제 계산값을 넣는다.
- **JS 로직·차트 초기화·필드명/형식은 절대 바꾸지 않는다.** `ORDERS_SAMPLE` 배열의 **값만** 교체한다.
- 데이터로 계산할 수 없는 지표는 만들어내지 않는다. 컬럼이 없으면 진행을 멈추고 사용자에게 알린다.

## 데이터 스펙 (`data/superstore_orders.csv`)
| 컬럼 | 설명 |
|---|---|
| Order ID | 주문 식별자 (주문건수 = nunique) — JS의 `orderId` |
| Order Date / Order Year | 주문일자 / 연도 (필터·추이용) — JS의 `year` |
| State/Province | 분석 단위 (핵심 축) — JS의 `state` |
| Region | 4개 대권역 (Central/East/South/West) — JS의 `region` |
| Country/Region | United States / Canada — JS의 `country` |
| Category | Office Supplies / Furniture / Technology — JS의 `category` |
| Segment | Consumer / Corporate / Home Office — JS의 `segment` |
| Sales / Quantity / Discount / Profit | 집계 원천 |

이 컬럼들이 없으면 진행을 멈추고 사용자에게 알린다. 컬럼명이 비슷하지만 다르면 가장 가까운 것에 매핑하고 알린다.

## 핵심 지표 정의 (계산식 고정)
| 지표 | 계산식 | 표기 |
|---|---|---|
| 선택 기간 매출 | Sales 합 (현재 필터 기준, 누적 아님) | `$` |
| 총이익 | Profit 합 | `$` |
| 이익률 | 총이익 / 총매출 × 100 | `%` |
| 평균할인율 | Discount 평균 | `%` |
| 주문건수 | Order ID nunique | 정수 |
| 전년 대비(YoY) | (최신연도값 − 직전연도값) / 직전연도값 × 100 | `%` |
| 전체 평균 대비 | 필터링된 값 − 필터 없음(전체) 값 | `%p` |

- State별 집계는 **필터(연도/Category/Segment/Region) 선택 시점에 매번 다시 계산**한다. 미리 모든 조합을 쪼개서 저장하지 않는다.
- 전년 대비: 연도 필터에서 특정 연도를 선택했으면 그 해 vs 바로 전 해를 비교하고,
"전체"를 선택했으면 데이터에 있는 가장 최근 2개 연도를 비교한다.
(category/segment/region 필터는 그대로 적용)
- 비율은 `%`, 증감은 `%p`로 구분 표기. 절대값/상대값 혼용 금지.

## 표본 가드
- 주문건수가 5건 미만인 State는 사분면 차트에서 버블을 옅게 표시하고, 랭킹 테이블·Top3 콜아웃에 "표본 작음" 배지를 붙인다.
- 표본이 작은 State를 근거 없이 "숨은 기회"로 단정하지 않는다. 버블 크기는 항상 주문건수에 비례한다.

## 디자인 토큰 (색은 최대 3색: red/green/blue — 임의 색 추가 금지)
```css
--surface-1: #fcfcfb; --page-plane: #f9f9f7;
--text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #898781;
--gridline: #e1e0d9; --baseline: #c3c2b7;
--series-1: #2a78d6;               /* 사분면·할인 차트 State 점 (blue) */
--series-1-mid: rgba(42,120,214,0.72); /* 사분면 버블 기본색 — 겹쳐도 구분되게 반투명 */
--series-1-low: rgba(42,120,214,0.35); /* 표본 작은 State 버블 */
--good: #0ca30c; --good-bg: rgba(12,163,12,0.08);   /* 상승 (green) */
--critical: #d03b3b; --critical-bg: rgba(208,59,59,0.08); /* 하락 (red) */
--neutral-bg: #e1e0d9;             /* 방향성 없는 뱃지 (회색, 색으로 안 셈) */
--region-1: #0d366b; --region-2: #1c5cab; --region-3: #3987e5; --region-4: #86b6ef; /* blue 명도 단계 */
--cat-1: #104281; --cat-2: #2a78d6; --cat-3: #86b6ef;                               /* blue 명도 단계 */
```
- **색은 red(하락) / green(상승) / blue(데이터) 3색만** 쓴다. Region 4개·Category 3개는 전부 blue의 명도 단계로만 구분한다.
- Region은 `Central→region-1(진함)···West→region-4(연함)`, Category는 `Office Supplies→cat-1···Technology→cat-3` 순서 고정
- KPI 수치 색은 검정(`--text-primary`) 고정. 증감 뱃지에만 good/critical/neutral 사용
- State별 기회/개선 지도는 red를 쓰지 않는다 — `--series-1` 계열의 순차(sequential) 파랑 램프 양 끝
  (옅은 `#cde2fb` ~ 진한 `#0d366b`)만 사용해, 진할수록 기회·옅을수록 개선 필요를 표현한다.
- 다크모드는 `prefers-color-scheme`로 대응

## 대시보드 구성 — 5-STEP 스토리 구조 (하나라도 빠지면 실패)

**STEP 1 — 지금 우리는 잘하고 있는가?**
KPI 카드 5개(선택 기간 매출·총이익·이익률·평균할인율·분석대상 State 수) + 전년비/전체평균대비 뱃지

**STEP 2 — 어디가 성장을 이끄는가?**
Region별 매출 추이 라인차트(4개 시리즈, 연도별) + 국가별(US/Canada) 매출 비중 텍스트

**STEP 3 — 그럼 어디에 기회가 있는가?**
"최우선 검토 후보 Top 3" 콜아웃 → State 사분면 차트(표본가드 적용) → State별 기회/개선 지도 → State 랭킹 테이블
- 사분면 차트의 x축(매출)은 **로그 스케일**을 쓴다 — State 간 매출 편차가 커서 선형 스케일이면
  대부분 State가 한쪽에 뭉쳐 보이기 때문. 버블 색은 `--series-1-mid`(반투명)로 겹쳐도 구분되게 한다.
- State별 기회/개선 지도는 사분면과 같은 stateAgg 데이터로 "기회 점수"를 계산해 0~1로 정규화한 뒤,
  파란색 하나의 명도 단계로만 표시한다 (진할수록 기회, 옅을수록 개선 필요). 빨간색은 쓰지 않는다.
  데이터 없는 State만 회색(`--gridline`)으로 표시.

**STEP 4 — 왜 이런 결과가 나왔는가?**
State별 평균 할인율×이익률 산점도 + Category별 매출 비중 **가로 막대 차트**(도넛 금지)

**STEP 5 — 그래서 무엇을 해야 하는가?**
Top3 기반 자동 요약 문구 + 데이터 한계 caveat 고정 문구

각 STEP 제목은 차트 이름이 아니라 **질문형**으로 유지한다.

---

## 금지
- reference를 무시하고 새 레이아웃을 만드는 것 / STEP 순서·질문형 제목을 바꾸는 것
- 레퍼런스 숫자·State명을 그대로 남겨두는 것
- `Math.random()` 등으로 차트 데이터를 생성하는 것
- `ORDERS_SAMPLE` 필드명·형식 변경 / 차트 JS 로직 수정
- KPI 수치에 색 입히기 / 한쪽 변만 있는 border
- 표본이 작은 State를 가드 문구 없이 "기회"로 단정하는 것
- STEP 5 caveat 생략 / `:root` 토큰 밖의 색 사용 / Category를 도넛으로 만드는 것
- State별 기회/개선 지도에 red를 쓰는 것 (파랑 단일 톤만 사용)
- 사분면 차트 x축을 다시 선형 스케일로 되돌리는 것

## 작업이 끝나면
- `output/region_discovery_dashboard.html`로 저장, 절대경로 file:// 링크 안내
- STEP 3 Top3 콜아웃과 동일한 기준으로 "우선 투자 검토 State" 3줄 요약 출력