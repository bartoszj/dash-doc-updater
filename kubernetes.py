from doc import TagDocumentation, Version


class Kubernetes(TagDocumentation):
    """
    Kubernetes updater.
    """
    def __init__(self, path: str, repository_path: str, git_url: str, minimum_version: str):
        super().__init__(path=path, repository_path=repository_path, git_url=git_url, minimum_version=minimum_version,
                         stable_version=True, processed_versions_file="kubernetes.yml", doc_name="Kubernetes.tgz")

    @property
    def name(self):
        return "Kubernetes"

    @classmethod
    def normalize_tag(cls, tag: str) -> str:
        version_prefix = "v"
        if tag.startswith(version_prefix):
            tag = tag[len(version_prefix):]
        return tag

    @classmethod
    def command(cls, version: Version):
        return f"source env/bin/activate && ./build.sh {version.name}"
