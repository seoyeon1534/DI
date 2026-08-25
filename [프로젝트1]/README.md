# iFood 캠페인 반응 분석 — README

과거 캠페인 수락 이력이 6차 캠페인 반응을 예측/설명하는지 검증하고, 7차 캠페인 예산 배분에 참고할 세그먼트 인사이트를 도출하는 분석 노트북입니다.

---

## 1. 실행 환경

### 1-1. Python 버전
- Python 3.10 이상 권장 (Colab 기본 런타임 기준)

### 1-2. 필요 패키지

이 노트북은 pandas, numpy, statsmodels, scikit-learn, kmodes, matplotlib, scipy를 사용합니다.
버전을 아래처럼 고정(pin)해서 requirements.txt로 관리하는 것을 권장합니다.

```txt
pandas>=2.0,<3.0
numpy>=1.24,<2.0
scikit-learn>=1.3,<1.5
statsmodels>=0.14,<0.15
kmodes>=0.12,<0.13
matplotlib>=3.7,<3.9
scipy>=1.10,<1.13
```

> ⚠️ **재현성 주의사항**: 위 버전 범위는 참고용 권장값입니다. 실제로 분석을 수행한 환경의 정확한 버전을 아래 명령으로 캡처해서 이 파일에 함께 보관하세요 (Restart & Run All 검증 시 필수).
>
> ```bash
> pip freeze | grep -Ei "pandas|numpy|scikit-learn|statsmodels|kmodes|matplotlib|scipy" > requirements_frozen.txt
> ```

### 1-3. 설치 방법

**Google Colab**
```python
!pip install kmodes
# pandas, numpy, scikit-learn, statsmodels, matplotlib, scipy는 Colab 기본 제공
```

**로컬 환경 (venv 권장)**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install pandas numpy scikit-learn statsmodels kmodes matplotlib scipy
```

### 1-4. 한글 폰트 (matplotlib)

일부 셀에서 `matplotlib.rcParams['font.family'] = 'NanumGothic'`을 사용합니다.
환경에 나눔고딕 폰트가 없으면 그래프의 한글 라벨이 깨지거나 경고가 발생합니다.

```bash
# Colab / Ubuntu 계열
!apt-get install -y fonts-nanum
!fc-cache -fv
```

설치 후 **런타임을 재시작**해야 matplotlib가 새 폰트를 인식합니다.

---

## 2. 데이터 다운로드 방법

### 2-1. 필요 파일

| 파일명 | 설명 | 사용 위치 |
|---|---|---|
| `marketing_clean.csv` | 전처리 완료된 원본 데이터 (2,036행, 32컬럼) | Step 0 ~ Step 3 |
| `marketing_segmented.csv` | `marketing_clean.csv`에 `Cluster`, `Segment_Name`, `Segment_Priority` 컬럼이 추가된 파일 (Step 3-4 실행 결과물) | Step 4 |

### 2-2. 확보 방법

1. `marketing_clean.csv`는 원본 iFood 마케팅 캠페인 데이터셋을 결측치 처리·파생변수 생성(Age, Children, AnyAccepted 등)까지 마친 전처리 완료본입니다. 원본 데이터 출처 및 전처리 코드는 별도 전처리 노트북을 참고하세요.
2. `marketing_segmented.csv`는 본 노트북의 **Step 3-4(클러스터링)까지 실행한 뒤** `df.to_csv()`로 저장한 파일입니다. 처음부터 실행한다면 별도로 다운로드할 필요 없이 Step 3-4까지 실행한 결과를 그대로 이어서 쓰거나, 아래처럼 저장 후 Step 4에서 다시 불러오면 됩니다.
```python
   df.to_csv('marketing_segmented.csv', index=False)
```

### 2-3. 파일 배치

**Google Colab**
```python
from google.colab import drive
drive.mount('/content/gdrive')
# 파일을 /content/gdrive/MyDrive/ 에 위치
```

**로컬 / 기타 환경**
```
project/
├── marketing_clean.csv
├── marketing_segmented.csv
└── notebook.ipynb
```
노트북 내 경로 문자열(`C:\DI\[프로젝트1]\marketing_campaign.csv`)을 실제 파일 위치로 일괄 수정하세요.

> ⚠️ **재현성 주의사항**: Restart & Run All 실행 전 **하나의 경로로 통일**하는 것을 권장합니다.

---

## 3. 노트북 실행 순서

셀은 위에서 아래로 순서대로 실행해야 합니다. 이전 셀에서 생성된 변수(`df`, `y`, `demo_cols` 등)를 이후 셀이 재사용하는 구조이므로, 중간부터 실행하면 `NameError`가 발생합니다.

| Step | 내용 | 주요 산출물 |
|---|---|---|
| Step 0 | 데이터 로드 및 기초 확인 (`AnyAccepted` 정의 검증) | `df` |
| Step 1 | H1 — 단순 로지스틱 회귀 (오즈비, marginal effect, Cohen's d) | 오즈비 7.542 |
| Step 2 | H2 — Model A(인구통계 통제) / Model B(소비·채널 추가 통제), VIF 점검 | 오즈비 6.873 / 6.840 |
| Step 3 | H3-1 — k-prototypes 클러스터링 (변수 준비 → Elbow/Silhouette로 k 결정 → k=4 최종 클러스터링 → gamma 실험 → 세그먼트 프로파일링/네이밍) | `df["세그먼트"]`, `marketing_segmented.csv` |
| Step 4 | H3-2 — 세그먼트별 오즈비 계산 + 교호작용항 모델 + LR test | LR test p=0.4288 |
| Step 5 | 종합 결론 및 실행 제안 | — |
| Step 6 | 한계 및 제언 | — |

### 3-1. 재현 시 체크리스트

- [ ] 모든 셀의 데이터 경로를 하나로 통일했는가
- [ ] Step 2에서 사용하는 `or_A`, `demo_cols` 등이 Step 2 코드 블록 내에서 명시적으로 정의되어 있는가 (원 노트북 일부 셀에는 정의 코드가 생략되어 있어 보완 필요)
- [ ] Step 3-2, 3-3, 3-4가 각각 `df`를 독립적으로 다시 로드하는지, 혹은 이전 셀의 `df`를 재사용하는지 확인 — 재사용 시 컬럼 구성이 달라져 있으면 오류 발생
- [ ] `pd.set_option('display.float_format', ...)`으로 퍼센트 포맷을 설정한 뒤, Step 4 이전에 `pd.reset_option('display.float_format')`으로 반드시 초기화했는가 (오즈비가 잘못된 퍼센트 형식으로 출력되는 문제 방지)
- [ ] **Restart & Run All**을 실제로 1회 수행하여 끝까지 에러 없이 완료되는지 확인

### 3-2. 예상 실행 시간

- k-prototypes 관련 셀(Step 3-2, 3-3, gamma 실험)은 k값·n_init 조합에 따라 반복 학습이 많아 다른 셀보다 오래 걸립니다 (환경에 따라 총 수 분 소요 가능).

---

## 4. 참고

- 본 분석은 관찰 데이터 기반이며, 인과추론(PSM/DiD 등)을 수행하지 않았습니다. 자세한 한계는 노트북 Step 6을 참고하세요.
- 그래프 라벨, 데이터프레임 컬럼명, 출력 텍스트는 한국어로 작성되어 있습니다.