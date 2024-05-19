#!/usr/bin/env python3

from collections.abc import Iterable
import configparser
import hashlib
import os
import plistlib
import re
import shutil
import tempfile
import typing
import uuid


class Connection(typing.TypedDict):
    destinationuid: str
    modifiers: int
    modifiersubtext: str
    vitoclose: bool


class UiData(typing.TypedDict):
    xpos: int
    ypos: int


class Metadata(typing.TypedDict):
    bundleid: str
    category: str
    connections: dict[str, list[Connection]]
    createdby: str
    description: str
    name: str
    objects: list[dict[str, typing.Any]]
    readme: str
    uidata: dict[str, UiData]
    version: str
    webaddress: str


class AlfredWorkflow:
    def __init__(self) -> None:
        self.metadata: Metadata = {
            "bundleid": "alexwlchan.github-shortcuts",
            "category": "Internet",
            "connections": {},
            "createdby": "@alexwlchan",
            "description": "Links to GitHub repos I use regularly",
            "name": "GitHub shortcuts",
            "objects": [],
            "readme": "",
            "uidata": {},
            "version": "1.0.0",
            "webaddress": "https://github.com/alexwlchan/github_alfred_shortcuts",
        }

    def add_link(self, url: str, title: str, icon: str, shortcut: str) -> None:
        trigger_object = {
            "config": {
                "argumenttype": 2,
                "keyword": shortcut,
                "subtext": "",
                "text": title,
                "withspace": False,
            },
            "type": "alfred.workflow.input.keyword",
            "uid": self.uuid("link", shortcut, url),
            "version": 1,
        }

        browser_object = {
            "config": {
                "browser": "",
                "spaces": "",
                "url": url,
                "utf8": True,
            },
            "type": "alfred.workflow.action.openurl",
            "uid": self.uuid("openurl", shortcut, url),
            "version": 1,
        }

        self._add_trigger_action_pair(
            trigger_object=trigger_object, action_object=browser_object, icon=icon
        )

    def uuid(self, *args: str) -> str:
        assert len(args) > 0
        md5 = hashlib.md5()
        for a in args:
            md5.update(a.encode("utf8"))

        # Quick check we don't have colliding UUIDs.
        if not hasattr(self, "_md5s"):
            self._md5s: dict[str, tuple[str, ...]] = {}
        hex_digest = md5.hexdigest()
        assert hex_digest not in self._md5s, (args, self._md5s[hex_digest])
        self._md5s[hex_digest] = args

        return str(uuid.UUID(hex=hex_digest)).upper()

    def _add_trigger_action_pair(
        self, trigger_object: typing.Any, action_object: typing.Any, icon: str
    ) -> None:
        self.metadata["objects"].append(trigger_object)
        self.metadata["objects"].append(action_object)

        if not hasattr(self, "idx"):
            self.idx = 0

        self.metadata["uidata"][trigger_object["uid"]] = {
            "xpos": 150,
            "ypos": 50 + 120 * self.idx,
        }
        self.metadata["uidata"][action_object["uid"]] = {
            "xpos": 600,
            "ypos": 50 + 120 * self.idx,
        }
        self.idx += 1

        self.metadata["connections"][trigger_object["uid"]] = [
            {
                "destinationuid": action_object["uid"],
                "modifiers": 0,
                "modifiersubtext": "",
                "vitoclose": False,
            },
        ]

    def assemble_package(self, name: str) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            shutil.copyfile("github.png", os.path.join(tmp_dir, "Icon.png"))

            plist_path = os.path.join(tmp_dir, "Info.plist")
            plistlib.dump(self.metadata, open(plist_path, "wb"))

            shutil.make_archive(
                base_name=f"{name}.alfredworkflow", format="zip", root_dir=tmp_dir
            )
            shutil.move(f"{name}.alfredworkflow.zip", f"{name}.alfredworkflow")


class Repo(typing.TypedDict):
    owner: str
    name: str
    shortcut: str


def get_repos(ini_path: str) -> Iterable[Repo]:
    config = configparser.ConfigParser()
    config.read(ini_path)

    for owner, repo_list in config["repos"].items():
        for line in repo_list.strip().splitlines():
            # Skip empty lines
            if not line.strip():
                continue

            # to match lines like
            #
            #     catalogue-api
            #     wellcomecollection.org (dotorg)
            #
            m = re.match(r"^(?P<name>[a-z._-]+)(?: \((?P<shortcut>[a-z_-]+)\))?$", line)

            if m is None:
                print(f"Unable to parse line: {line!r}")
                continue

            yield {
                "owner": owner,
                "name": m.group("name"),
                "shortcut": m.group("shortcut") or m.group("name"),
            }


if __name__ == "__main__":
    workflow = AlfredWorkflow()

    for repo in get_repos("repos.ini"):
        workflow.add_link(
            url=f"https://github.com/{repo['owner']}/{repo['name']}",
            title=f"{repo['owner']}/{repo['name']}",
            icon="github.png",
            shortcut=repo["shortcut"],
        )

    workflow.assemble_package(name="github_shortcuts")
