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


def download_kpt(version, gcloud=None, statedir=None):
    now = datetime.datetime.utcnow()
    now = now.replace(microsecond=0)

    scratch_dir = os.path.join(
        e2e.workspace_dir(), "kpt-scratch-" + now.strftime("%Y%m%d%H%M%s")
    )

    # We build up symlinks to the downloaded binaries in the bin directory
    bin_dir = os.path.join(scratch_dir, "bin")
    os.makedirs(bin_dir, exist_ok=True)

    url = "gs://kpt-dev/releases/v{version}/linux_amd64/kpt_linux_amd64-v{version}.tar.gz".format(version=version)

    tarfile = os.path.join(scratch_dir, "kpt.tar.gz")
    gcloud.download_from_gcs(url, tarfile)
    expanded = downloads.expand_tar(tarfile)
    kpt_path = os.path.join(bin_dir, "kpt")
    os.symlink(os.path.join(expanded, "kpt"), kpt_path)
    downloads.exec(["chmod", "+x", kpt_path])

    return Kpt(kpt_path, statedir=statedir)


def local_kpt(statedir=None):
    return Kpt("kpt", statedir=statedir)


class Kpt(object):
    def __init__(self, bin, statedir=None, env=None):
        if env is None:
            env = os.environ.copy()
        self.bin = os.path.expanduser(bin)
        self.env = env
        self.statedir = statedir

    def __repr__(self):
        s = "Kpt:" + self.bin
        if self.statedir:
            s = s + " statedir=" + self.statedir
        return s

    # add_to_path ensures that kubectl is on the provider environ
    def add_to_path(self, env):
        d = os.path.dirname(self.bin)
        env["PATH"] = d + ":" + env["PATH"]

    def get(self, src, dest):
        stdout = self.exec(["pkg", "get", src, dest])
        return stdout

    def set(self, path, k, v):
        stdout = self.exec(["cfg", "set", path, k, v])
        return stdout

    def list(self, path):
        stdout = self.exec(["cfg", "list-setters", path])
        return stdout

    def exec(self, args):
        return downloads.exec(
            [self.bin] + args, cwd=self.statedir, env=self.env
        ).strip()
