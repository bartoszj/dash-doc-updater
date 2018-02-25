from typing import List, Tuple, Optional, TypeVar
from pkg_resources import parse_version, SetuptoolsVersion
from pathlib import Path


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


class Documentation(object):
    def __init__(self):
        self.versions: List[Version] = []

    def check_updates(self):
        """
        Check for new available versions.
        """
        pass

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
