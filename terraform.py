from doc import RepoUpdater, BaseBuilder, ProcessedVersions, Version
import re
from pygit2 import DiffFile, DiffDelta


class Terraform(RepoUpdater, BaseBuilder, ProcessedVersions):
    """
    Terraform updater.
    """
    def __init__(self, path: str, repository_path: str, git_url: str):
        super().__init__(path=path, repository_path=repository_path, git_url=git_url,
                         processed_versions_file="terraform.yml", doc_name="Terraform.tgz")

    @property
    def name(self):
        return "Terraform"

    def check_updates(self):
        super().check_updates()

        config_file_path = "content/config.rb"
        regex = re.compile(r"h.version\s*=\s*\"(\S*)\"")

        # Commit
        head = self.repo.revparse_single("remotes/origin/HEAD")
        diff = head.tree.diff_to_tree()
        diff_file: DiffFile

        # Find config file path
        for dd in diff.deltas:  # type: DiffDelta
            df = dd.old_file
            if df.path == config_file_path:
                diff_file = df
                break

        # Read config.rb file
        blob = self.repo[diff_file.id]
        data = blob.data.decode("utf-8")
        version_str = regex.search(data).group(1)
        version = Version(version_str)

        # Only not already processed versions:
        if version in self.processed_versions:
            return

        self.versions = [version]

    @classmethod
    def command(cls, version: Version):
        return f"./build_current_from_0.10.sh {version.name}"
