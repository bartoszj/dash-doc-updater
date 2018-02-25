#! /usr/bin/env python
import argparse
import yaml
from typing import List
from doc import Documentation
from kubernetes import Kubernetes

CONFIG_PATH = "config.yml"

parser = argparse.ArgumentParser(description="Check for updates in the tracked dash repositories")
args = parser.parse_args()


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.load(f)


if __name__ == '__main__':
    config = load_config()

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

    # Start processing
    for doc in docs:
        doc.update()
