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
import requests
import subprocess
import pathlib


def exec(args, env=None, cwd=None, print_stdout=True):
    if env is None:
        env = os.environ.copy()
    print("running %s" % (args))
    r = subprocess.run(
        args, env=env, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if print_stdout:
        print(r.stdout.decode())
    print(r.stderr.decode())
    if r.returncode != 0:
        r.check_returncode()
    return r.stdout.decode()


def read_url(u):
    r = requests.get(u)
    if r.status_code != 200:
        raise Exception("unexpected response code %d fetching %s" % (r.status_code, u))
    return r.text


archive = os.path.join(pathlib.Path.home(), ".cache", "kops-test", "assets")


def sha256_of_file(f):
    stdout = exec(["sha256sum", f])
    return stdout.split()[0]


def download_hashed_url(url):
    hash = read_url(url + ".sha256").strip()
    os.makedirs(archive, exist_ok=True)
    dest = os.path.join(archive, hash)
    if os.path.exists(dest):
        actual_hash = sha256_of_file(dest)
        if actual_hash != hash:
            print(
                "hash mismatch on %s (%s vs %s), will download again"
                % (dest, actual_hash, hash)
            )
        else:
            return dest
    download_url(url, dest)
    return dest


def download_url(url, dest):
    exec(["curl", url, "-o", dest])


def expand_tar(tarfile):
    hash = sha256_of_file(tarfile)
    dest = os.path.join(archive, "expanded", hash)
    if os.path.exists(dest):
        return dest

    tmpdest = dest + ".tmp"
    os.makedirs(tmpdest)
    exec(["tar", "xf", tarfile, "-C", tmpdest])
    exec(["mv", tmpdest, dest])

    return dest
