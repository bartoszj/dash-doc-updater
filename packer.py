from doc import TagDocumentation


class Packer(TagDocumentation):
    """
    Packer updater.
    """
    processed_versions_file = "packer.yml"
    doc_name = "Packer.tgz"

    @classmethod
    def normalize_tag(cls, tag: str) -> str:
        version_prefix = "v"
        if tag.startswith(version_prefix):
            tag = tag[len(version_prefix):]
        return tag
