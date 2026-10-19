"""발표자료 빌드: 최종보고서의 숫자와 report/figs 그림으로 slides.pdf를 만든다 (프로젝트 최상위 폴더).

실행: python tools/build_slides.py  (프로젝트 루트에서)
"""
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
FIG = '../report/figs/'

CSS = """
@page { size: 338mm 190mm; margin: 0; }
html, body { margin: 0; padding: 0; background: #fff; color: #1a1a1a;
  font-family: "Malgun Gothic", "맑은 고딕", sans-serif; }
.slide { width: 338mm; height: 190mm; box-sizing: border-box; padding: 14mm 18mm;
  page-break-after: always; position: relative; overflow: hidden; }
.slide:last-child { page-break-after: auto; }
h1 { font-size: 30pt; margin: 0 0 6mm 0; color: #0b2a4a; line-height: 1.25; }
h2 { font-size: 22pt; margin: 0 0 5mm 0; color: #0b2a4a; line-height: 1.3; }
p, li { font-size: 15pt; line-height: 1.45; margin: 0 0 2.5mm 0; }
ul { margin: 0; padding-left: 6mm; }
.kicker { font-size: 12pt; color: #5b6b7d; margin-bottom: 2mm; }
.big { font-size: 40pt; font-weight: 700; color: #0b2a4a; line-height: 1.1; }
.bigsub { font-size: 14pt; color: #444; }
.cards { display: flex; gap: 6mm; margin-top: 6mm; }
.card { flex: 1; border: 1px solid #c9d3de; border-radius: 3mm; padding: 4mm 5mm; background: #f5f8fb; }
.card .n { font-size: 26pt; font-weight: 700; color: #0b2a4a; }
.card .t { font-size: 12.5pt; color: #444; }
table { border-collapse: collapse; width: 100%; font-size: 13pt; margin-top: 2mm; }
th, td { border: 0.6pt solid #b7c2cf; padding: 1.8mm 2.5mm; text-align: left; }
th { background: #e8eef5; color: #0b2a4a; }
td.r, th.r { text-align: right; }
img { display: block; max-width: 100%; max-height: 92mm; margin: 2mm auto; }
.two { display: flex; gap: 8mm; align-items: flex-start; }
.two > div { flex: 1; }
.foot { position: absolute; bottom: 7mm; left: 18mm; font-size: 10pt; color: #7a8796; }
.hl { color: #b3261e; font-weight: 700; }
"""


def slide(body, n, foot=''):
    f = f'<div class="foot">{foot}</div>' if foot else ''
    return f'<section class="slide">{body}{f}<div class="foot" style="left:auto;right:18mm">{n}</div></section>'


S = []

S.append(slide("""
<div style="margin-top:38mm">
<div class="kicker">M2 조 (한서연, 이서진, 한상훈, 유서영) · 궁·능 운영팀 발표 · 20분</div>
<h1 style="font-size:40pt">무료 개방일에 개소마다 인력을<br>평소의 몇 배로 늘려야 하는가</h1>
<p class="bigsub" style="margin-top:8mm">2025년 백테스트 52개 원점 · 2026년 1월 4주 권고 · 궁 4곳, 종묘, 조선왕릉 18곳</p>
</div>""", 1))

S.append(slide("""
<div class="kicker">결론 먼저 (3분)</div>
<h2>무료 개방일에는 개소 유형마다 다르게 늘려야 하고, 그렇게 하면 비용이 43% 줄어든다</h2>
<div class="cards">
  <div class="card"><div class="n">893명·일</div><div class="t">2026년 1월 4주 권고 합계 (정수, 왕릉 하루 1명 이상 포함)</div></div>
  <div class="card"><div class="n">−6.40억 원</div><div class="t">백테스트 비용 절감 (직전 7일 평균 대비, 43%)</div></div>
  <div class="card"><div class="n">50명</div><div class="t">1/28(마지막 수요일, 무료) 권고, 운영 규칙 적용</div></div>
</div>
<ul style="margin-top:7mm">
  <li><b>요청 1:</b> 무료 개방일 증원 기준(궁 1.8배·명절 후 4배, 종묘 4.3배)을 운영 기준으로 채택</li>
  <li><b>요청 2:</b> 달력에 없는 무료 개방이 공지되면 그 날짜를 표시해 다시 예측하는 절차 운영</li>
  <li><b>가정 변화:</b> 서비스 수준 0.9면 951명·일(+58), 1명 1,500명이면 1,027명·일(+134). 네 가정 모두에서 최종 모형이 직전 방식보다 싸다</li>
</ul>
""", 2))

S.append(slide(f"""
<div class="kicker">1. 질문과 범위</div>
<h2>개소 × 날짜 단위 7일 예측, 원점 전날 확정, 1순위 지표는 WAPE</h2>
<table>
<tr><th>항목</th><th>정한 것</th></tr>
<tr><td>예측 단위</td><td>개소(23곳) × 날짜. 합계로 보면 오차가 상쇄돼 좋아 보인다</td></tr>
<tr><td>확정 시점</td><td>원점 전날 확정 (1주 전 확정은 0.76억 원 더 비쌈)</td></tr>
<tr><td>시험 원점</td><td>2025-01-01부터 7일 간격 52개 (설·추석·마지막 수요일 포함)</td></tr>
<tr><td>무료 개방일</td><td>달력 규칙: 명절 연휴 + 매월 마지막 수요일. 유료 관람객 수는 쓰지 않음</td></tr>
<tr><td>비용 가정</td><td>모자란 1명·일 60만 원, 남는 1명·일 15만 원, 1명 = 2,000명 → 0.8 분위수</td></tr>
</table>
""", 3))

S.append(slide(f"""
<div class="kicker">2. 증원 폭</div>
<h2>궁은 명절 당일 이후 4배, 마지막 수요일 1.8배로 늘린다. 왕릉은 공휴일 기준이다</h2>
<img src="{FIG}fig5.png" style="max-height:88mm">
<p class="kicker">배수 = 그날 관람객 ÷ 앞뒤 28일 평소 같은 요일 평균 (2023∼2025년 중앙값). 인과 효과가 아니라 연휴·행사가 함께 일어난 크기다.</p>
""", 4))

S.append(slide(f"""
<div class="kicker">3. 방법 선택</div>
<h2>공휴일·무료 개방 정보를 넣은 최종 모형이 오차와 비용을 모두 가장 낮췄다</h2>
<div class="two">
<div>
<table>
<tr><th>방식</th><th class="r">WAPE</th><th class="r">적중률</th><th class="r">비용 (억 원)</th></tr>
<tr><td>직전 7일 평균 (현재 방식)</td><td class="r">0.444</td><td class="r">0.582</td><td class="r">14.86</td></tr>
<tr><td>+ 0.8 분위수 보정</td><td class="r">0.444</td><td class="r">0.804</td><td class="r">13.20</td></tr>
<tr><td>신경망 MLP</td><td class="r">0.339</td><td class="r">0.785</td><td class="r">9.66</td></tr>
<tr><td><b>Chronos-2 + 공휴일·무료 개방 (최종)</b></td><td class="r"><b>0.293</b></td><td class="r"><b>0.804</b></td><td class="r"><b>8.46</b></td></tr>
</table>
<p class="kicker" style="margin-top:3mm">52개 원점 중 39개에서 WAPE 1위 (나이브·계절 나이브·직전 7일 평균과 비교)</p>
</div>
<div><img src="{FIG}fig1.png" style="max-height:70mm"><p class="kicker">주당 비용: 무료 개방 주(A·B)에 비용이 몰린다</p></div>
</div>
""", 5))

S.append(slide(f"""
<div class="kicker">4. 정보 추가 효과 (FVA)</div>
<h2>신경망은 명절 연휴 정보가 1.83억 원으로 가장 크게 줄였고, 최종 모형은 공휴일 정보가 1.04억 원으로 가장 컸다</h2>
<img src="{FIG}fig3.png" style="max-height:80mm">
<p>정기 휴관 요일 정보는 효과가 없다(+0.04억 원). 날씨 정보는 비용을 늘렸다(신경망 기준: 전날 큰비 +0.23억, 완벽한 예보 가정 +0.06억).</p>
""", 6))

S.append(slide(f"""
<div class="kicker">5. 비용 절감</div>
<h2>직전 7일 평균 대비 6.40억 원 절감. 이 중 보정으로 1.66억, 모형으로 4.74억</h2>
<table>
<tr><th>방식</th><th class="r">모자란 인원 비용 (억 원)</th><th class="r">남는 인원 비용 (억 원)</th><th class="r">합계 (억 원)</th><th class="r">직전 대비</th></tr>
<tr><td>직전 7일 평균</td><td class="r">11.92</td><td class="r">2.94</td><td class="r">14.86</td><td class="r">—</td></tr>
<tr><td>+ 0.8 분위수 보정</td><td class="r">6.42</td><td class="r">6.78</td><td class="r">13.20</td><td class="r">−1.66</td></tr>
<tr><td><b>최종 모형 (Chronos-2 + 공휴일·무료 개방)</b></td><td class="r">4.63</td><td class="r">3.83</td><td class="r"><b>8.46</b></td><td class="r"><b>−6.40</b></td></tr>
</table>
<p style="margin-top:4mm">왕릉 최소 1명 규칙(팀 결정)을 넣으면 19.55억 → 14.05억 원(−5.50억). 모든 방식에 같은 규칙을 적용했고 순위는 같다.</p>
""", 7))

S.append(slide(f"""
<div class="kicker">6. 2026년 1월 권고</div>
<h2>4주 권고는 893명·일. 무료 개방일 1/28은 운영 규칙으로 50명을 배치한다</h2>
<table>
<tr><th>개소</th><th class="r">1주 (01-01~07)</th><th class="r">2주 (01-08~14)</th><th class="r">3주 (01-15~21)</th><th class="r">4주 (01-22~28)</th><th class="r">4주 합 (명·일)</th><th class="r">1/21 (수, 평소, 명)</th><th class="r">1/28 (수, 무료, 명)</th></tr>
<tr><td>경복궁</td><td class="r">54</td><td class="r">43</td><td class="r">45</td><td class="r">51</td><td class="r">193</td><td class="r">8</td><td class="r"><b>14</b></td></tr>
<tr><td>창덕궁</td><td class="r">17</td><td class="r">15</td><td class="r">14</td><td class="r">15</td><td class="r">61</td><td class="r">2</td><td class="r"><b>4</b></td></tr>
<tr><td>창경궁</td><td class="r">12</td><td class="r">10</td><td class="r">8</td><td class="r">10</td><td class="r">40</td><td class="r">1</td><td class="r"><b>2</b></td></tr>
<tr><td>덕수궁</td><td class="r">31</td><td class="r">31</td><td class="r">32</td><td class="r">38</td><td class="r">132</td><td class="r">5</td><td class="r"><b>9</b></td></tr>
<tr><td>종묘</td><td class="r">9</td><td class="r">8</td><td class="r">8</td><td class="r">10</td><td class="r">35</td><td class="r">1</td><td class="r"><b>3</b></td></tr>
<tr><td>왕릉 18곳 (각 1명 · 열린 날)</td><td class="r">6</td><td class="r">6</td><td class="r">6</td><td class="r">6</td><td class="r">각 24</td><td class="r">1</td><td class="r">1</td></tr>
<tr><td><b>합계</b></td><td class="r"><b>231</b></td><td class="r"><b>215</b></td><td class="r"><b>215</b></td><td class="r"><b>232</b></td><td class="r"><b>893</b></td><td class="r"><b>35</b></td><td class="r"><b>50</b></td></tr>
</table>
<p class="kicker" style="margin-top:3mm">정수 인원 = 0.8 분위수 ÷ 2,000명을 올림. 소수 합 449.6명·일, 왕릉 하루 1명 하한을 넣으면 822.7명·일, 정수 합 893명·일(왕릉 432명·일 포함).</p>
""", 8))

S.append(slide(f"""
<div class="kicker">7. 1/28 (마지막 수요일) 해석</div>
<h2>모형만 쓰면 1/28은 평소 수요일의 1.3배에 그친다. 운영 규칙은 궁 1.8배, 종묘 4.3배로 올린다</h2>
<div class="two">
<div>
<ul>
  <li>마지막 수요일 적중률은 0.48로 목표 0.8에 못 미친다 (MLP는 0.72).</li>
  <li>실제 관람객은 중앙값 예측의 약 1.5배였다. 1·2·3주 일찍 확정해도 적중률이 0.54·0.52·0.61이라, 원인은 확정 시점이 아니라 무료 효과 과소 추정이다.</li>
  <li>경복궁 1/28 모형 소수 인원 9.57명은 1/21(평소 수요일) 소수 인원 7.35명의 1.30배이고, 올림하면 10명이다. 운영 규칙(1.8배)을 적용하면 14명이다.</li>
  <li>1/28 전체로는 모형 40명에서 50명으로 10명 늘어난다. 이 추가분은 남을 경우 최대 150만 원이다.</li>
</ul>
</div>
<div><img src="{FIG}fig7.png" style="max-height:66mm"><p class="kicker">주 범주별 적중률 (fig7)</p></div>
</div>
""", 9))

S.append(slide(f"""
<div class="kicker">8. 가정 바꿔 보기</div>
<h2>가정을 바꿔도 최종 모형은 모든 경우에 직전 7일 평균보다 쌌다</h2>
<table>
<tr><th>가정</th><th class="r">직전 7일 평균 (억 원)</th><th class="r">최종 모형 (억 원)</th><th class="r">절감 (억 원)</th><th class="r">4주 권고 (명·일)</th></tr>
<tr><td>기본 (τ 0.8, 모자란 1명 60만 원, 2,000명)</td><td class="r">14.86</td><td class="r">8.46</td><td class="r">6.40</td><td class="r">893</td></tr>
<tr><td>① 서비스 수준 0.9 (비용 가정은 기본)</td><td class="r">14.86</td><td class="r">8.88</td><td class="r">5.98</td><td class="r">951</td></tr>
<tr><td>② 무료 개방일만 모자란 1명 120만 원</td><td class="r">19.76</td><td class="r">9.62</td><td class="r">10.14</td><td class="r">893</td></tr>
<tr><td>③ (예비) 1명이 하루 1,500명</td><td class="r">19.81</td><td class="r">11.28</td><td class="r">8.53</td><td class="r">1,027</td></tr>
</table>
<p class="kicker" style="margin-top:3mm">② 권고가 기본과 같은 이유: 1/28 인원은 운영 규칙으로 정하므로 1/28만 올리는 ②의 차이가 사라진다. 23개소 × 4가정 모두 절감이 양수다.</p>
""", 10))

S.append(slide(f"""
<div class="kicker">9. 한계와 오차</div>
<h2>남은 오차는 무료 개방일 중 마지막 수요일과 추석 연휴 후반에 몰려 있다</h2>
<div class="two">
<div>
<ul>
  <li>부족 상위 10건 중 7건이 추석 연휴 후반 (2025-10-08∼09, 궁 4곳). 가을 궁중문화축전과 겹쳐 명절과 행사 효과를 나눌 수 없다.</li>
  <li>2025년 10월 무료 개방(규칙 밖)은 달력에 없어 예측하지 못했다. 공지 반영으로 최대 0.39억 원을 줄일 수 있다(상한).</li>
  <li>날씨는 격자 자료라 국지적인 비가 반영되지 않는다.</li>
  <li>2026년 무료 확대(조선왕릉 매주 수요일 등)가 이어지면 배수를 다시 계산해야 한다.</li>
</ul>
</div>
<div><img src="{FIG}fig8.png" style="max-height:66mm"><p class="kicker">경복궁 2025 추석: 직전 7일 평균은 연휴 급증을 따라가지 못한다</p></div>
</div>
""", 11))

S.append(slide("""
<div class="kicker">10. 운영팀에 요청할 결정</div>
<h2>세 가지를 결정해 주시면 다음 권고부터 바로 반영하겠습니다</h2>
<div class="cards">
  <div class="card"><div class="n">①</div><div class="t"><b>무료 개방일 증원 기준</b><br>궁 1.8배(마지막 수요일)·4배(명절 당일 이후), 종묘 4.3배를 기준으로 증원</div></div>
  <div class="card"><div class="n">②</div><div class="t"><b>4주 표 + 매주 재확정</b><br>4주 치를 한 번 내고 매주 화요일에 다음 1주를 다시 확정 (한 달 전 확정이 필요하면 4주 표 그대로 사용)</div></div>
  <div class="card"><div class="n">③</div><div class="t"><b>공지 기록 절차</b><br>규칙 밖 무료 개방·행사 공지를 날짜·개소 표로 모아 다시 예측 (공지 반영 상한 −0.39억)</div></div>
</div>
<p style="margin-top:6mm">아직 계산하지 않은 것: 마지막 수요일 여유 분위수의 비용, 왕릉 관리소 단위 인력 공유 효과.</p>
""", 12))


HTML = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<style>{CSS}</style></head><body>
{''.join(S)}
</body></html>"""

html_path = os.path.join(TOOLS, '_slides.html')
open(html_path, 'w', encoding='utf-8').write(HTML)
out = os.path.join(ROOT, 'slides.pdf')
subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                '--print-to-pdf=' + out, 'file:///' + html_path.replace(chr(92), '/')],
               capture_output=True)
os.remove(html_path)
data = open(out, 'rb').read()
print('slides pages', len(re.findall(rb'/Type\s*/Page[^s]', data)), out, os.path.getsize(out))
