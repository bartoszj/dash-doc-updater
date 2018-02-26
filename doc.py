import yaml
import re
import subprocess
import time
from typing import List, Tuple, Optional, TypeVar
from pkg_resources import parse_version, SetuptoolsVersion
from pathlib import Path
from pygit2 import clone_repository, Repository, GIT_FETCH_PRUNE
from abc import ABC, abstractmethod

V = TypeVar("V", bound="Version")


class Version(object):
    def __init__(self, version):
        self.name = version
        """Version name"""
        self.version: SetuptoolsVersion = parse_version(version)
        """Version object"""

    def __str__(self):
        return f"<Version({self.name}, {str(self.version)})>"

    def __repr__(self):
        return f"<Version({self.name}, {str(self.version)})>"

    def __hash__(self):
        return hash(self.version)

    def __lt__(self, other: V):
        return self.version.__lt__(other.version)

    def __le__(self, other: V):
        return self.version.__le__(other.version)

    def __eq__(self, other: V):
        return self.version.__eq__(other.version)

    def __ge__(self, other: V):
        return self.version.__ge__(other.version)

    def __gt__(self, other: V):
        return self.version.__gt__(other.version)

    def __ne__(self, other: V):
        return self.version.__ne__(other.version)


class Documentation(ABC):
    """
    Abstract class for all documentation updaters
    """
    def __init__(self):
        self.versions: List[Version] = []
        """List of version which have to be updated"""

    @abstractmethod
    def check_updates(self):
        """
        Check for new available versions.
        """
        pass

    @abstractmethod
    def update_version(self, version: Version) -> Optional[Path]:
        """
        Generate documentation for selected version.
        :param version: Version to generate.
        :return: Path to generated documentation.
        """
        pass

    def update(self) -> List[Tuple[Version, Path]]:
        """
        Check for new available versions and generate documentation for new versions.
        :return: List of generated versions and generated documentations
        """
        updated: List[Tuple[Version, Path]] = []
        self.check_updates()
        for version in self.versions:
            path = self.update_version(version)
            if path is not None:
                updated.append((version, path))

        return updated


class TagDocumentation(Documentation):
    """
    Base class for documentation updaters which are using tags to find new versions.
    """

    def __init__(self, path: str, repository_path: str, git_url: str, minimum_version: str,
                 processed_versions_file: str, doc_name: str, build_folder: str = "build"):
        """
        Initialize updater object with configuration.

        :param path: Path to the documentation generator.
        :param repository_path: Path to cloned repository.
        :param git_url: URL to git repository.
        :param minimum_version: Minimum supported version.
        :param processed_versions_file: File name of the processed versions.
        :param doc_name: Name of the generated documentation file.
        :param build_folder: Name of the build folder.
        """
        super().__init__()

        self.path = Path(path)
        """Path to Kubernetes documentation generator"""

        self.repository_path = self.path.joinpath(repository_path)
        """Path to Kubernetes repository"""

        self.git_url = git_url
        """URL to git repository"""

        self.repo: Repository = None
        """Git repository"""

        self.minimum_version = Version(minimum_version)
        """Minimum supported version"""

        self.processed_versions_file = processed_versions_file
        """File name of the processed versions"""

        self.processed_versions: List[Version] = []
        """List of already versions"""

        self.build_folder = build_folder
        """Name of the build folder"""

        self.doc_name = doc_name
        """Name of the generated documentation file"""

        self.load_processed_versions()
        self.initialize_repo()

    def load_processed_versions(self):
        """
        Load processed versions from file on disk.

        Versions are available in the `processed_versions` variable.
        """
        with open(self.processed_versions_file) as f:
            config = yaml.load(f)
            versions = config["versions"]
            self.processed_versions = [Version(v) for v in versions]

    def initialize_repo(self):
        """
        Initialize local repository.

        Repository is available from `repo` veriable.
        """
        # Initialize new repository
        if not self.repository_path.exists():
            print(f"{self.__class__.__name__} clonning...")
            self.repository_path.mkdir(parents=True)
            self.repo = clone_repository(self.git_url, str(self.repository_path))
        # Read repository
        else:
            self.repo = Repository(str(self.repository_path))

    def save_processed_versions(self):
        """
        Save processed version to file on disk.
        """
        with open(self.processed_versions_file, "w") as f:
            versions = [v.name for v in sorted(self.processed_versions)]
            config = {"versions": versions}
            yaml.dump(config, f, default_flow_style=False)

    @classmethod
    def normalize_tag(cls, tag: str) -> str:
        """
        Normalize version from tag.

        It can for example remove "v" at the beginning of the name.
        """
        return tag

    def check_updates(self):
        """
        Check for new available versions.

        Fetches new tags
        """
        super().check_updates()
        print(f"{self.__class__.__name__} fetching...")
        for remote in self.repo.remotes:
            remote.fetch(prune=GIT_FETCH_PRUNE)

        # Parse versions
        tag_prefix = "refs/tags/"
        regex = re.compile(f"^{tag_prefix}")
        versions: List[Version] = []
        for tag in filter(lambda r: regex.match(r), self.repo.listall_references()):  # type: str
            tag = tag.replace(tag_prefix, "")

            tag = self.__class__.normalize_tag(tag)

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

    @classmethod
    def command(cls, version: Version) -> str:
        """
        Prepares command which will be used to generate documentation.
        :param version: Version to generate.
        :return: Command which will be used to generate documentation.
        """
        return f"./build.sh {version.name}"

    def update_version(self, version: Version) -> Optional[Path]:
        """
        Generate documentation for selected version.
        :param version: Version to generate.
        :return: Path to generated documentation.
        """
        print(f"{self.__class__.__name__} {version.name} processing...")
        start_time = time.time()
        process = subprocess.run(
            self.__class__.command(version),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            cwd=self.path)
        stop_time = time.time()
        time_elapsed = stop_time - start_time

        # Success
        if process.returncode == 0:
            print(f"{self.__class__.__name__} {version.name} success {time_elapsed:0.3f}s...")
            self.processed_versions.append(version)
            self.save_processed_versions()

            build_path = self.path.\
                joinpath(self.build_folder).\
                joinpath(version.name).\
                joinpath(self.doc_name)
            print(build_path)
            return build_path
        # Error
        else:
            print(f"{self.__class__.__name__} {version.name} failed...")
            print("stdout:")
            print(process.stdout)
            print("stderr:")
            print(process.stderr)
        return None
