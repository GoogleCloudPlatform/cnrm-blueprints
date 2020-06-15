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

import os
import os.path
from os import path
import yaml

KPT_FILE_NAME = "Kptfile"
SETTER_PREFIX = "io.k8s.cli.setters"

class Blueprint:

  class Package:
    def __init__(self, submodule, kpt_path):
      self.package_path = submodule
      self.is_patch = True if "patch" in path.basename(submodule) else False
      self.setters = []
      with open(kpt_path) as file:
        config = yaml.safe_load(file)

      if config and config["openAPI"] and config["openAPI"]["definitions"]:
        for field in config["openAPI"]["definitions"].keys():
          if field.startswith(SETTER_PREFIX) and \
              config["openAPI"]["definitions"][field]["x-k8s-cli"] and \
              config["openAPI"]["definitions"][field]["x-k8s-cli"]["setter"] and \
              config["openAPI"]["definitions"][field]["x-k8s-cli"]["setter"]["name"]:
            self.setters.append(config["openAPI"]["definitions"][field]["x-k8s-cli"]["setter"]["name"])

    def __repr__(self):
      return "\n\tpackage_path: %s\n\tis_patch: %s\n\tsetters: %s\n" % (self.package_path, self.is_patch, self.setters)

  def __init__(self, root_path, submodule):
    self.packages = {}
    root_kpt_path = path.join(root_path, submodule, KPT_FILE_NAME)
    if path.exists(root_kpt_path):
      self.packages[submodule] = Blueprint.Package(submodule, root_kpt_path)
    else:
      root_path = path.join(root_path, submodule)
      for subdir in os.listdir(root_path):
        sub_package = path.join(submodule, subdir)
        kpt_path = path.join(root_path, subdir, KPT_FILE_NAME)
        if path.isdir(path.join(root_path, subdir)) and path.exists(kpt_path):
          self.packages[sub_package] = Blueprint.Package(sub_package, kpt_path)

  def __repr__(self):
    return self.packages

  def filter_out_patch_packages(self):
    return {k:v for (k, v) in self.packages.items() if not v.is_patch }
