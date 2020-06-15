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
import downloads
import json
import os
import e2e


def download_gcloud(version):
    now = datetime.datetime.utcnow()
    now = now.replace(microsecond=0)

    scratch_dir = os.path.join(
        e2e.workspace_dir(), "gcloud-scratch-" + now.strftime("%Y%m%d%H%M%s")
    )

    # We build up symlinks to the downloaded binaries in the bin directory
    bin_dir = os.path.join(scratch_dir, "bin")
    os.makedirs(bin_dir, exist_ok=True)

    url = (
        "https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-"
        + version
        + "-linux-x86_64.tar.gz"
    )
    tarfile = os.path.join(scratch_dir, "gcloud.tar.gz")
    downloads.download_url(url, tarfile)  # TODO: hashing?
    expanded = downloads.expand_tar(tarfile)

    gcloud_path = os.path.join(bin_dir, "gcloud")
    os.symlink(os.path.join(expanded, "google-cloud-sdk", "bin", "gcloud"), gcloud_path)

    gsutil_path = os.path.join(bin_dir, "gsutil")
    os.symlink(os.path.join(expanded, "google-cloud-sdk", "bin", "gsutil"), gsutil_path)

    return Gcloud(gcloud_path, gsutil=gsutil_path)


def local_gcloud():
    return Gcloud("gcloud", gsutil="gsutil")


class Gcloud(object):
    def __init__(self, bin, statedir=None, env=None, gsutil=None):
        if env is None:
            env = os.environ.copy()
        self.bin = os.path.expanduser(bin)
        self.env = env
        self.statedir = statedir
        self.gsutil = gsutil

    def __repr__(self):
        s = "Gcloud:" + self.bin
        return s

    # add_to_path ensures that kubectl is on the provider environ
    def add_to_path(self, env):
        d = os.path.dirname(self.bin)
        env["PATH"] = d + ":" + env["PATH"]

    def download_from_gcs(self, url, dest):
        mirror = os.environ.get("GCS_TRUSTED_MIRROR")
        if mirror:
            print("using GCS_TRUSTED_MIRROR %s" % (mirror))
            if not mirror.endswith("/"):
                mirror += "/"
            url = mirror + url.replace("gs://", "gs/")

        args = ["cp", url, dest]
        return downloads.exec([self.gsutil] + args, env=self.env).strip()

    def current_project(self):
        return self.exec(["config", "get-value", "project"])

    def set_current_project(self, project):
        return self.exec(["config", "set", "project", project])

    def describe_project(self, project):
        args = ["projects", "describe", project]
        return self.exec_and_parse_json(args)

    def describe_gke_cluster(self, location, name):
        args = ["container", "clusters", "describe", "--zone", location, name]
        return self.exec_and_parse_json(args)

    def delete_gke_cluster(self, location, name):
        args = ["container", "clusters", "delete", "--quiet", "--zone", location, name]
        return self.exec(args)

    def list_gke_clusters(self):
        args = ["container", "clusters", "list"]
        return self.exec_and_parse_json(args)

    def get_gke_cluster_creds(self, name, location, project):
        args = ["container", "clusters", "get-credentials", name, "--zone", location, "--project", project]
        return self.exec(args)

    def exec(self, args):
        return downloads.exec(
            [self.bin] + args, cwd=self.statedir, env=self.env
        ).strip()

    def exec_and_parse_json(self, args):
        j = downloads.exec(
            [self.bin, "--format", "json"] + args, cwd=self.statedir, env=self.env
        ).strip()
        return json.loads(j)

    def decrypt_key(self, args):
        return self.exec(args)
