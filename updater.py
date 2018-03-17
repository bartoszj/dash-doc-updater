#! /usr/bin/env python
import argparse
import yaml
import shutil
import json
from typing import List, Tuple
from pathlib import Path
from doc import Documentation, Version
from kubernetes import Kubernetes
from packer import Packer
from terraform import Terraform

CONFIG_PATH = "config.yml"

parser = argparse.ArgumentParser(description="Check for updates in the tracked dash repositories")
args = parser.parse_args()


class Dash:
    """
    Represents "Dash-User-Contributions" repository.
    """

    def __init__(self, path: str):
        """
        Initialize "Dash-User-Contributions" repository.
        :param path: Path to the repository
        """

        self.path = Path(path)

    def add_version(self, doc_name: str, version: Version, doc_path: Path):
        """
        Add new version to doc set.

        :param doc_name: Documentation name.
        :param version: Version of the new documentation.
        :param doc_path: Path to generated documentation.
        """
        doc_set_path = self.path.joinpath("docsets").joinpath(doc_name)
        doc_set_json_path = doc_set_path.joinpath("docset.json")
        versions_dir_path = doc_set_path.joinpath("versions")
        version_dir_path = versions_dir_path.joinpath(version.name)
        dst_doc_path = version_dir_path.joinpath(doc_path.name)
        relative_dst_doc_path = dst_doc_path.relative_to(doc_set_path)

        # Create new version directory.
        version_dir_path.mkdir(parents=True, exist_ok=True)

        # Copy new doc to doc set.
        shutil.copy(str(doc_path), str(version_dir_path))
        print(f"{doc_name} added version: {version.name}")

        # Update docset.json.
        with open(doc_set_json_path, "r+") as f:
            j = json.load(f)

            specific_versions = j["specific_versions"]
            specific_versions = self.append_version(specific_versions, version, relative_dst_doc_path)
            j["specific_versions"] = specific_versions

            # Save file
            f.seek(0)
            json.dump(j, f, indent=4)

    @staticmethod
    def append_version(specific_versions: list, version: Version, path: Path) -> list:
        """
        Append specific_versions entry with new version and sort results in the docset.json file.

        :param specific_versions: Existing "specific_versions".
        :param version: New version to add.
        :param path: Path to the doc.
        :return: Sorted "specific_versions" with added version.
        """
        # Check if version already exists.
        exists = False
        for v in specific_versions:  # type: dict
            ver = v["version"]
            if ver == version.name:
                exists = True
                break

        # Stop is entry exists.
        if exists:
            return specific_versions

        # Add new version.
        ver = {"version": version.name, "archive": str(path)}
        specific_versions.append(ver)

        # Sort versions.
        def key(k: dict):
            return Version(k["version"])
        specific_versions.sort(key=key, reverse=True)

        return specific_versions

    def update_newest_version(self, doc_name: str, updated_versions: List[Tuple[Version, Path]]):
        """
        Updates newest and stable version of the documentation.

        :param doc_name: Documentation name.
        :param updated_versions: List of updated versions.
        """
        doc_set_path = self.path.joinpath("docsets").joinpath(doc_name)
        doc_set_json_path = doc_set_path.joinpath("docset.json")

        # Read docset.json to get newest stable version
        with open(doc_set_json_path, "r+") as f:
            j = json.load(f)
            specific_versions = j["specific_versions"]

            versions = [Version(v["version"]) for v in specific_versions]
            stable_versions = [v for v in versions if v.is_stable]
            stable_versions.sort()

            # Not stable versions -> Exit.
            if len(stable_versions) == 0:
                return

            # Latest stable version.
            latest_stable_version = stable_versions[-1]

            # Find latest version in updates.
            latest_stable_version_path = None
            for version, path in updated_versions:
                if version == latest_stable_version:
                    latest_stable_version_path = path
                    break

            # Latest version nas not found.
            if latest_stable_version_path is None:
                return

            # Copy latest documentation.
            shutil.copy(str(latest_stable_version_path), str(doc_set_path))
            print(f"{doc_name} added default version: {version.name}")

            # Update docset.json.
            j["version"] = latest_stable_version.name
            f.seek(0)
            json.dump(j, f, indent=4)

    def add_versions(self, doc_name: str, versions: List[Tuple[Version, Path]]):
        """
        Add new versions to doc set.

        :param doc_name: Documentation name.
        :param versions: Versions to add.
        """
        for v, p in versions:
            self.add_version(doc_name, v, p)

        # Update newest version.
        self.update_newest_version(doc_name=doc_name, updated_versions=versions)


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.load(f)


if __name__ == '__main__':
    config = load_config()

    # Dash
    dash_config = config["dash"]
    dash = Dash(
        path=dash_config["path"]
    )

    docs: List[Documentation] = []

    # Kubernetes
    kubernetes_config = config["kubernetes"]
    kubernetes = Kubernetes(
        path=kubernetes_config["path"],
        repository_path=kubernetes_config["repository_path"],
        git_url=kubernetes_config["git_url"],
        minimum_version=kubernetes_config["minimum_version"]
    )
    docs.append(kubernetes)

    # Packer
    packer_config = config["packer"]
    packer = Packer(
        path=packer_config["path"],
        repository_path=packer_config["repository_path"],
        git_url=packer_config["git_url"],
        minimum_version=packer_config["minimum_version"]
    )
    docs.append(packer)

    # Terraform
    terraform_config = config["terraform"]
    terraform = Terraform(
        path=terraform_config["path"],
        repository_path=terraform_config["repository_path"],
        git_url=terraform_config["git_url"]
    )
    docs.append(terraform)

    # Start processing.
    for doc in docs:

        # Update documentation.
        updates = doc.update()

        # Add new versions.
        dash.add_versions(doc_name=doc.name, versions=updates)
