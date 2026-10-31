"""설비센서 50건으로 노이즈와 추세를 판정하고 그래프 한 장(index.html)과 expected.json을 만든다."""
import csv
import json
import statistics as st

CSV_NAME = "Day5_설비센서_50건_가상.csv"
VIB, TEMP = "진동(mm/s)", "온도(℃)"

with open(CSV_NAME, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))


def series(prefix, col):
    picked = [r for r in rows if r["설비"].startswith(prefix)]
    return [r["시간"][-5:] for r in picked], [float(r[col]) for r in picked]


def judge(times, values):
    # 처음 12점(08:00~11:40)이 기준선, 상한 = 평균 + 3 × 표준편차
    base = values[:12]
    limit = st.mean(base) + 3 * st.stdev(base)
    # 상한을 3번 연속 넘으면 추세, 그 첫 시각이 추세 시작
    for i in range(len(values) - 2):
        if all(v > limit for v in values[i:i + 3]):
            return limit, times[i]
    return limit, None


def first_normal_range_hit(times, values):
    # 평상 범위 = 평균 ± 2 × 표준편차, 처음 벗어난 시각
    m, s = st.mean(values), st.stdev(values)
    return next((t for t, v in zip(times, values) if abs(v - m) > 2 * s), None)


def minutes(t):
    return int(t[:2]) * 60 + int(t[3:])


times, a_vib = series("설비A", VIB)
_, b_vib = series("설비B", VIB)
_, b_temp = series("설비B", TEMP)

a_limit, a_start = judge(times, a_vib)
b_vib_limit, b_vib_start = judge(times, b_vib)
b_temp_limit, b_temp_start = judge(times, b_temp)
assert a_start is None, "설비A는 추세가 아니어야 한다"

first_hit = min(first_normal_range_hit(times, b_vib), first_normal_range_hit(times, b_temp))
lead = minutes(first_hit) - minutes(b_temp_start)
a_spike = max(a_vib)
a_spike_time = times[a_vib.index(a_spike)]

# 그래프: 같은 시간축에 진동(위)과 온도(아래)
W, L, R = 480, 34, 12
X = lambda i: L + i * (W - L - R) / (len(times) - 1)


def panel(top, height, lo, hi):
    return lambda v: top + height - (v - lo) / (hi - lo) * height


def line(values, y, cls):
    pts = " ".join(f"{X(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
    return f'<polyline class="{cls}" points="{pts}"/>'


def marker(t, top, bottom, label):
    x = X(times.index(t))
    return (f'<line class="mark" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}"/>'
            f'<text class="b" x="{x - 4:.1f}" y="{top + 10}" text-anchor="end">{label}</text>')


yv = panel(24, 150, 0.5, 4.0)
yt = panel(214, 110, 50, 67)
svg = [f'<svg viewBox="0 0 {W} 352" role="img" aria-label="설비A 진동, 설비B 진동과 온도의 시간별 그래프">']
for v in (1, 2, 3, 4):
    svg.append(f'<text class="t" x="{L - 5}" y="{yv(v) + 4:.1f}" text-anchor="end">{v}</text>')
for v in (50, 55, 60, 65):
    svg.append(f'<text class="t" x="{L - 5}" y="{yt(v) + 4:.1f}" text-anchor="end">{v}</text>')
svg.append(f'<text class="h" x="{L}" y="14">진동 (mm/s)</text>')
svg.append(f'<text class="h" x="{L}" y="204">설비B 온도 (℃)</text>')
svg.append(f'<line class="limit" x1="{L}" y1="{yv(b_vib_limit):.1f}" x2="{W - R}" y2="{yv(b_vib_limit):.1f}"/>')
svg.append(f'<text class="t" x="{L + 2}" y="{yv(b_vib_limit) - 5:.1f}">설비B 기준선 상한 {b_vib_limit:.2f}</text>')
svg.append(f'<line class="limit" x1="{L}" y1="{yt(b_temp_limit):.1f}" x2="{W - R}" y2="{yt(b_temp_limit):.1f}"/>')
svg.append(f'<text class="t" x="{L + 2}" y="{yt(b_temp_limit) - 4:.1f}">기준선 상한 {b_temp_limit:.2f}</text>')
svg.append(marker(b_vib_start, 24, 174, f"진동 추세 시작 {b_vib_start}"))
svg.append(marker(b_temp_start, 214, 324, f"온도 추세 시작 {b_temp_start}"))
svg.append(line(a_vib, yv, "a"))
svg.append(line(b_vib, yv, "bl"))
svg.append(line(b_temp, yt, "bl"))
i = a_vib.index(a_spike)
svg.append(f'<text class="a-t" x="{X(i) - 6:.1f}" y="{yv(a_spike) + 4:.1f}" text-anchor="end">설비A {a_spike_time} {a_spike} 한 번 (노이즈)</text>')
svg.append(f'<text class="b" x="{W - R}" y="{yv(b_vib[-1]) - 6:.1f}" text-anchor="end">설비B {b_vib[-1]}</text>')
for t in ("08:00", "10:00", "12:00", "14:00", "16:00"):
    svg.append(f'<text class="t" x="{X(times.index(t)):.1f}" y="344" text-anchor="{"end" if t == "16:00" else "middle"}">{t}</text>')
svg.append("</svg>")

html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>노이즈 vs 추세</title>
<style>
:root {{ --bg:#fff; --ink:#1f2933; --muted:#616e7c; --a:#2563eb; --b:#c2410c; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#16191d; --ink:#e4e7eb; --muted:#9aa5b1; --a:#7ba7f7; --b:#f59e6b; }} }}
body {{ margin:0; background:var(--bg); color:var(--ink); font-family:system-ui,"Malgun Gothic",sans-serif; line-height:1.55; }}
main {{ max-width:720px; margin:0 auto; padding:24px 16px; }}
h1 {{ font-size:1.35rem; margin:0 0 8px; }}
p {{ margin:0 0 16px; }}
svg {{ display:block; width:100%; height:auto; }}
svg text {{ font-size:11px; }}
polyline {{ fill:none; stroke-width:2; }}
.a {{ stroke:var(--a); }} .bl {{ stroke:var(--b); }}
.limit {{ stroke:var(--muted); stroke-dasharray:4 3; }}
.mark {{ stroke:var(--b); stroke-width:1; }}
.t {{ fill:var(--muted); }} .h {{ fill:var(--ink); font-weight:600; }}
.b {{ fill:var(--b); font-weight:600; }} .a-t {{ fill:var(--a); font-weight:600; }}
small {{ color:var(--muted); display:block; margin-top:16px; }}
</style></head><body><main>
<h1>한 번의 튐이 아니라 추세적 상승이 신호다</h1>
<p>설비A는 {a_spike_time}에 진동 {a_spike}으로 한 번 튄 노이즈입니다. 설비B는 온도 {b_temp_start}, 진동 {b_vib_start}부터 추세로, 평상 범위로 처음 잡힌 {first_hit}보다 {lead}분 빠릅니다.</p>
{"".join(svg)}
<small>판정: 처음 12점 기준선의 평균 + 3 × 표준편차를 3번 연속 넘으면 추세. 실습용 가상 데이터. 출처: keerhee/kma-auto-genai-3-1, data/Day5/{CSV_NAME}</small>
</main></body></html>
"""
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

expected = {"values": {
    "a_spike_time": {"value": a_spike_time, "decimals": None, "block": 1},
    "a_spike": {"value": a_spike, "decimals": 1, "block": 1},
    "b_temp_start": {"value": b_temp_start, "decimals": None, "block": 1},
    "b_vib_start": {"value": b_vib_start, "decimals": None, "block": 1},
    "b_temp_limit": {"value": round(b_temp_limit, 2), "decimals": 2, "block": 1},
    "b_vib_limit": {"value": round(b_vib_limit, 2), "decimals": 2, "block": 1},
    "lead_minutes": {"value": lead, "decimals": 0, "block": 1},
}}
with open("expected.json", "w", encoding="utf-8") as f:
    json.dump(expected, f, ensure_ascii=False, indent=2)
print(json.dumps(expected, ensure_ascii=False))
