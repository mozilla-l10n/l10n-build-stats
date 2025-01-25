#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Extract completion statistics for Fenix

python fenix_stats.py --path path_to_mozilla_unified_clone
"""

from compare_locales import paths
import xml.etree.ElementTree as ET
import argparse
import json
import os
import re
import sys
import subprocess


def getFirefoxReleases(repo_path):
    try:
        print("Extracting tags from repository")
        result = subprocess.run(
            ["hg", "-R", repo_path, "tags"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Error running hg tags: {result.stderr}")

        # Filter output using regex
        output = result.stdout
        tag_re = re.compile(r"(FIREFOX_([0-9_]*)_RELEASE)")
        filtered_lines = [line for line in output.splitlines() if tag_re.search(line)]

        # Process the filtered lines to extract version
        releases = {}
        for line in filtered_lines:
            match = tag_re.search(line)
            if match:
                tag_name = match.group(1)
                version = match.group(2).replace("_", ".")
                releases[version] = tag_name

        return releases

    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def updateRepository(tag, repo_path):
    try:
        print(f"Updating repository to tag: {tag}")
        result = subprocess.run(
            ["hg", "-R", repo_path, "update", tag],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Error updating repository to {tag}: {result.stderr}")
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def parseXMLFile(file_path, source=False):
    """
    Parse the strings.xml file and return a list of string IDs.

    If it's the source locale, exclude strings with tools:ignore="UnusedResources".
    """
    string_ids = []

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        for string in root.findall("string"):
            if source:
                tools_ignore = string.attrib.get(
                    "{http://schemas.android.com/tools}ignore", ""
                )
                if "UnusedResources" not in tools_ignore.split(","):
                    string_ids.append(string.attrib["name"])
            else:
                string_ids.append(string.attrib["name"])
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return string_ids


def extractStringList(repo_path):
    toml_paths = {
        "fenix": os.path.join(repo_path, "mobile", "android", "fenix", "l10n.toml"),
        "android-components": os.path.join(
            repo_path, "mobile", "android", "android-components", "l10n.toml"
        ),
    }

    string_list = {}
    all_locales = []
    for product, toml_path in toml_paths.items():
        if not os.path.exists(toml_path):
            sys.exit(f"Missing config file {os.path.relpath(toml_path, repo_path)}.")

        basedir = os.path.dirname(toml_path)
        project_config = paths.TOMLParser().parse(toml_path, env={"l10n_base": ""})
        basedir = os.path.join(basedir, project_config.root)

        # Get the list of message IDs for the source locale
        files = paths.ProjectFiles(None, [project_config])
        for l10n_file, source_file, _, _ in files:
            key = f"{product}:{os.path.relpath(source_file, basedir)}"
            string_list[key] = {
                "source": parseXMLFile(source_file, source=True),
            }

        locales = project_config.all_locales
        # Storing a superset of all locales across TOML files
        all_locales = list(set(locales + all_locales))
        for locale in locales:
            files = paths.ProjectFiles(locale, [project_config])
            for l10n_file, source_file, _, _ in files:
                # Ignore missing files for locale
                if not os.path.exists(l10n_file):
                    continue
                key = f"{product}:{os.path.relpath(source_file, basedir)}"
                if key not in string_list:
                    print(
                        f"Extra file {os.path.relpath(l10n_file, basedir)} in {locale}"
                    )
                    continue
                # Remove extra strings not available in source
                string_list[key][locale] = [
                    id
                    for id in parseXMLFile(l10n_file)
                    if id in string_list[key]["source"]
                ]

    return string_list, locales


def main():
    cl_parser = argparse.ArgumentParser()
    cl_parser.add_argument(
        "--path",
        required=True,
        dest="repo_path",
        help="Path to local clone of mozilla-unified",
    )
    cl_parser.add_argument(
        "--version",
        required=True,
        dest="version",
        help="Version of Firefox to check",
    )
    args = cl_parser.parse_args()

    version = args.version
    repo_path = args.repo_path

    # Get absolute path of ../stats from the current script location
    output_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "stats")
    )

    # Get the release tags from mozilla-unified
    firefox_releases = getFirefoxReleases(repo_path)
    if version not in firefox_releases:
        sys.exit(f"Version {version} not available as a release in repository tags")

    # Update the repository to the tag
    updateRepository(firefox_releases[version], repo_path)

    # Extract list statistics
    string_list, locales = extractStringList(repo_path)

    completion = {}
    source_stats = sum(len(values.get("source", [])) for values in string_list.values())

    for locale in locales:
        if locale == "source":
            continue
        locale_stats = sum(
            len(values.get(locale, [])) for values in string_list.values()
        )
        completion[locale] = round((locale_stats / source_stats) * 100)

    for locale, perc in completion.items():
        print(f"{locale}: {perc}%")

    output_file = os.path.join(output_path, f"fenix_{version.replace('.', '_')}.json")
    with open(output_file, "w") as f:
        json.dump(completion, f)


if __name__ == "__main__":
    main()
