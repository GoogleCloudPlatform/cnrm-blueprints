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
NON_PACKAGE_FOLDERS = ["test"]


class UpdatedPackages:
    class KptPackage:
        def __init__(self, root_path, pkg_path):
            self.pkg_path = pkg_path
            self.name = pkg_path.split("/")[0]
            self.is_patch = True if "patch" in path.basename(
                pkg_path) else False
            self.setters = []
            kpt_path = path.join(root_path, pkg_path, KPT_FILE_NAME)
            with open(kpt_path) as file:
                config = yaml.safe_load(file)

            if config and config["openAPI"] and config["openAPI"][
                "definitions"]:
                for field in config["openAPI"]["definitions"].keys():
                    if field.startswith(SETTER_PREFIX) and \
                        config["openAPI"]["definitions"][field]["x-k8s-cli"] and \
                        config["openAPI"]["definitions"][field]["x-k8s-cli"][
                            "setter"] and \
                        config["openAPI"]["definitions"][field]["x-k8s-cli"][
                            "setter"][
                            "name"]:
                        self.setters.append(
                            config["openAPI"]["definitions"][field][
                                "x-k8s-cli"]["setter"][
                                "name"])

        def __repr__(self):
            return "\n\tname:%s\n\tpath: %s\n\tis_patch: %s\n\tsetters: %s\n" % (
                self.name, self.pkg_path, self.is_patch, self.setters)

    def __init__(self, root_path, updates):
        self.packages = {}
        self.root_path = root_path
        for update in updates:
            file = path.join(root_path, update)
            if path.isfile(file):
                self.add_kpt_package_from_path(update)
            elif path.isdir(file):
                self.add_kpt_package_from_dir(update)

    def __repr__(self):
        return self.packages

    def filter_out_patch_packages(self):
        return {k: v for (k, v) in self.packages.items() if not v.is_patch}

    def filter_patch_packages(self):
        return {k: v for (k, v) in self.packages.items() if v.is_patch}

    # The updated file is part of the subdirectory of the main repo
    # It might be part of a blueprint package
    def add_kpt_package_from_path(self, p):
        if not p or p in self.packages:
            return
        root = p.split("/")[0]
        if root in NON_PACKAGE_FOLDERS:
            return
        dir = path.dirname(p)
        kpt_path = path.join(self.root_path, dir, KPT_FILE_NAME)
        if path.exists(kpt_path):
            self.packages[p] = UpdatedPackages.KptPackage(self.root_path, p)
        else:
            self.add_kpt_package_from_path(dir)

    # The updated directory is a submodule of the main repo
    # The function adds the packages from the updated submodule
    def add_kpt_package_from_dir(self, dir):
        full_path = path.join(self.root_path, dir)
        if path.isfile(full_path) or dir in self.packages:
            return
        for subdir in os.listdir(full_path):
            sub_package = path.join(dir, subdir)
            kpt_path = path.join(self.root_path, sub_package, KPT_FILE_NAME)
            if path.exists(kpt_path):
                self.packages[sub_package] = UpdatedPackages.KptPackage(
                    self.root_path,
                    sub_package)
            else:
                self.add_kpt_package_from_dir(sub_package)
