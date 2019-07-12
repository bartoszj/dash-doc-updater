from doc import TagDocumentation


class Packer(TagDocumentation):
    """
    Packer updater.
    """
    def __init__(self, path: str, repository_path: str, git_url: str, minimum_version: str):
        super().__init__(path=path, repository_path=repository_path, git_url=git_url, minimum_version=minimum_version,
                         stable_version=True, processed_versions_file="packer.yml", doc_name="Packer.tgz")

    @property
    def name(self):
        return "Packer"

    @classmethod
    def normalize_tag(cls, tag: str) -> str:
        version_prefix = "v"
        if tag.startswith(version_prefix):
            tag = tag[len(version_prefix):]
        return tag
