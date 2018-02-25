from doc import TagDocumentation, Version


class Kubernetes(TagDocumentation):
    """
    Kubernetes updater.
    """
    processed_versions_file = "kubernetes.yml"
    doc_name = "Kubernetes.tgz"

    @classmethod
    def normalize_tag(cls, tag: str) -> str:
        version_prefix = "v"
        if tag.startswith(version_prefix):
            tag = tag[len(version_prefix):]
        return tag

    @classmethod
    def command(cls, version: Version):
        return f"source env/bin/activate && ./build.sh {version.name}"
