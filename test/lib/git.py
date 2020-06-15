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

import downloads
import os

class Git(object):
    def __init__(self, user_email, user_name, env=None):
        if env is None:
            env = os.environ.copy()
        self.bin = "git"
        self.env = env
        downloads.exec(["chmod", "600", "/root/.ssh/id_rsa"])
        downloads.exec(["git", "config", "--global", "user.email", user_email])
        downloads.exec(["git", "config", "--global", "user.name", user_name])

    def __repr__(self):
        return "Git:" + downloads.exec(["which", "git"])

    def clone(self, repo, directory):
        downloads.exec(["git", "clone", "--recursive", repo, directory])
        self.statedir = directory

    def checkout(self, branch):
        self.exec(["checkout", branch])

    def commit_and_push(self, branch, file, msg):
        self.exec(["add", file])
        self.exec(["commit", "-m", msg])
        self.exec(["push", "origin", "HEAD:%s" % branch])

    def create_remote_tag(self, tag):
        self.exec(["tag", tag])
        self.exec(["push", "origin", tag])

    def get_commit_message(self, commit_hash):
        return self.exec(["show", "--pretty=format:%s", "-s", commit_hash])

    def get_last_commit_hash(self):
        return self.exec(["rev-parse", "HEAD"])

    def exec(self, args):
        return downloads.exec(
            [self.bin] + args, cwd=self.statedir, env=self.env
        ).strip()
