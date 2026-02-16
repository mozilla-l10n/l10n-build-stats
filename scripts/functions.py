import json
import os
import re
import subprocess

from re import Match, Pattern

from logging_config import get_logger
from moz.l10n.formats import UnsupportedFormat
from moz.l10n.model import Entry
from moz.l10n.resource import parse_resource


logger = get_logger(__name__)


StringList = dict[str, dict[str, list[str]]]


def store_completion(
    string_list: dict[str, dict[str, list[str]]],
    version: str,
    locales: list[str],
    product: str,
) -> None:
    """
    Calculate and store localization completion statistics to a JSON file.

    Args:
        string_list: Nested dict mapping file -> locale -> string IDs
        version: Product version (e.g., "147.0")
        locales: List of locale codes to process
        product: Product name ("firefox" or "fenix")

    Raises:
        ZeroDivisionError: If source has no strings (shouldn't happen)
        OSError: If output file can't be written
    """
    completion: dict[str, float] = {}
    stats_path = get_stats_path()
    source_stats: int = sum(
        len(values.get("source", [])) for values in string_list.values()
    )

    for locale in locales:
        if locale == "source":
            continue
        locale_stats: int = sum(
            len(values.get(locale, [])) for values in string_list.values()
        )
        completion[locale] = round((locale_stats / source_stats), 4)

    for locale, percentage in completion.items():
        logger.info(f"{locale}: {round(percentage * 100, 2)}%")

    output_file: str = os.path.join(
        stats_path, f"{product}_{version.replace('.', '_')}.json"
    )
    with open(output_file, "w") as f:
        json.dump(completion, f)


def get_firefox_releases(repo_path: str) -> dict[str, str]:
    """
    Extract Firefox release tags from a git repository.

    Args:
        repo_path: Path to the git repository

    Returns:
        Dictionary mapping version strings to git tag names

    Raises:
        RuntimeError: If git command fails
    """
    logger.info("Extracting tags from repository")
    result = subprocess.run(
        ["git", "-C", repo_path, "tag", "-l", "FIREFOX_*"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Error running git tag: {result.stderr}")

    # Filter output using regex
    output: str = result.stdout
    tag_re: Pattern[str] = re.compile(r"(FIREFOX_([0-9_]*)_RELEASE)")
    filtered_lines: list[str] = [
        line for line in output.splitlines() if tag_re.search(line)
    ]

    # Process the filtered lines to extract version
    releases: dict[str, str] = {}
    for line in filtered_lines:
        match: Match[str] | None = tag_re.search(line)
        if match:
            tag_name: str = match.group(1)
            version: str = match.group(2).replace("_", ".")
            releases[version] = tag_name

    return releases


def get_stats_path() -> str:
    """
    Get the absolute path to the stats directory.

    Returns:
        Absolute path to the stats directory
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "stats"))


def update_git_repository(changeset: str, repo_path: str) -> None:
    """
    Update git repository to a specific changeset.

    Args:
        changeset: Git changeset/tag/branch to checkout
        repo_path: Path to the git repository

    Raises:
        RuntimeError: If git checkout fails
    """
    logger.info(f"Updating git repository to changeset: {changeset}")
    result = subprocess.run(
        ["git", "-C", repo_path, "checkout", changeset],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Error updating repository to {changeset}: {result.stderr}")


def get_json_files(product: str) -> list[str]:
    """
    List all JSON statistics files for a given product.

    Args:
        product: Product name ("firefox" or "fenix")

    Returns:
        Sorted list of JSON filenames for the product
    """
    # List all JSON files starting with the product name
    stats_path = get_stats_path()
    json_files = [
        f
        for f in os.listdir(stats_path)
        if f.startswith(product) and f.endswith(".json")
    ]
    json_files.sort()

    return json_files


def get_version_from_filename(filename: str) -> tuple[str, str]:
    """
    Extract version information from a statistics filename.

    Args:
        filename: Filename like "firefox_147_0.json"

    Returns:
        Tuple of (full_version, major_version) e.g., ("147.0", "147")
    """
    version_re = re.compile(r"_([\d_]*)")
    match: Match[str] | None = version_re.search(filename)
    assert match is not None
    version: str = match.group(1).replace("_", ".")
    major_version: str = version.split(".")[0]

    return version, major_version


def parse_file(
    file_path: str,
    rel_file: str,
    locale: str,
    string_list: StringList,
    version: str = "",
) -> None:
    """
    Parse a localization file and extract string IDs.

    Args:
        file_path: Absolute path to the file to parse
        rel_file: Relative file path (used as dict key)
        locale: Locale code ("source" for reference files)
        string_list: Dict to update with parsed string IDs
        version: Product version (for Android removedIn meta check)

    Side effects:
        Updates string_list dict with parsed string IDs
    """

    def store(id: str) -> None:
        string_list[rel_file][locale].append(id)

    def meta_include(entry: Entry) -> bool:
        if entry.meta is None:
            return True

        removed_in = entry.get_meta("{http://mozac.org/tools}removedIn")
        removed = removed_in and int(removed_in) < int(version.split(".")[0])
        if removed:
            logger.debug(f"Ignoring {entry_id} because removed in version {removed_in}")

        tools_ignore = entry.get_meta("{http://schemas.android.com/tools}ignore")
        unused = "UnusedResources" in str(tools_ignore).split(",")
        if unused and not removed:
            logger.debug(f"Ignoring {entry_id} because marked as UnusedResources")

        return not (unused or removed)

    if rel_file not in string_list:
        string_list[rel_file] = {}
    if locale not in string_list[rel_file]:
        string_list[rel_file][locale] = []

    try:
        resource = parse_resource(file_path)
        for section in resource.sections:
            for entry in section.entries:
                if not isinstance(entry, Entry):
                    continue

                entry_id = ".".join(section.id + entry.id)
                if locale == "source":
                    if meta_include(entry):
                        store(entry_id)
                elif entry_id in string_list[rel_file]["source"]:
                    store(entry_id)

                """
                This step is not strictly necessary: we could just look at
                the message since Pontoon will prevent from saving a
                translation with missing attributes. Just an additional check
                in case something went wrong (manual edits, migrations).
                """
                if entry.properties:
                    for attribute in entry.properties:
                        attr_id = f"{entry_id}.{attribute}"
                        if (
                            locale == "source"
                            or attr_id in string_list[rel_file]["source"]
                        ):
                            store(attr_id)
    except UnsupportedFormat:
        if locale == "source":
            logger.warning(f"Unsupported format: {rel_file}")
    except Exception as e:
        logger.error(f"Error parsing file: {rel_file}")
        logger.error(e)
