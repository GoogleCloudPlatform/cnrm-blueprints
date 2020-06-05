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
import json

import e2e


def save_state(state):
    p = os.path.join(e2e.artifacts_dir(), "state.json")
    with open(p, "w") as f:
        json.dump(state, f, sort_keys=True, indent=4, separators=(",", ": "))


def load_state():
    p = os.path.join(e2e.artifacts_dir(), "state.json")
    state = {}
    if os.path.exists(p):
        with open(p) as f:
            state = json.load(f)
    return state


def update_state(state, add):
    m = merge_dicts(state, add)
    for k, v in m.items():
        state[k] = v


def merge_dicts(l, r):
    m = {**l, **r}
    for k, v in m.items():
        if k in l and k in r:
            if isinstance(r[k], dict):
                m[k] = merge_dicts(l[k], r[k])
    return m
