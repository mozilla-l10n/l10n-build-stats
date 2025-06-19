#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Extract completion statistics for Fenix

python firefox_stats.py --path path_to_mozilla_firefox_clone
"""

from collections import defaultdict
from functions import (
    get_fxios_releases,
    get_ios_locale,
    read_config,
    store_fxios_completion,
    update_git_repository,
)
from pathlib import Path
from urllib.parse import quote as urlquote
from urllib.request import urlopen
import argparse
import json
import sys


def find_strings_files(repo_path, localizable_paths):
    strings_files = []
    repo_path = Path(repo_path)

    for relative_dir in localizable_paths:
        lproj_dir = repo_path / relative_dir
        if not lproj_dir.is_dir():
            continue

        for strings_file in lproj_dir.glob("*.strings"):
            strings_files.append(str(strings_file.relative_to(repo_path)))

    return strings_files


def extract_strings(repo_path, ref_files, locale, string_list):
    repo_path = Path(repo_path)
    ios_locale = get_ios_locale(locale)
    for ref_file in ref_files:
        f = ref_file
        if locale != "en-US":
            f = f.replace("en-US.lproj/", f"{ios_locale}.lproj/").replace(
                "Base.lproj/", f"{ios_locale}.lproj/"
            )

        key_file_name = ref_file.replace("en-US.lproj/", "").replace("Base.lproj/", "")
        if key_file_name not in string_list:
            string_list[key_file_name] = {}
        if locale not in string_list[key_file_name]:
            string_list[key_file_name][locale] = []

        if not (repo_path / f).is_file():
            continue
        with open(repo_path / f, "r", encoding="utf-8") as file:
            for line in file:
                if line.startswith('"') and " = " in line:
                    string_id, _ = line.split(" = ", 1)
                    string_id = string_id.strip('"')
                    string_list[key_file_name][locale].append(string_id)


def compute_localization_completion(string_list, ref_locale="en-US"):
    completion = defaultdict(
        lambda: {"total": 0, "translated": 0, "missing": [], "percentage": 0.0}
    )

    for file_path, locales in string_list.items():
        ref_ids = set(locales.get(ref_locale, []))
        for locale, ids in locales.items():
            if locale == ref_locale:
                continue
            target_ids = set(ids)
            # Exclude IDs that don't exist in the reference locale
            valid_ids = ref_ids & target_ids
            missing = ref_ids - valid_ids

            completion[locale]["total"] += len(ref_ids)
            completion[locale]["translated"] += len(valid_ids)
            completion[locale]["missing"].extend(
                f"{file_path}:{msgid}" for msgid in sorted(missing)
            )

    for locale, stats in completion.items():
        total = stats["total"]
        missing = len(stats["missing"])
        stats["percentage"] = (
            round(100 * (total - missing) / total, 1) if total else 0.0
        )

    return dict(completion)


def get_fxios_locales():
    query = """
{
  project(slug: "firefox-for-ios") {
    localizations {
      locale {
        code
      }
    }
  }
}
"""
    locales = []
    try:
        url = f"https://pontoon.mozilla.org/graphql?query={urlquote(query)}&raw"
        print("Reading sources for Pontoon")
        response = urlopen(url)
        json_data = json.load(response)
        for locale in json_data["data"]["project"]["localizations"]:
            locales.append(locale["locale"]["code"])
        locales.sort()
    except Exception as e:
        sys.exit(e)

    return locales


def main():
    cl_parser = argparse.ArgumentParser()
    cl_parser.add_argument(
        "--version",
        required=True,
        dest="version",
        help="Version of Firefox for iOS to check",
    )
    args = cl_parser.parse_args()

    version = args.version
    [firefox_ios_path] = read_config(["firefox_ios_path"])

    # Get the release tags from mozilla-unified
    fxios_releases = get_fxios_releases(firefox_ios_path)
    if version not in fxios_releases:
        sys.exit(f"Version {version} not available as a release in repository tags")

    # Update the source repository to the tag
    update_git_repository(fxios_releases[version], firefox_ios_path)

    localizable_paths = [
        "firefox-ios/Client/en-US.lproj",
        "firefox-ios/Shared/en-US.lproj",
        "firefox-ios/Shared/Supporting Files/en-US.lproj",
        "firefox-ios/WidgetKit/en-US.lproj",
    ]
    ref_strings_files = find_strings_files(firefox_ios_path, localizable_paths)

    string_list = {}
    # Extract reference strings first
    extract_strings(firefox_ios_path, ref_strings_files, "en-US", string_list)

    # Extract other locales
    locales = get_fxios_locales()

    for locale in locales:
        extract_strings(firefox_ios_path, ref_strings_files, locale, string_list)

    # Determine completion levels
    completion = compute_localization_completion(string_list)

    # Store completion levels in CSV file
    store_fxios_completion(completion, version, "fxios")


if __name__ == "__main__":
    main()
