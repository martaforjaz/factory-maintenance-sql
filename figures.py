"""Generate the README figures from the pipeline CSV outputs."""
import csv
from html import escape
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAVY, PLUM, GRAY = "#173457", "#935784", "#526579"


def label(x, y, value, size=20, color=NAVY, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')


def save(name, height, title, elements):
    folder = ROOT / "figures"
    folder.mkdir(exist_ok=True)
    (folder / f"{name}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="{height}" '
        f'viewBox="0 0 1080 {height}" font-family="Arial, sans-serif" role="img">'
        f'<title>{escape(title)}</title><rect width="1080" height="{height}" fill="#fff"/>'
        + "".join(elements) + "</svg>\n", encoding="utf-8")


def read(name):
    with (ROOT / "output" / f"{name}.csv").open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def overview(rows):
    n = sum(int(r["observations"]) for r in rows)
    k = sum(int(r["failures"]) for r in rows)
    checks = read("quality_checks")
    passed = sum(int(r["violations"]) == 0 for r in checks)
    items = [label(36, 50, "From factory telemetry to maintenance analytics", 34, weight=700),
             label(36, 82, "UCI AI4I 2020 · public synthetic benchmark", 20, GRAY)]
    stages = [("UCI source", f"{n:,} observations"),
              ("Validated SQLite", f"{passed}/{len(checks)} SQL checks passed"),
              ("Analysis outputs", f"{k:,} failures · {100*k/n:.2f}% overall")]
    for i, (title, detail) in enumerate(stages):
        x = 36 + 348 * i
        items += [f'<rect x="{x}" y="110" width="312" height="105" rx="7" fill="#eaf0f6"/>',
                  label(x+18, 153, title, 24, weight=700),
                  label(x+18, 185, detail, 19, GRAY)]
        if i < 2:
            items.append(label(x+330, 171, "→", 25, PLUM, 700, "middle"))
    save("pipeline", 249, "Pipeline overview and verified counts", items)


def wilson(k, n):
    rate = k / n
    z = 1.96
    denominator = 1 + z*z/n
    center = (rate + z*z/(2*n)) / denominator
    margin = z * sqrt(rate*(1-rate)/n + z*z/(4*n*n)) / denominator
    return center-margin, center+margin


def cohort_plot(rows):
    title = "The highest-wear band has the highest failure rate in every grade"
    items = [label(36, 49, title, 29, weight=700),
             label(36, 80, "Observed failure rates by product grade and tool wear", 20, GRAY),
             label(810, 124, "Rate", 16, GRAY, 700),
             label(920, 124, "Failures / rows", 16, GRAY, 700)]
    wear_order = {"0–99": 0, "100–199": 1, "200+": 2}
    cohorts = sorted(rows, key=lambda r: (r["grade"], wear_order[r["wear_band"]]))
    def scale(rate):
        return 255 + 530 * rate / .25
    for i in range(6):
        x = scale(i * .05)
        items += [f'<line x1="{x}" y1="139" x2="{x}" y2="548" stroke="#dce4ec"/>',
                  label(x, 573, f"{i*5}%", 16, GRAY, anchor="middle")]
    for i, r in enumerate(cohorts):
        y = 157 + i * 46
        k, n = int(r["failures"]), int(r["observations"])
        lo, hi = wilson(k, n)
        color = PLUM if r["wear_band"] == "200+" else NAVY
        if i % 3 == 0:
            items.append(label(36, y+6, f'Grade {r["grade"]}', 18, weight=700))
        items += [label(137, y+6, r["wear_band"] + " min", 17, GRAY),
                  f'<line x1="{scale(lo)}" y1="{y}" x2="{scale(hi)}" y2="{y}" stroke="{color}" stroke-width="3"/>',
                  f'<circle cx="{scale(k/n)}" cy="{y}" r="6" fill="{color}"/>',
                  label(810, y+6, f"{100*k/n:.2f}%", 18, color, 700),
                  label(920, y+6, f"{k:,} / {n:,}", 17, GRAY)]
    items.append(label(36, 621, "Lines show descriptive 95% Wilson intervals under a binomial assumption.", 17, GRAY))
    save("failure-rates", 650, title, items)


if __name__ == "__main__":
    data = read("failure_rates")
    overview(data)
    cohort_plot(data)
