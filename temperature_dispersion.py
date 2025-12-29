import csv
import re
from collections import defaultdict
from statistics import mean, pstdev
from pathlib import Path

STATION_PATH = Path("station.csv")
SQL_PATH = Path("dump/china_data_insert.sql")
FIGURE_DIR = Path("Figure")


def load_city_provinces(station_path: Path) -> dict[str, str]:
    city_to_province: dict[str, str] = {}
    with station_path.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader, None)
        for row in reader:
            if len(row) < 4:
                continue
            province = row[2].strip()
            city = row[3].strip()
            if city and province and city not in city_to_province:
                city_to_province[city] = province
    return city_to_province


def load_city_temps(sql_path: Path, city_to_province: dict[str, str]):
    pattern = re.compile(r"\((\d+),\s*'([^']+)',\s*([-\d.]+)\)")
    in_city_temp = False
    buffer: list[str] = []

    with sql_path.open(encoding="utf-8") as file:
        for line in file:
            lower = line.lower()
            if lower.startswith("insert into city_temp"):
                in_city_temp = True
                buffer.append(line)
                continue
            if in_city_temp:
                buffer.append(line)
                if ";" in line:
                    break

    for line in buffer:
        for match in pattern.finditer(line):
            month = int(match.group(1))
            city = match.group(2)
            temp = float(match.group(3))
            province = city_to_province.get(city)
            if not province:
                continue
            yield province, city, month, temp


def build_city_monthly_map(city_month_temps):
    province_city_month: dict[str, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    for province, city, month, temp in city_month_temps:
        province_city_month[province][city][month] = temp
    return province_city_month


def compute_annual_means(province_city_month):
    province_city_annual: dict[str, dict[str, float]] = defaultdict(dict)
    for province, city_months in province_city_month.items():
        for city, months in city_months.items():
            if not months:
                continue
            province_city_annual[province][city] = mean(months.values())
    return province_city_annual


def compute_top_provinces(province_city_annual, count=2):
    dispersions = []
    for province, city_means in province_city_annual.items():
        if len(city_means) < 2:
            continue
        dispersions.append((pstdev(city_means.values()), province))
    dispersions.sort(reverse=True)
    return [province for _, province in dispersions[:count]]


def compute_monthly_dispersion(province_city_month):
    dispersions = []
    for province, city_months in province_city_month.items():
        months = defaultdict(list)
        for temps in city_months.values():
            for month, temp in temps.items():
                months[month].append(temp)
        for month, temps in months.items():
            if len(temps) < 2:
                continue
            dispersions.append((pstdev(temps), province, month))
    dispersions.sort(reverse=True)
    return dispersions


def render_bar_chart_svg(
    title,
    labels,
    values,
    xlabel,
    unit,
    width=1200,
    bar_height=18,
    label_width=140,
    margin=30,
):
    max_label_len = max((len(label) for label in labels), default=0)
    label_width = max(label_width, min(240, max_label_len * 12))
    chart_width = width - label_width - margin * 2
    height = margin * 2 + len(labels) * (bar_height + 6) + 40

    min_val = min(values)
    max_val = max(values)
    if min_val == max_val:
        min_val -= 1
        max_val += 1

    def scale(val):
        return (val - min_val) / (max_val - min_val) * chart_width

    zero_x = label_width + margin + scale(0)
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<style>text{font-family:Arial,sans-serif;font-size:12px;}</style>',
        f'<text x="{width/2}" y="{margin}" text-anchor="middle" font-size="16">{title}</text>',
        f'<line x1="{label_width + margin}" y1="{height - margin - 30}" '
        f'x2="{width - margin}" y2="{height - margin - 30}" stroke="#333"/>',
        f'<line x1="{zero_x}" y1="{margin + 20}" x2="{zero_x}" '
        f'y2="{height - margin - 30}" stroke="#666" stroke-dasharray="4"/>',
    ]

    y = margin + 30
    for label, value in zip(labels, values):
        bar_y = y
        bar_len = scale(value) - scale(0)
        bar_x = zero_x if bar_len >= 0 else zero_x + bar_len
        svg_lines.append(
            f'<text x="{label_width + margin - 6}" y="{bar_y + bar_height - 4}" '
            f'text-anchor="end">{label}</text>'
        )
        svg_lines.append(
            f'<rect x="{bar_x}" y="{bar_y}" width="{abs(bar_len)}" '
            f'height="{bar_height}" fill="#4C78A8"/>'
        )
        svg_lines.append(
            f'<text x="{bar_x + abs(bar_len) + 4}" y="{bar_y + bar_height - 4}">'
            f'{value:.2f}</text>'
        )
        y += bar_height + 6

    svg_lines.append(
        f'<text x="{width - margin}" y="{height - margin}" text-anchor="end">'
        f'{xlabel} ({unit})</text>'
    )
    svg_lines.append("</svg>")
    return "\n".join(svg_lines)


def main():
    FIGURE_DIR.mkdir(exist_ok=True)

    city_to_province = load_city_provinces(STATION_PATH)
    city_month_temps = list(load_city_temps(SQL_PATH, city_to_province))
    province_city_month = build_city_monthly_map(city_month_temps)
    province_city_annual = compute_annual_means(province_city_month)

    top_provinces = compute_top_provinces(province_city_annual, count=2)
    monthly_dispersion = compute_monthly_dispersion(province_city_month)

    if not monthly_dispersion:
        raise SystemExit("No monthly dispersion data found.")

    selected_province = monthly_dispersion[0][1]
    months_for_selected = [month for _, province, month in monthly_dispersion if province == selected_province][:3]

    for province in top_provinces:
        city_means = province_city_annual[province]
        sorted_items = sorted(city_means.items(), key=lambda x: x[1], reverse=True)
        labels = [city for city, _ in sorted_items]
        values = [val for _, val in sorted_items]
        svg = render_bar_chart_svg(
            title=f"{province} 各市全年均温",
            labels=labels,
            values=values,
            xlabel="全年均温",
            unit="原始单位",
        )
        (FIGURE_DIR / f"annual_mean_{province}.svg").write_text(svg, encoding="utf-8")

    for month in months_for_selected:
        city_temps = {
            city: temps.get(month)
            for city, temps in province_city_month[selected_province].items()
        }
        city_temps = {city: temp for city, temp in city_temps.items() if temp is not None}
        sorted_items = sorted(city_temps.items(), key=lambda x: x[1], reverse=True)
        labels = [city for city, _ in sorted_items]
        values = [val for _, val in sorted_items]
        svg = render_bar_chart_svg(
            title=f"{selected_province} {month}月各市月均温",
            labels=labels,
            values=values,
            xlabel=f"{month}月均温",
            unit="原始单位",
        )
        (FIGURE_DIR / f"monthly_mean_{selected_province}_{month}.svg").write_text(
            svg, encoding="utf-8"
        )

    print("Annual top provinces:", top_provinces)
    print("Selected province for monthly charts:", selected_province, "months:", months_for_selected)


if __name__ == "__main__":
    main()
