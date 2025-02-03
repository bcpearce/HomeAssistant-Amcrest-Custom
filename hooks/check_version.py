#!/usr/bin/python
import importlib.metadata
import json
import subprocess
import tomllib

if __name__ == "__main__":
    """Check if the version in pyproject.toml matches the manifest."""
    try:
        installed_version = importlib.metadata.version("homeassistant-amcrest-custom")
        with open("custom_components/amcrest/manifest.json") as f:
            manifest_version = json.load(f)["version"]
        with open("pyproject.toml", "rb") as f:
            pyproject_version = tomllib.load(f)["project"]["version"]
        if len({installed_version, manifest_version, pyproject_version}) != 1:
            print(
                "Versions do not match: ",
                f"{installed_version=}, {manifest_version=}, {pyproject_version=}",
            )
            exit(1)

        # check that a tag does not already exist for a version
        tag_proc = subprocess.run(["git", "tag"], capture_output=True)
        tags = tag_proc.stdout.decode().split("\n")
        if manifest_version in tags:
            print(f"Error, a tagged version {manifest_version} already exists")
            exit(1)
    except Exception as e:
        print(f"An error occurred {e}")
        exit(1)
