import json
import os
import re
import subprocess
import sys
from typing import List, Match, Pattern


def read_config(params):
    # Get absolute path of the repository's root from the script location
    root_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    config_file = os.path.join(root_folder, "config", "config")

    # Abort if config file is missing
    if not os.path.exists(config_file):
        sys.exit("ERROR: config file is missing")

    # Read all available paths in the config file
    paths = {}
    with open(config_file, "r") as cfg_file:
        for line in cfg_file:
            line = line.strip()
            # Ignore comments and empty lines
            if line == "" or line.startswith("#"):
                continue
            paths[line.split("=")[0]] = line.split("=")[1].strip('"')

    results = []
    for param in params:
        if param not in paths:
            sys.exit("{} is not defined in the config file".format(param))
        else:
            if not os.path.exists(paths[param]):
                sys.exit(
                    "Path defined for {} ({}) does not exist".format(
                        param, paths[param]
                    )
                )
        results.append(paths[param])

    return results


def store_completion(string_list, version, locales, product):
    completion = {}
    stats_path = get_stats_path()
    source_stats = sum(len(values.get("source", [])) for values in string_list.values())

    for locale in locales:
        if locale == "source":
            continue
        locale_stats = sum(
            len(values.get(locale, [])) for values in string_list.values()
        )
        completion[locale] = round((locale_stats / source_stats), 4)

    for locale, percentage in completion.items():
        print(f"{locale}: {round(percentage * 100, 2)}%")

    output_file = os.path.join(
        stats_path, f"{product}_{version.replace('.', '_')}.json"
    )
    with open(output_file, "w") as f:
        json.dump(completion, f)


def get_firefox_releases(repo_path):
    try:
        print("Extracting tags from repository")
        result = subprocess.run(
            ["git", "-C", repo_path, "tag", "-l", "FIREFOX_*"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Error running git tag: {result.stderr}")

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


def get_stats_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "stats"))


def update_git_repository(changeset, repo_path):
    try:
        print(f"Updating git repository to changeset: {changeset}")
        result = subprocess.run(
            ["git", "-C", repo_path, "checkout", changeset],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Error git updating repository to {changeset}: {result.stderr}"
            )
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def get_json_files(product: str) -> List[str]:
    # List all JSON files starting with the product name
    stats_path: str = get_stats_path()
    json_files: List[str] = [
        f
        for f in os.listdir(stats_path)
        if f.startswith(product) and f.endswith(".json")
    ]
    json_files.sort()

    return json_files


def get_version_from_filename(filename: str) -> tuple[str, str]:
    version_re: Pattern[str] = re.compile(r"_([\d_]*)")
    match: Match[str] | None = version_re.search(filename)
    assert match is not None
    version: str = match.group(1).replace("_", ".")
    major_version: str = version.split(".")[0]

    return version, major_version
