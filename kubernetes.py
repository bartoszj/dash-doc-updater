import pathlib
import re
import yaml
import subprocess
from doc import Documentation, Version
from pygit2 import clone_repository, Repository, GIT_FETCH_PRUNE
from typing import List, Optional
from pathlib import Path


class Kubernetes(Documentation):
    """
    Kubernetes updater.
    """

    kubernetes_version_file = "kubernetes.yml"
    kubernetes_build_folder = "build"
    kubernetes_doc_name = "Kubernetes.tgz"

    def __init__(self, path: str, repository_path: str, git_url: str, minimum_version: str):
        """
        Initialize Kubernetes updated object with configuration.

        :param path: Path to Kubernetes documentation generator.
        :param repository_path: Path to Kubernetes repository.
        :param git_url: URL to git repository.
        :param minimum_version: Minimum supported version.
        """
        super().__init__()

        self.path = pathlib.Path(path)
        """Path to Kubernetes documentation generator"""

        self.repository_path = self.path.joinpath(repository_path)
        """Path to Kubernetes repository"""

        self.git_url = git_url
        """URL to git repository"""

        self.repo: Repository = None
        """Git repository"""

        self.minimum_version = Version(minimum_version)
        """Minimum supported version"""

        self.processed_versions: List[Version] = []
        """List of already versions"""

        self._load_versions()
        self._initialize_repo()

    def _load_versions(self):
        with open(self.__class__.kubernetes_version_file) as f:
            config = yaml.load(f)
            versions = config["versions"]
            self.processed_versions = [Version(v) for v in versions]

    def _initialize_repo(self):
        # Initialize new repository
        if not self.repository_path.exists():
            print("Kubernetes clonning...")
            self.repository_path.mkdir(parents=True)
            self.repo = clone_repository(self.git_url, str(self.repository_path))
        # Read repository
        else:
            self.repo = Repository(str(self.repository_path))

    def _save_versions(self):
        with open(self.__class__.kubernetes_version_file, "w") as f:
            versions = [v.name for v in self.processed_versions]
            config = {"versions": versions}
            yaml.dump(config, f, default_flow_style=False)

    def check_updates(self):
        """
        Check for new available versions.
        """
        super().check_updates()
        print("Kubernetes fetching...")
        for remote in self.repo.remotes:
            remote.fetch(prune=GIT_FETCH_PRUNE)

        # Parse versions
        tag_prefix = "refs/tags/"
        version_prefix = "v"
        regex = re.compile(f"^{tag_prefix}")
        versions: List[Version] = []
        for tag in filter(lambda r: regex.match(r), self.repo.listall_references()):  # type: str
            tag = tag.replace(tag_prefix, "")
            if tag.startswith(version_prefix):
                tag = tag[len(version_prefix):]

            version = Version(tag)
            # Only newer tags
            if version < self.minimum_version:
                continue

            # Only not already processed versions:
            if version in self.processed_versions:
                continue

            versions.append(version)

        # Sort versions
        self.versions = sorted(versions)

    def update_version(self, version: Version) -> Optional[Path]:
        """
        Generate documentation for selected version.
        :param version: Version to generate.
        :return: Path to generated documentation.
        """
        print(f"Kubernetes {version.name} processing...")
        process = subprocess.run(
            f"source env/bin/activate && ./build.sh {version.name}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            cwd=self.path)

        # Success
        if process.returncode == 0:
            print(f"Kubernetes {version.name} success...")
            self.processed_versions.append(version)
            self._save_versions()

            return self.path.\
                joinpath(self.__class__.kubernetes_build_folder).\
                joinpath(version.name).\
                joinpath(self.__class__.kubernetes_doc_name)
        # Error
        else:
            print(f"Kubernetes {version.name} failed...")
            print("stdout:")
            print(process.stdout)
            print("stderr:")
            print(process.stderr)
        return None
