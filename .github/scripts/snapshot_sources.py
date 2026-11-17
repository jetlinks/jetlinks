"""Freeze the 1.3 reactor sources before publishing a coherent SNAPSHOT build."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

PARENT = "jetlinks/jetlinks"
BRANCH = "1.3"
MODULES = {
    "jetlinks-core": "jetlinks/jetlinks-core",
    "jetlinks-supports": "jetlinks/jetlinks-supports",
    "rule-engine": "jetlinks/rule-engine",
}
SHA = re.compile(r"[0-9a-f]{40}")


def api(path):
    token = os.environ.get("GH_TOKEN")
    if not token:
        return json.loads(subprocess.check_output(["gh", "api", path], text=True))
    request = urllib.request.Request(
        "https://api.github.com/" + path,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def resolve(source_repository="", source_sha="", source_ref=BRANCH, get=api):
    """Notifications wake the build; their SHA must never roll back a branch."""
    if source_ref != BRANCH:
        raise ValueError("Only the 1.3 release line can be published")
    allowed = {PARENT, *MODULES.values()}
    if source_repository and source_repository not in allowed:
        raise ValueError("Unknown source repository")
    if bool(source_repository) != bool(source_sha):
        raise ValueError("Source repository and SHA must be supplied together")
    if source_sha and not SHA.fullmatch(source_sha):
        raise ValueError("Invalid source commit SHA")
    # Resolve every repository before changing any checkout. Queued old events
    # therefore publish the newest available combination instead of old input.
    heads = {}
    for repository in sorted(allowed):
        sha = get(f"repos/{repository}/git/ref/heads/{BRANCH}")["object"]["sha"]
        if not SHA.fullmatch(sha):
            raise ValueError("Invalid branch head from GitHub")
        heads[repository] = sha
    if source_repository:
        comparison = get(f"repos/{source_repository}/compare/{source_sha}...{heads[source_repository]}")
        if comparison["status"] not in {"identical", "ahead"}:
            raise ValueError("Source commit is not contained in the selected release branch")
    return {"branch": BRANCH, "parent": {"repository": PARENT, "sha": heads[PARENT]},
            "modules": [{"path": path, "repository": repository, "sha": heads[repository]}
                        for path, repository in MODULES.items()],
            "trigger": {"repository": source_repository, "sha": source_sha, "ref": source_ref},
            "run": {"repository": os.environ.get("GITHUB_REPOSITORY", PARENT),
                    "id": os.environ.get("GITHUB_RUN_ID", "local")}}


def git(root, *args):
    # All source repositories are public; do not require SSH keys on the runner.
    return subprocess.check_output(
        ["git", "-c", "url.https://github.com/.insteadOf=git@github.com:",
         "-C", str(root), *args], text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    ).strip()


def reactor(root):
    """Read declared reactor modules rather than unrelated example POM files."""
    root = Path(root).resolve()
    models = []
    seen = set()

    def visit(folder):
        folder = folder.resolve()
        if not folder.is_relative_to(root) or folder in seen:
            raise ValueError("Invalid reactor module path")
        seen.add(folder)
        model = ET.parse(folder / "pom.xml").getroot()
        models.append((folder, model))
        for module in model.findall("{*}modules/{*}module"):
            visit(folder / module.text)

    visit(root)
    version = models[0][1].findtext("{*}version")
    if not version or not re.fullmatch(r"1\.3\.\d+-SNAPSHOT", version):
        raise ValueError("Parent version must belong to the 1.3 SNAPSHOT release line")
    artifacts = {model.findtext("{*}artifactId") for _, model in models}
    if None in artifacts or len(artifacts) != len(models):
        raise ValueError("Reactor artifact IDs must be present and unique")
    for folder, model in models:
        own = model.findtext("{*}version")
        if own and own != version:
            raise ValueError(f"Module version differs from parent: {folder}")
        parent = model.findtext("{*}parent/{*}artifactId")
        if parent in artifacts and model.findtext("{*}parent/{*}version") != version:
            raise ValueError(f"Module parent version differs from release line: {folder}")
    return {"version": version, "artifacts": sorted(artifacts)}


def prepare(root, manifest):
    root = Path(root).resolve()
    git(root, "fetch", "--no-tags", "origin", manifest["parent"]["sha"])
    git(root, "checkout", "--detach", manifest["parent"]["sha"])
    configured = git(root, "config", "--file", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$")
    if {line.split(None, 1)[1] for line in configured.splitlines()} != set(MODULES):
        raise ValueError("The release reactor submodule set has changed; update its source contract")
    for path, repository in MODULES.items():
        url = git(root, "config", "--file", ".gitmodules", "--get", f"submodule.{path}.url")
        branch = git(root, "config", "--file", ".gitmodules", "--get", f"submodule.{path}.branch")
        if url not in {"git@github.com:" + repository + ".git", "https://github.com/" + repository + ".git"} or branch != BRANCH:
            raise ValueError("The submodule repository or release branch differs from its source contract")
    git(root, "submodule", "update", "--init", "--recursive")
    for module in manifest["modules"]:
        path = root / module["path"]
        git(path, "remote", "set-url", "origin", "https://github.com/" + module["repository"] + ".git")
        git(path, "fetch", "--no-tags", "origin", module["sha"])
        git(path, "checkout", "--detach", module["sha"])
        git(path, "submodule", "update", "--init", "--recursive")
        if git(path, "rev-parse", "HEAD") != module["sha"]:
            raise ValueError("A submodule was not pinned to its resolved source SHA")
    manifest["reactor"] = reactor(root)
    manifest["recursiveSubmodules"] = git(root, "submodule", "status", "--recursive").splitlines()
    return manifest


def verify_publication(manifest, log):
    text = Path(log).read_text()
    expected = manifest["reactor"]
    uploaded = set(re.findall(r"Uploaded to snapshots: .*?/org/jetlinks/([^/]+)/([^/]+-SNAPSHOT)/", text))
    missing = set(expected["artifacts"]) - {artifact for artifact, version in uploaded if version == expected["version"]}
    if "BUILD SUCCESS" not in text or "BUILD FAILURE" in text or missing:
        raise ValueError("Publication did not confirm all reactor artifacts: " + ", ".join(sorted(missing)))
    manifest["publication"] = {"status": "success", "artifacts": sorted(uploaded),
                               "logSha256": hashlib.sha256(text.encode()).hexdigest()}
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "verify"])
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--log")
    args = parser.parse_args()
    path = Path(args.manifest)
    if args.mode == "prepare":
        manifest = resolve(os.environ.get("SOURCE_REPOSITORY", ""),
                           os.environ.get("SOURCE_SHA", ""), os.environ.get("SOURCE_REF", BRANCH))
        # Keep the resolved inputs even if checkout or version validation fails.
        path.write_text(json.dumps(manifest, indent=2) + "\n")
        manifest = prepare(Path.cwd(), manifest)
    else:
        manifest = verify_publication(json.loads(path.read_text()), args.log)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
