# State 투자기회 발견 대시보드 킷

Superstore 주문 데이터(CSV) 하나만 있으면, **명령어 한 줄**로 강사와 동일한 퀄리티의
대시보드가 만들어집니다.

## 사용법 (3단계)

```bash
# 1. 이 폴더에서 Claude Code 실행
cd 06-region-discovery
claude

# 2. 명령어 한 줄
/build-dashboard

# 3. 끝. output/region_discovery_dashboard.html 이 열립니다.
```

## 내 데이터로 바꾸기
`data/superstore_orders.csv`를 본인 주문 데이터로 교체하고 다시 `/build-dashboard` 하면 끝.

필요한 컬럼
- `Order ID`: 주문 식별자 (주문건수 = nunique 기준)
- `Order Date` 또는 `Order Year`: 주문 연도 (필터용)
- `State/Province`: 분석 단위 (핵심 축)
- `Region`: 대권역 (필터·계층 탐색용)
- `Country/Region`: 국가
- `Category`, `Segment`: 필터용 차원
- `Sales`, `Quantity`, `Discount`, `Profit`: 집계 원천

State는 여기서 **전체 목록을 그대로** 다 씁니다 — 몇 개인지, 이름이 뭔지는 상관없습니다.

## 폴더 구조
```
06-region-discovery/
├── CLAUDE.md                        # 디자인 헌법 (색·KPI·표본가드 규칙)
├── .claude/skills/build-dashboard/  # 작업 절차 (이게 명령어가 됨)
├── templates/reference.html         # 품질 기준 = 완성된 State 탐색 대시보드
├── data/superstore_orders.csv       # 주문 단위 원본 데이터 (본인 것으로 교체)
└── output/                          # 결과물이 여기 생성됨
```


## 왜 강사와 똑같이 나오나?
- **CLAUDE.md** = 디자인·KPI·표본가드 규칙을 고정 (헌법)
- **Skill** = 분석→렌더 절차를 고정 (작업 매뉴얼)
- **templates/reference.html** = 품질 기준선 (이걸 보고 같은 수준으로 만듦)

세 개가 묶여 있어서, 데이터만 바뀌어도 결과 퀄리티는 일정합니다. 특히 이 킷은 필터(연도·Category·
Segment·Region)를 바꿀 때마다 **브라우저가 원본 데이터를 그 자리에서 다시 집계**하는 방식이라,
미리 쪼개서 저장한 요약본을 쓰는 다른 킷들과 달리 표본이 왜곡될 일이 없습니다.

## 이 대시보드가 답하는 질문
- 어느 State가 **매출은 큰데 이익률이 낮아** 구조개선이 필요한가?
- 어느 State가 **매출은 작지만 이익률이 높아** 숨은 투자 기회인가?
- 그 후보가 **표본(주문건수)으로 뒷받침될 만큼 믿을 만한 신호**인가, 아니면 우연히 튄 소수 주문인가?