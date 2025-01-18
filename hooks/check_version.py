#!/usr/bin/python
import importlib.metadata
import json

import tomllib

if __name__ == "__main__":
    """Check if the version in pyproject.toml matches the manifest."""
    try:
        installed_version = importlib.metadata.version("homeassistant-gtfs-realtime")
        with open("custom_components/gtfs_realtime/manifest.json") as f:
            manifest_version = json.load(f)["version"]
        with open("pyproject.toml", "rb") as f:
            pyproject_version = tomllib.load(f)["tool"]["poetry"]["version"]
        if installed_version == manifest_version == pyproject_version:
            exit(0)
        else:
            print(
                "Versions do not match: ",
                f"{installed_version=}, {manifest_version=}, {pyproject_version=}",
            )
            exit(1)
    except Exception as e:
        print(f"An error occurred {e}")
