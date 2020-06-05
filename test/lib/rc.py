# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import re

CONFIG_FILE = "anthoscli-release-candidates.json"
VERSION_PATTERN_REX = "(anthoscli-.+-rc)(\\d+)"

class ReleaseCandidate(object):
  def __init__(self, dir, repo, branch, tag):
    self.file = dir + "/" + CONFIG_FILE
    with open(self.file) as f:
      self.data = json.load(f)
      self.stage = self.get_launch_stage(repo, branch, tag)

  def __repr__(self):
    return self.data

  def get_launch_stage(self, repo, branch, tag):
    for s in self.data:
      for blueprint in s["blueprints"]:
        if repo != blueprint["name"]:
          continue
        if branch and branch in blueprint["branches"]:
          return s
        if tag and blueprint["tag-regex"] and re.match(blueprint["tag-regex"], tag):
          return s
    return None

  def get_anthos_cli_version(self):
    return None if not self.stage else str(self.stage["anthoscli-version"])

  def update_release_candidate(self):
    current = self.stage["release-candidate"]["next"]
    m = re.match(VERSION_PATTERN_REX, current)
    next = re.sub(VERSION_PATTERN_REX, m.group(1) + str(int(m.group(2)) + 1),
                  current)
    self.stage["release-candidate"]["current"] = current
    self.stage["release-candidate"]["next"] = next

    for index, s in enumerate(self.data):
      if s["stage"] == self.stage["stage"]:
        self.data[index]["release-candidate"]["current"] = current
        self.data[index]["release-candidate"]["next"] = next

    with open(self.file, "w") as f:
      json.dump(self.data, f, indent=2)

  def get_current_release_candidate(self):
    return str(self.stage["release-candidate"]["current"])
