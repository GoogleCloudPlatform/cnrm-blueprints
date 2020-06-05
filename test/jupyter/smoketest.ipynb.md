```python
state = {
    "project": "anthos-blueprints-validation",
    "project_number": "1074580744525",
    "anthoscli_version": "0.1.1",
}
```


```python
import os
import re
import sys
import tempfile
sys.path.insert(0, os.path.abspath('../lib'))

from state import *
from e2e import *
from downloads import *
from anthoscli import *
from gcloud import *
from git import *
from kpt import *
from kubectl import *

%env GCS_TRUSTED_MIRROR=gs://anthoscli-test-cloudbuild-mirror

repo = os.getenv("REPO_NAME")
branch = os.getenv("BRANCH_NAME")
tag = os.getenv("TAG_NAME")
commit_sha = os.getenv("COMMIT_SHA")
cluster_name = "anthos-blueprints-test-cluster"

if not repo:
  repo = "anthos-blueprints"

if not branch:
  branch = "master"

if not tag:
  tag = branch
```

#### Install gcloud


```python
if not "gcloud_version" in state:
    update_state(state, { "gcloud_version": "287.0.0" }) # TODO: how to query latest version?
gcloud = download_gcloud(state["gcloud_version"])
gcloud
```

#### Install kubectl


```python
if not "kubernetes_version" in state:
    update_state(state, { "kubernetes_version": get_kubernetes_version("stable") })
kubectl = download_kubectl(state["kubernetes_version"])
kubectl
kubectl.version()
```

#### Install anthoscli


```python
anthoscli = download_anthoscli(state["anthoscli_version"], gcloud=gcloud)
kubectl.add_to_path(anthoscli.env)
gcloud.add_to_path(anthoscli.env)
# Use strict mode so we catch the most we can
anthoscli.env["ANTHOSCLI_STRICT_MODE"] = "1"

v = anthoscli.version()
update_state(state, { "anthoscli_reported_version": v} )
v
```

#### Install kpt


```python
workdir = workspace_dir()
statedir = os.path.join(workdir, "my-anthos")
os.makedirs(statedir, exist_ok=True)

if not "kpt_version" in state:
    update_state(state, { "kpt_version": "0.24.0" }) # TODO: How to get latest?

kpt = download_kpt(state["kpt_version"], gcloud=gcloud, statedir=statedir) # TODO: How to get tagged version?
kpt
```

#### Configure project, zone etc.


```python
if not "project" in state:
    p = os.environ.get("PROJECT_ID")
    if not p:
        p = gcloud.current_project()
    update_state(state, { "project": p })
gcloud.set_current_project(state["project"])
state["project"]
```


```python
if not "zone" in state:
    update_state(state, { "zone": "us-central1-f" })
```


```python
save_state(state)
state
```

#### Get the submodule kpt package


```python
gcloud.decrypt_key(["kms", "decrypt", "--ciphertext-file=/root/.ssh/id_rsa.enc",
                    "--plaintext-file=/root/.ssh/id_rsa", "--location=global",
                    "--keyring=asm-cb-keyring", "--key=github-key"])

repo_url = "git@github.com:nan-yu/%s" % repo
git_user_email = "anthos-blueprints-validation-bot@google.com"
git_user_name = "anthos-blueprints-validation-bot"

git = Git(git_user_email, git_user_name)
git.clone(repo_url, "%s/%s" % (tempfile.gettempdir(), repo))

if not commit_sha:
  commit_sha = git.get_last_commit_hash()
commit_msg = git.get_commit_message(commit_sha)

m = re.compile("Update the submodule: *(.+)").match(commit_msg)
submodule = "anthos-service-mesh-packages/asm" if not m else m.group(1)
package = "%s.git/%s" % (repo_url, submodule)
kpt.get(package, "cluster1/")
```


```python
kpt.set("cluster1/", "cluster-name", cluster_name)
kpt.set("cluster1/", "gcloud.compute.zone", state["zone"])
kpt.set("cluster1/", "gcloud.core.project", state["project"])
kpt.set("cluster1/", "gcloud.project.projectNumber", state["project_number"])
kpt.list("cluster1/")
```

#### vet the manifest using anthoscli


```python
anthoscli.vet(statedir)
```

#### Apply it using anthoscli


```python
anthoscli.env["ANTHOSCLI_STRICT_MODE"] = ""
anthoscli.apply(statedir)
```

#### Perform some basic sanity checks 


```python
cluster = gcloud.describe_gke_cluster(state["zone"], cluster_name)
cluster
```


```python
status = cluster.get("status")
if status == "RUNNING":
    update_state(state, {"success": True})
else:
    update_state(state, {"success": False})
save_state(state)
```

#### Clean up!


```python
gcloud.delete_gke_cluster(state["zone"], cluster_name)

```

#### Pushing release tags for anthoscli


```python
if state["success"]:
  new_tag = git.commit_and_push(tag, branch, anthoscli-release-candidates.json)
  git.create_remote_tag(new_tag)
else:
  print("The cluster is not running")

```
