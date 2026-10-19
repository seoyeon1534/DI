"""보고서 빌드: 원고 템플릿(tools/report_template.md)의 부록 표를 결과 파일에서 채우고,
report/최종보고서.md · .docx · .pdf 를 만든 뒤 세 파일이 있는지 확인한다.

실행: python tools/build_report.py  (프로젝트 루트에서)
"""
import os
import re
import subprocess

import math

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, 'report')
TOOLS = os.path.join(ROOT, 'tools')
NL = chr(10)
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
MANAGE = {
    '조선왕릉동부지구관리소': ['동구릉', '광릉', '홍유릉', '사릉'],
    '조선왕릉중부지구관리소': ['태릉', '정릉', '헌릉', '선릉', '의릉', '영휘원'],
    '조선왕릉서부지구관리소': ['서오릉', '서삼릉', '융릉', '파주삼릉', '파주장릉', '김포장릉', '양주온릉'],
    '세종대왕유적관리소': ['세종대왕유적'],
}


def table_a1():
    po = pd.read_csv(os.path.join(ROOT, 'appendix/report_addons/per_origin_table.csv'), encoding='utf-8-sig')
    rows = ['| 원점 | 범주 | 입력 구간 (Chronos-2) | WAPE 나이브 | WAPE 계절 나이브 | WAPE 직전 7일 평균 | WAPE 최종 모형 | 비용 직전 → 최종 (억 원) |',
            '|---|---|---|---:|---:|---:|---:|---:|']
    for _, r in po.iterrows():
        w = {'나이브': r['WAPE 나이브'], '계절': r['WAPE 계절 나이브'], '직전': r['WAPE 직전 7일 평균'], '최종': r['WAPE C3']}
        best = min(w, key=w.get)
        v = {k: f"{x:.3f}" for k, x in w.items()}
        v[best] = f"**{v[best]}**"
        rows.append(f"| {r['원점']} | {r['주범주']} | {r['Chronos-2 입력']} | {v['나이브']} | {v['계절']} | {v['직전']} | {v['최종']} | "
                    f"{r['비용 직전 7일 평균(백만)'] / 100:.2f} → {r['비용 C3(백만)'] / 100:.2f} |")
    rows.append('| **52개 합산** | | | 0.428 | 0.499 | 0.444 | **0.293** | 14.86 → 8.46 |')
    return NL.join(rows)


def table_a2():
    sc = pd.read_csv(os.path.join(ROOT, 'appendix/report_addons/site_scenarios_cost.csv'), encoding='utf-8-sig', dtype=str)
    sc = sc.rename(columns={'Unnamed: 0': 'site'})
    rows = ['| 개소 | 절감 기본 | 절감 ① 서비스 수준 0.9 | 절감 ② 무료 개방일 C_u 120만 | 절감 ③ 1명 1,500명 |',
            '|---|---:|---:|---:|---:|']
    for _, r in sc.iloc[2:].iterrows():
        name = r['site']
        if not isinstance(name, str) or name.strip() in ('', 'site'):
            continue
        vals = [f"{float(r[c]):,.1f}" for c in ['기본.2', '① 서비스 수준 0.9.2', '② 무료 개방일 C_u 120만.2', '③ 1명당 1,500명.2']]
        if name == '합계':
            vals = [f"**{x}**" for x in vals]
            name = f"**{name}**"
        rows.append('| ' + ' | '.join([name] + vals) + ' |')
    return NL.join(rows)


def load_rec():
    r = pd.read_csv(os.path.join(ROOT, 'data/recommend_2026.csv'), encoding='utf-8-sig')
    r['date'] = pd.to_datetime(r['date'])
    r['open'] = ~r['휴관'].astype(bool)
    r['value'] = np.where(r['open'], r['최종 권고 (정수)'], 0)
    return r


def table_a3(rec):
    palace = ['경복궁', '창덕궁', '창경궁', '덕수궁', '종묘']
    rows = ['| 날짜 | 요일 | 경복궁 | 창덕궁 | 창경궁 | 덕수궁 | 종묘 | 왕릉 18곳 합 | 합계 | 비고 |',
            '|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for d in sorted(rec['date'].unique()):
        sub = rec[rec['date'] == d]
        cells = []
        for s in palace:
            x = sub[sub['site'] == s].iloc[0]
            cells.append('휴관' if not x['open'] else str(int(x['value'])))
        tv = int(sub[sub['group'] == '왕릉']['value'].sum())
        total = sum(int(sub[sub['site'] == s]['value'].iloc[0]) for s in palace) + tv
        r0 = sub.iloc[0]
        note = []
        if r0['is_free_rule']:
            note.append('무료 개방')
        if isinstance(r0['holiday_name'], str) and r0['holiday_name']:
            note.append(r0['holiday_name'])
        rows.append(f"| {d.strftime('%m-%d')} | {r0['weekday']} | " + ' | '.join(cells)
                    + f" | {tv} | {total} | {', '.join(note)} |")
    return NL.join(rows)


def table_a4(rec):
    w = rec[rec['group'] == '왕릉']
    rows = ['| 관리소 | 개소 | 정기 휴관 | 개소당 4주 합 | 관리소 4주 합 | 1/21 | 1/28 |',
            '|---|---|---|---:|---:|---:|---:|']
    total = 0
    for m, sites in MANAGE.items():
        sub = w[w['site'].isin(sites)]
        per = int(sub.groupby('site')['value'].sum().iloc[0])
        assert (sub.groupby('site')['value'].sum() == per).all()
        cw = sub['closed_weekday'].iloc[0]
        v21 = int(sub[sub['date'] == '2026-01-21']['value'].iloc[0])
        v28 = int(sub[sub['date'] == '2026-01-28']['value'].iloc[0])
        assert len(sites) == sub['site'].nunique()
        rows.append(f"| {m} | {', '.join(sites)} ({len(sites)}곳) | {cw} | {per} | {per * len(sites)} | {v21} | {v28} |")
        total += per * len(sites)
    assert total == int(w['value'].sum()) == 432, total
    rows.append(f"| **합계 (18곳)** | | | | **{total}** | | |")
    return NL.join(rows)


# 가운뎃점(·) 규칙 (CLAUDE.md 5절)
KEEP_MIDDOT = ['궁·능', '명·일', '개소·일', '궁·능유적본부', 'Chronos-2 + 공휴일·무료 개방', '공휴일·무료 개방']


def fix_middots(text):
    """문장 안 나열의 가운뎃점을 쉼표로 바꾸고, 범위 표기는 ∼로 바꾼다. 바뀐 개수를 돌려준다."""
    protected = {}
    for i, k in enumerate(KEEP_MIDDOT):
        token = f'@@K{i}@@'
        protected[token] = k
        text = text.replace(k, token)
    n_range = 0
    text, n1 = re.subn(r'(\d)·(\d)·(\d)주', lambda m: f'{m.group(1)}∼{m.group(3)}주', text)
    text, n2 = re.subn(r'(\d)·(\d)주', lambda m: f'{m.group(1)}∼{m.group(2)}주', text)
    n_range = n1 + n2
    text, n3 = re.subn(r'(?<=[가-힣0-9A-Za-z%)\]])·(?=[가-힣0-9A-Za-z(])', ', ', text)
    n_sp = text.count(' · ')
    text = text.replace(' · ', ', ')
    n3 += n_sp
    for token, k in protected.items():
        text = text.replace(token, k)
    return text, n_range + n3, n3


def next_number():
    nums = []
    for f in os.listdir(REPORT):
        m = re.fullmatch(r'최종보고서_(\d+)\.pdf', f)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) if nums else 0) + 1


RULE_1028 = {'경복궁': 1.8, '창덕궁': 1.8, '창경궁': 1.8, '덕수궁': 1.8, '종묘': 4.3}


def apply_rule_1028(rec):
    """승인된 안: 1/28 궁·종묘 권고 = ceil(운영 규칙 배수 × 1/21 소수 권고). 원본 파일은 바꾸지 않는다."""
    rec = rec.copy()
    for site, mult in RULE_1028.items():
        d21 = float(rec[(rec['site'] == site) & (rec['date'] == '2026-01-21')]['최종 권고 (소수)'].iloc[0])
        new = math.ceil(mult * d21)
        m = (rec['site'] == site) & (rec['date'] == '2026-01-28')
        rec.loc[m, 'value'] = new
    return rec


def week_table(rec):
    """주차별 권고 표 (1/28 반영)."""
    palace = ['경복궁', '창덕궁', '창경궁', '덕수궁', '종묘']
    lines = ['| 개소 | 1주 (01-01∼07) | 2주 (01-08∼14) | 3주 (01-15∼21) | 4주 (01-22∼28) | 4주 합 | 4주 소수 합 (모형) | 1/21 (수, 평소) | 1/28 (수, 무료) |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    dec = rec.groupby('site')['기본 (소수)'].sum()
    tot = [0, 0, 0, 0]
    tot4 = v21t = v28t = 0
    wk = lambda sub: [int(sub[sub['주차'] == w]['value'].sum()) for w in [1, 2, 3, 4]]
    for site in palace:
        sub = rec[rec['site'] == site]
        w = wk(sub)
        v21 = int(sub[sub['date'] == '2026-01-21']['value'].iloc[0])
        v28 = int(sub[sub['date'] == '2026-01-28']['value'].iloc[0])
        tot = [a + b for a, b in zip(tot, w)]; tot4 += sum(w); v21t += v21; v28t += v28
        lines.append(f"| {site} | " + ' | '.join(f"{x:,}" for x in w) + f" | {sum(w):,} | {dec[site]:.1f} | {v21} | {v28} |")
    tb = rec[rec['group'] == '왕릉']
    one = tb[tb['site'] == sorted(tb['site'].unique())[0]]
    w = wk(one)
    v21 = int(one[one['date'] == '2026-01-21']['value'].iloc[0]); v28 = int(one[one['date'] == '2026-01-28']['value'].iloc[0])
    tot = [a + b * 18 for a, b in zip(tot, w)]; tot4 += sum(w) * 18; v21t += v21 * 18; v28t += v28 * 18
    dec_tomb = float(dec[[x for x in dec.index if x not in RULE_1028]].sum())
    lines.append('| 왕릉 18곳 (각) | ' + ' | '.join(str(x) for x in w) + f' | {sum(w)} | 18곳 합 {dec_tomb:.1f} | {v21} | {v28} |')
    lines.append('| **합계** | ' + ' | '.join(f"**{x:,}**" for x in tot) + f" | **{tot4:,}** | **{float(dec.sum()):.1f}** | **{v21t}** | **{v28t}** |")
    return NL.join(lines), tot4, tot, v28t




def scenario_rows():
    """가정별 4주 정수 합에 1/28 운영 규칙을 적용한 값과 기본 대비 차이."""
    r = pd.read_csv(os.path.join(ROOT, 'data/recommend_2026.csv'), encoding='utf-8-sig')
    r['date'] = pd.to_datetime(r['date'])
    cols = [('기본 (소수)', '기본 (정수)'), ('① 서비스 수준 0.9 (소수)', '① 서비스 수준 0.9 (정수)'),
            ('② 무료 개방일 C_u 120만 (소수)', '② 무료 개방일 C_u 120만 (정수)'), ('③ 1명당 1,500명 (소수)', '③ 1명당 1,500명 (정수)')]
    out = []
    for dc, ic in cols:
        base = int(r[ic].sum())
        delta = 0
        for site, mult in RULE_1028.items():
            d21 = float(r[(r['site'] == site) & (r['date'] == '2026-01-21')][dc].iloc[0])
            old = int(r[(r['site'] == site) & (r['date'] == '2026-01-28')][ic].iloc[0])
            delta += math.ceil(mult * d21) - old
        out.append(base + delta)
    return out


def fill_template_to(path):
    return _fill(path)


def fill_template(n):
    return _fill(os.path.join(REPORT, f'최종보고서_{n}.md'))


def _fill(out):
    t = open(os.path.join(TOOLS, 'report_template.md'), encoding='utf-8').read()
    rec = apply_rule_1028(load_rec())
    wk_md, tot4, tot, v28t = week_table(rec)
    rows = {s_: int(rec[(rec['site'] == s_) & (rec['date'] == '2026-01-28')]['value'].iloc[0]) for s_ in RULE_1028}
    row_txt = '、'.join(f"{k} {v}명" for k, v in rows.items())
    row_txt = row_txt.replace('、', ', ')
    fills = {'{{A1}}': table_a1(), '{{A2}}': table_a2(), '{{A3}}': table_a3(rec), '{{A4}}': table_a4(rec),
             '{{WEEK}}': wk_md, '{{TOTAL4}}': f'{tot4:,}', '{{WKS}}': ', '.join(f'{x:,}' for x in tot),
             '{{ROW_1028}}': row_txt, '{{TOT_1028}}': f'{v28t:,}'}
    sc = scenario_rows()
    base_sc = sc[0]
    fills.update({'{{SC0}}': f'{sc[0]:,}', '{{SC1}}': f'{sc[1]:,} ({sc[1] - base_sc:+,})'.replace('+', '+'),
                  '{{SC2}}': f'{sc[2]:,} ({sc[2] - base_sc:+,})'.replace('+0', '0'),
                  '{{SC3}}': f'{sc[3]:,} ({sc[3] - base_sc:+,})'})
    for k, v in fills.items():
        assert k in t, k
        t = t.replace(k, v)
    assert '{{' not in t
    for bad in ['⬜', '(가안)', '[그림 ']:
        assert bad not in t, bad
    t, n_all, n_list = fix_middots(t)
    print(f'가운뎃점 바꾼 개수: {n_all} (쉼표 {n_list}, 범위 ∼ {n_all - n_list})')
    open(out, 'w', encoding='utf-8').write(t)
    return out


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise SystemExit(f"실패: {' '.join(cmd)}\n{r.stderr}")
    return r


def build_preview():
    """작업 중 미리보기: 번호 없는 작업중_미리보기.pdf 하나만 덮어쓴다(md·docx·제출본은 만들지 않는다)."""
    fill_template(0)
    src = os.path.join(REPORT, '최종보고서_0.md')
    html = os.path.join(TOOLS, '_preview.html')
    run(['pandoc', '최종보고서_0.md', '-f', 'markdown', '-t', 'html5', '--standalone', '--embed-resources',
         '--resource-path=.', '--css', os.path.join(TOOLS, 'report_style.css'),
         '--metadata', 'pagetitle=미리보기', '-o', html], REPORT)
    h = open(html, encoding='utf-8').read()
    h = re.sub(r'<colgroup>.*?</colgroup>', '', h, flags=re.S)
    h = re.sub(r'<table style="[^"]*"', '<table', h)
    open(html, 'w', encoding='utf-8').write(h)
    pdf = os.path.join(REPORT, '작업중_미리보기.pdf')
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                    '--print-to-pdf=' + pdf, 'file:///' + html.replace(chr(92), '/')], capture_output=True)
    os.remove(html); os.remove(src)
    data = open(pdf, 'rb').read()
    print('미리보기 pages', len(re.findall(rb'/Type\s*/Page[^s]', data)))


def build():
    n = next_number()
    base = f'최종보고서_{n}'
    fill_template(n)
    html = os.path.join(TOOLS, '_build_report.html')
    run(['pandoc', base + '.md', '-f', 'markdown', '-t', 'html5', '--standalone', '--embed-resources',
         '--resource-path=.', '--css', os.path.join(TOOLS, 'report_style.css'),
         '--metadata', 'pagetitle=궁·능 인력 배치 최종 보고서', '-o', html], REPORT)
    h = open(html, encoding='utf-8').read()
    h = re.sub(r'<colgroup>.*?</colgroup>', '', h, flags=re.S)
    h = re.sub(r'<table style="[^"]*"', '<table', h)
    open(html, 'w', encoding='utf-8').write(h)
    pdf = os.path.join(REPORT, base + '.pdf')
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                    '--print-to-pdf=' + pdf, 'file:///' + html.replace(chr(92), '/')],
                   capture_output=True)
    os.remove(html)
    run(['pandoc', base + '.md', '-f', 'markdown', '-t', 'docx', '--resource-path=.', '-o', base + '.docx'], REPORT)
    data = open(pdf, 'rb').read()
    pages = len(re.findall(rb'/Type\s*/Page[^s]', data))
    print('pages', pages)
    print('번호', n)
    import shutil
    shutil.copy(os.path.join(REPORT, base + '.pdf'), os.path.join(ROOT, 'report.pdf'))
    print('제출용 복사:', os.path.join(ROOT, 'report.pdf'))
    for f in [base + '.md', base + '.docx', base + '.pdf']:
        p = os.path.join(REPORT, f)
        print(f, os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else 0)


def build_pdf_only():
    """요청에 따라 report.pdf 한 개만 만든다 (프로젝트 최상위). md·docx·번호 파일은 만들지 않는다."""
    import shutil
    rec = apply_rule_1028(load_rec())
    src_md = os.path.join(REPORT, '_report_src.md')
    out_md = fill_template_to(src_md)
    html = os.path.join(TOOLS, '_report_pdf.html')
    run(['pandoc', out_md, '-f', 'markdown', '-t', 'html5', '--standalone', '--embed-resources',
         '--resource-path=' + REPORT, '--css', os.path.join(TOOLS, 'report_style.css'),
         '--metadata', 'pagetitle=궁·능 인력 배치 최종 보고서', '-o', html], REPORT)
    h = open(html, encoding='utf-8').read()
    h = re.sub(r'<colgroup>.*?</colgroup>', '', h, flags=re.S)
    h = re.sub(r'<table style="[^"]*"', '<table', h)
    open(html, 'w', encoding='utf-8').write(h)
    pdf = os.path.join(ROOT, 'report.pdf')
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                    '--print-to-pdf=' + pdf, 'file:///' + html.replace(chr(92), '/')], capture_output=True)
    for f in (html, out_md):
        os.remove(f)
    data = open(pdf, 'rb').read()
    print('report.pdf pages', len(re.findall(rb'/Type\s*/Page[^s]', data)), pdf, os.path.getsize(pdf))


if __name__ == '__main__':
    import sys
    build_preview() if '--preview' in sys.argv else (build_pdf_only() if '--pdf-only' in sys.argv else build())
