import yaml
import re
import subprocess
import time
import pygit2
from typing import List, Tuple, Optional, TypeVar
from pkg_resources import parse_version
from setuptools.extern.packaging.version import Version as SetuptoolsVersion
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

    @property
    def is_stable(self):
        return not self.version.is_prerelease and not self.version.is_postrelease

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
    def __init__(self, path: str, **kwargs):
        """
        Initialize Documentation updated object with empty list of version to update.

        :param path: Path to the documentation generator.
        :param kwargs: Parameters passed by child classes.
        """

        self.path = Path(path)
        """Path to the documentation generator"""

        self.versions: List[Version] = []
        """List of version which have to be updated"""

        super().__init__(**kwargs)

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def check_updates(self):
        """
        Check for new available versions.
        """
        pass

    @abstractmethod
    def build_version(self, version: Version) -> Optional[Path]:
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
            path = self.build_version(version)
            if path is not None:
                updated.append((version, path))

        return updated


class ProcessedVersions:
    """
    Handle reading and writing processed versions.
    """
    def __init__(self, processed_versions_file: str, **kwargs):
        """
        Initializer for processed versions, which loads processed versions from the file on disk.

        :param processed_versions_file: File name of the processed versions.
        """

        self.processed_versions_file = processed_versions_file
        """File name of the processed versions"""

        self.processed_versions: List[Version] = []
        """List of already versions"""

        self.load_processed_versions()

    def load_processed_versions(self):
        """
        Load processed versions from file on disk.

        Versions are available in the `processed_versions` variable.
        """
        with open(self.processed_versions_file) as f:
            config = yaml.load(f, Loader=yaml.BaseLoader)
            versions = config["versions"]
            self.processed_versions = [Version(v) for v in versions]

    def save_processed_versions(self):
        """
        Save processed version to file on disk.
        """
        with open(self.processed_versions_file, "w") as f:
            versions = [v.name for v in sorted(self.processed_versions)]
            config = {"versions": versions}
            yaml.dump(config, f, default_flow_style=False)


class RepoUpdater(Documentation):
    class Callbacks(pygit2.RemoteCallbacks):

        def credentials(self, url, username_from_url, allowed_types):
            if allowed_types & pygit2.credentials.GIT_CREDENTIAL_USERNAME:
                return pygit2.Username("git")
            elif allowed_types & pygit2.credentials.GIT_CREDENTIAL_SSH_KEY:
                return pygit2.KeypairFromAgent("git")
            else:
                return None

    """
    Handle initializing repository.
    """
    def __init__(self, repository_path: str, git_url: str, **kwargs):
        """
        Handle initializing repository.

        :param repository_path: Path to cloned repository.
        :param git_url: URL to git repository.
        """
        self.git_url = git_url
        """URL to git repository"""

        self.repo: Repository = None
        """Git repository"""

        super().__init__(**kwargs)

        self.repository_path = self.path.joinpath(repository_path)
        """Path to cloned repository"""

    def initialize_repo(self):
        """
        Initialize local repository.

        Repository is available from `repo` veriable.
        """
        # Initialize new repository
        if not self.repository_path.exists():
            print(f"{self.name} clonning...")
            self.repository_path.mkdir(parents=True)
            self.repo = clone_repository(self.git_url, str(self.repository_path), callbacks=self.Callbacks())
            self.repo.create_reference("refs/remotes/origin/HEAD", f"refs/remotes/origin/{self.repo.head.shorthand}")
        # Read repository
        else:
            self.repo = Repository(str(self.repository_path))

    def check_updates(self):
        """
        Initialize repository and check for new available versions.
        """
        self.initialize_repo()

        print(f"{self.name} fetching...")
        for remote in self.repo.remotes:
            remote.fetch(prune=GIT_FETCH_PRUNE, callbacks=self.Callbacks())
            remote.fetch(prune=GIT_FETCH_PRUNE, callbacks=self.Callbacks(), refspecs=["refs/tags/*:refs/tags/*"])


class TagUpdater(RepoUpdater, ProcessedVersions):
    """
    Handle updating version from the repository tags.
    """
    def __init__(self, minimum_version: str, stable_version: bool = False, **kwargs):
        """
        Handle updating version from the repository tags.

        :param minimum_version: Minimum supported version.
        """

        self.minimum_version = Version(minimum_version)
        """Minimum supported version"""

        self.stable_version = stable_version
        """Should only stable version be processed"""

        super().__init__(**kwargs)

    @classmethod
    def normalize_tag(cls, tag: str) -> str:
        """
        Normalize version from tag.

        It can for example remove "v" at the beginning of the name.
        """
        return tag

    def check_updates(self):
        """
        Check for new available versions from tags.
        """
        super().check_updates()

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

            # Process only stable versions
            if self.stable_version and not version.is_stable:
                continue

            # Only not already processed versions:
            if version in self.processed_versions:
                continue

            versions.append(version)

        # Sort versions
        self.versions = sorted(versions)


class BaseBuilder(Documentation, ProcessedVersions):
    """
    Handle building documentation.
    """
    def __init__(self, doc_name: str, build_folder: str = "build", **kwargs):
        """
        Handle building documentation.

        :param doc_name: Name of the generated documentation file.
        :param build_folder: Name of the build folder.
        """
        self.build_folder = build_folder
        """Name of the build folder"""

        self.doc_name = doc_name
        """Name of the generated documentation file"""

        super().__init__(**kwargs)

    @classmethod
    def command(cls, version: Version) -> str:
        """
        Prepares command which will be used to generate documentation.

        :param version: Version to generate.
        :return: Command which will be used to generate documentation.
        """
        return f"./build.sh {version.name}"

    def build_version(self, version: Version) -> Optional[Path]:
        """
        Generate documentation for selected version.

        :param version: Version to generate.
        :return: Path to generated documentation.
        """
        print(f"{self.name} {version.name} processing...")
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
            print(f"{self.name} {version.name} success {time_elapsed:0.3f}s...")
            self.processed_versions.append(version)
            self.save_processed_versions()

            build_path = self.path. \
                joinpath(self.build_folder). \
                joinpath(version.name). \
                joinpath(self.doc_name)
            return build_path
        # Error
        else:
            print(f"{self.name} {version.name} failed...")
            print("stdout:")
            print(process.stdout)
            print("stderr:")
            print(process.stderr)
        return None


class TagDocumentation(TagUpdater, BaseBuilder):
    """
    Base class for documentation updaters which are using tags to find new versions.
    """
    def __init__(self, **kwargs):
        """
        Initialize updater object with configuration.
        """

        super().__init__(**kwargs)
