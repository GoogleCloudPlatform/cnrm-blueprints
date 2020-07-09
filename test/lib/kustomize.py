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

import datetime
import os

import downloads
import e2e


def download_kustomize(version):
    now = datetime.datetime.utcnow()
    now = now.replace(microsecond=0)

    scratch_dir = os.path.join(
        e2e.workspace_dir(), "kustomize-scratch-" + now.strftime("%Y%m%d%H%M%s")
    )

    # We build up symlinks to the downloaded binaries in the bin directory
    bin_dir = os.path.join(scratch_dir, "bin")
    os.makedirs(bin_dir, exist_ok=True)

    url = "https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize/v{version}/kustomize_v{version}_linux_amd64.tar.gz".format(version=version)

    downloads.exec(["curl", "-LJO", url], cwd=scratch_dir)
    tarfile = os.path.join(scratch_dir, "kustomize_v{version}_linux_amd64.tar.gz".format(version=version))
    expanded = downloads.expand_tar(tarfile)

    kustomize_path = os.path.join(bin_dir, "kustomize")
    os.symlink(os.path.join(expanded, "kustomize"), kustomize_path)
    downloads.exec(["chmod", "+x", kustomize_path])
    return Kustomize(kustomize_path)

def local_kustomize():
    return Kustomize("kustomize")


class Kustomize(object):
    def __init__(self, bin, env=None):
        if env is None:
            env = os.environ.copy()
        self.bin = os.path.expanduser(bin)
        self.env = env

    def __repr__(self):
        s = "Kustomize:" + self.bin
        return s

    # add_to_path ensures that kustomize is on the provider environ
    def add_to_path(self, env):
        d = os.path.dirname(self.bin)
        env["PATH"] = d + ":" + env["PATH"]

    def create_with_namespace(self, namespace, dir):
        stdout = self.exec(["create", "--autodetect", "--namespace", namespace], dir)
        return stdout

    def build(self, output, dir):
        stdout = self.exec(["build", "-o", output], dir)
        return stdout

    def version(self):
        stdout = self.exec(["version"])
        return stdout

    def exec(self, args, dir=None):
        return downloads.exec(
            [self.bin] + args, cwd=dir, env=self.env
        ).strip()
