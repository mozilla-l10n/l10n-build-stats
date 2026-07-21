#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Generate a Slack-ready summary comparing the two most recent major releases
for the top 25 locales of each product.

python scripts/generate_summary.py
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import sys

from typing import Any, TypedDict

import gspread

from logging_config import get_logger, setup_logging


logger = get_logger(__name__)


ROOT_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_FILE: str = os.path.join(ROOT_PATH, "docs", "data", "data.json")
API_CONFIG: str = os.path.join(ROOT_PATH, "api_config.env")

# Stable gids of the per-product detail sheets in the workbook.
SHEET_GIDS: dict[str, int] = {"firefox": 1198308940, "fenix": 1449426221}

# Confluence summary page used as the "summary charts" link in the header.
SUMMARY_CHARTS_URL: str = (
    "https://mozilla-hub.atlassian.net/wiki/spaces/FDPDT/pages/563806484/"
    "Localization+Team+Weekly+Business+Review+WBR#Product-Localization-Status"
)

# Magnitude (in percentage points) at which a locale change is called out.
NOTABLE_THRESHOLD_PP: float = 1.0

PRODUCT_LABELS: dict[str, str] = {"firefox": "Desktop", "fenix": "Android"}


class LocaleChange(TypedDict):
    code: str
    name: str
    previous: float
    latest: float
    delta_pp: float


class DotReleaseGain(TypedDict):
    code: str
    name: str
    base: float
    latest: float
    delta_pp: float


def load_completion_data() -> dict[str, dict[str, Any]]:
    """Load the chart data file produced by build_chart_json.py."""
    if not os.path.exists(DATA_FILE):
        sys.exit(
            f"Missing {os.path.relpath(DATA_FILE, ROOT_PATH)}. "
            "Run scripts/build_chart_json.py first."
        )
    with open(DATA_FILE) as f:
        return json.load(f)


def read_api_config() -> dict[str, str]:
    """Read the [GDOCS] section of api_config.env."""
    if not os.path.exists(API_CONFIG):
        sys.exit(
            f"Missing {os.path.relpath(API_CONFIG, ROOT_PATH)}. "
            "Copy api_config.env.example and fill in your service account."
        )
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(API_CONFIG)
    return dict(parser.items("GDOCS"))


def build_credentials(cfg: dict[str, str]) -> dict[str, str]:
    return {
        "type": "service_account",
        "project_id": cfg["gspread_project_id"],
        "private_key_id": cfg["gspread_private_key_id"],
        "private_key": cfg["gspread_private_key"].replace("\\n", "\n"),
        "client_id": cfg["gspread_client_id"],
        "client_email": cfg["gspread_client_email"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": cfg["client_x509_cert_url"],
    }


def fetch_top_locales(cfg: dict[str, str], limit: int = 25) -> dict[str, list[str]]:
    """
    Read the "Top Locales" worksheet and return the top `limit` locales per product.

    Expects two header cells named 'firefox' and 'fenix' (case-insensitive),
    with locale codes underneath.
    """
    connection = gspread.service_account_from_dict(build_credentials(cfg))
    sh = connection.open_by_key(cfg["spreadsheet_key"])
    try:
        ws = sh.worksheet("Top Locales")
    except gspread.exceptions.WorksheetNotFound:
        sys.exit("Worksheet 'Top Locales' not found in the spreadsheet.")

    rows = ws.get_all_values()
    if not rows:
        sys.exit("'Top Locales' worksheet is empty.")

    header = [c.strip().lower() for c in rows[0]]
    out: dict[str, list[str]] = {}
    for product in ("firefox", "fenix"):
        if product not in header:
            sys.exit(
                f"Column '{product}' not found in 'Top Locales' header: {rows[0]!r}"
            )
        col = header.index(product)
        codes: list[str] = []
        for row in rows[1:]:
            if len(row) <= col:
                continue
            code = row[col].strip()
            if code:
                codes.append(code)
            if len(codes) >= limit:
                break
        out[product] = codes
    return out


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in version.split("."))


def collect_versions(data: dict[str, dict[str, Any]], product: str) -> list[str]:
    seen: set[str] = set()
    for entry in data.values():
        seen.update(entry.get(product, {}).keys())
    return sorted(seen, key=_version_key)


def latest_dot_release(versions: list[str], major: str) -> str:
    candidates = [v for v in versions if v.split(".")[0] == major]
    return max(candidates, key=_version_key)


def find_two_latest_majors(versions: list[str]) -> tuple[str, str]:
    majors = sorted({int(v.split(".")[0]) for v in versions}, reverse=True)
    if len(majors) < 2:
        sys.exit(f"Need at least two major versions, found: {majors}")
    return str(majors[1]), str(majors[0])


def build_locale_changes(
    data: dict[str, dict[str, Any]],
    product: str,
    previous_version: str,
    latest_version: str,
    top_locales: list[str],
) -> list[LocaleChange]:
    rows: list[LocaleChange] = []
    for code in top_locales:
        series = data.get(code, {}).get(product)
        if not series:
            continue
        prev = series.get(previous_version)
        cur = series.get(latest_version)
        if prev is None or cur is None:
            continue
        rows.append(
            {
                "code": code,
                "name": data[code].get("name", code),
                "previous": float(prev),
                "latest": float(cur),
                "delta_pp": (float(cur) - float(prev)) * 100,
            }
        )
    return rows


def build_dot_release_gains(
    data: dict[str, dict[str, Any]],
    product: str,
    base_version: str,
    latest_version: str,
    top_locales: list[str],
) -> list[DotReleaseGain]:
    if base_version == latest_version:
        return []
    gains: list[DotReleaseGain] = []
    for code in top_locales:
        series = data.get(code, {}).get(product)
        if not series:
            continue
        base = series.get(base_version)
        cur = series.get(latest_version)
        if base is None or cur is None:
            continue
        delta = (float(cur) - float(base)) * 100
        if delta >= NOTABLE_THRESHOLD_PP:
            gains.append(
                {
                    "code": code,
                    "name": data[code].get("name", code),
                    "base": float(base),
                    "latest": float(cur),
                    "delta_pp": delta,
                }
            )
    return gains


def fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def fmt_delta(delta_pp: float) -> str:
    sign = "+" if delta_pp > 0 else ("-" if delta_pp < 0 else "±")
    return f"{sign}{abs(delta_pp):.2f}%"


def render_product_paragraph(
    product: str,
    spreadsheet_key: str,
    previous_major: str,
    latest_dot_version: str,
    base_version: str,
    changes: list[LocaleChange],
    gains: list[DotReleaseGain],
) -> str:
    label = PRODUCT_LABELS[product]
    gid = SHEET_GIDS[product]
    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_key}"
        f"/edit?gid={gid}#gid={gid}"
    )

    notable = [c for c in changes if abs(c["delta_pp"]) >= NOTABLE_THRESHOLD_PP]
    notable.sort(key=lambda c: c["delta_pp"])  # most negative first

    improved = sum(1 for c in changes if c["delta_pp"] > 0)
    declined = sum(1 for c in changes if c["delta_pp"] < 0)

    lead = (
        f"{improved} of the top 25 locales improved and {declined} declined "
        f"vs fx{previous_major}."
    )
    parts: list[str] = [f"[{label}]({url}): {lead}"]

    if notable:
        items = [
            f"{c['name']} ({fmt_delta(c['delta_pp'])}) now at {fmt_pct(c['latest'])}"
            for c in notable
        ]
        parts.append("Notable changes (|Δ| ≥ 1.00pp): " + "; ".join(items) + ".")
    else:
        parts.append("No locale moved by more than ±1.00 percentage points.")

    if gains and base_version != latest_dot_version:
        items = [
            f"{g['name']} (+{g['delta_pp']:.2f}%, now {fmt_pct(g['latest'])})"
            for g in sorted(gains, key=lambda g: -g["delta_pp"])
        ]
        parts.append(
            f"Dot-release improvements ({base_version} → {latest_dot_version}): "
            + ", ".join(items)
            + "."
        )

    return " ".join(parts)


def main() -> None:
    setup_logging()

    argparse.ArgumentParser(description=__doc__).parse_args()

    data = load_completion_data()
    cfg = read_api_config()
    spreadsheet_key = cfg["spreadsheet_key"]
    top_locales = fetch_top_locales(cfg)

    paragraphs: list[str] = []
    latest_major: str = ""
    for product in ("firefox", "fenix"):
        versions = collect_versions(data, product)
        if not versions:
            sys.exit(f"No version data for product '{product}' in {DATA_FILE}.")
        prev_major, cur_major = find_two_latest_majors(versions)
        # Compare the major base releases (e.g. 152.0 -> 153.0), not the latest
        # dot release of each major. The dot-release section below still tracks
        # improvements within the current major (base -> latest dot).
        previous_version = f"{prev_major}.0"
        latest_version = f"{cur_major}.0"
        latest_dot = latest_dot_release(versions, cur_major)
        base_version = f"{cur_major}.0"
        latest_major = cur_major

        changes = build_locale_changes(
            data, product, previous_version, latest_version, top_locales[product]
        )
        gains = build_dot_release_gains(
            data, product, base_version, latest_dot, top_locales[product]
        )
        paragraphs.append(
            render_product_paragraph(
                product,
                spreadsheet_key,
                prev_major,
                latest_dot,
                base_version,
                changes,
                gains,
            )
        )

    header = (
        f"Extracted completion data for fx{latest_major} "
        f"([summary charts]({SUMMARY_CHARTS_URL}))."
    )
    print(header)
    print()
    print(paragraphs[0])
    print()
    print(paragraphs[1])


if __name__ == "__main__":
    main()
