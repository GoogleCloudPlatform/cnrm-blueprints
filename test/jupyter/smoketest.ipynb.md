```python
state = {
    "project": "anthos-blueprints-validation",
    "project_number": "1074580744525",
    "anthoscli_version": "0.1.10"
}

import os
import re
import sys
import tempfile
sys.path.insert(0, os.path.abspath('../lib'))

from blueprint import *
from state import *
from e2e import *
from downloads import *
from anthoscli import *
from gcloud import *
from git import *
from kpt import *
from kubectl import *
from random import randint
from rc import *

%env GCS_TRUSTED_MIRROR=gs://anthoscli-test-cloudbuild-mirror

repo = os.getenv("REPO_NAME")
branch = os.getenv("BRANCH_NAME")
commit_sha = os.getenv("COMMIT_SHA")

if not repo:
  repo = "blueprints"

if not branch:
  branch = "master"


```

#### Install gcloud


```python
if not "gcloud_version" in state:
    update_state(state, { "gcloud_version": "287.0.0" }) # TODO: how to query latest version?
gcloud = download_gcloud(state["gcloud_version"])
gcloud
```

#### Setup blueprint submodule


```python
gcloud.decrypt_key(["kms", "decrypt", "--ciphertext-file=/root/.ssh/id_rsa.enc",
                    "--plaintext-file=/root/.ssh/id_rsa", "--location=global",
                    "--keyring=blueprints-cb-keyring", "--key=github-key"])

repo_url = "git@github.com:GoogleCloudPlatform/%s" % repo
git_user_email = "anthos-blueprints-validation-bot@google.com"
git_user_name = "anthos-blueprints-validation-bot"
clone_directory = "%s/%s" % (tempfile.gettempdir(), repo)

git = Git(git_user_email, git_user_name)
git.clone(repo_url, clone_directory)

if not commit_sha:
  commit_sha = git.get_last_commit_hash()
commit_msg = git.get_commit_message(commit_sha)

m = re.compile("^Update submodule:\s*(.+)/(branches|tags)/(\S*).*$").match(commit_msg)

blueprint = "anthos-service-mesh-packages"  # Use ASM as the default validation package
blueprint_branch = "release-1.5-asm"   # Use ASM's latest release branch
blueprint_tag = ""
blueprint_mode = ""
blueprint_revision = blueprint_branch
if not m:
  blueprint = m.group(1)  # the blueprint name
  blueprint_mode = m.group(2) # branches or tags
  blueprint_revision = m.group(3) # either the branch name or the tag name
  blueprint_branch = blueprint_revision if blueprint_mode == "branches" else ""
  blueprint_tag = blueprint_revision if blueprint_mode == "tags" else ""

release_candidate = ReleaseCandidate(clone_directory, blueprint, blueprint_branch, blueprint_tag)
anthoscli_version = release_candidate.get_anthos_cli_version()
submodule = blueprint if m and blueprint_mode == "tags" else "%s-%s" % (blueprint, blueprint_revision)

if not anthoscli_version:
  update_state(stage, {"anthoscli_version": anthoscli_version})
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

#### Get the submodule's kpt packages


```python
# TODO: Validate the patch packages using anthoscli export and kustomize
packages = Blueprint(clone_directory, submodule).filter_out_patch_packages()
print(packages)
clusters = []
for package_path in packages:
  cluster_name = "btc-%s" % randint(0, 100) #btc stands for blueprints-test-cluster
  package_full_path = "%s.git/%s" % (repo_url, package_path)
  kpt.get(package_full_path, cluster_name)
  for setter in packages[package_path].setters:
    if "gcloud.container.cluster" == setter or "cluster-name" in setter:
      kpt.set(cluster_name, setter, cluster_name)
    elif "gcloud.compute.zone" == setter or "gcloud.compute.location" == setter:
      kpt.set(cluster_name, setter, state["zone"])
    elif "gcloud.core.project" == setter:
      kpt.set(cluster_name, setter, state["project"])
    elif "gcloud.project.projectNumber" == setter:
      kpt.set(cluster_name, setter, state["project_number"])
  kpt.list(cluster_name)
  clusters.append(cluster_name)
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
has_failure = False

for cluster_name in clusters:
  cluster = gcloud.describe_gke_cluster(state["zone"], cluster_name)
  cluster
  status = cluster.get("status")
  if status != "RUNNING":
    has_failure = True
  else:
    gcloud.get_gke_cluster_creds(cluster_name, state["zone"], state["project"])
    checks = kubectl.exec(["wait", "--for=condition=available", "--timeout=600s", "deployment", "--all", "--all-namespaces"])
    print(checks)
    if "error" in checks or "timed out" in checks:
      has_failure = True
```


```python
if has_failure:
    update_state(state, {"success": False})
else:
    update_state(state, {"success": True})
save_state(state)
```

#### Clean up!


```python
for cluster_name in clusters:
  gcloud.delete_gke_cluster(state["zone"], cluster_name)

```

#### Pushing release tags for anthoscli


```python
if state["success"]:
  git.checkout(branch)
  release_candidate.update_release_candidate()
  new_tag = release_candidate.get_current_release_candidate()
  git.commit_and_push(branch, CONFIG_FILE, "Update the anthoscli release version to " + new_tag)
  git.create_remote_tag(new_tag)
else:
  print("Errors occurred while running validation test")

```
