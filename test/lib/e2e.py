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
import tempfile

_artifacts_dir = None


def artifacts_dir():
    global _artifacts_dir
    if _artifacts_dir is None:
        wd = workspace_dir()
        _artifacts_dir = os.path.join(wd, "artifacts")
        os.makedirs(_artifacts_dir, exist_ok=True)
    return _artifacts_dir


_workspace_dir = None


def workspace_dir():
    global _workspace_dir
    if _workspace_dir is None:
        _workspace_dir = os.environ.get("WORKSPACE") or tempfile.mkdtemp(prefix="tmp-e2e")
    return _workspace_dir
