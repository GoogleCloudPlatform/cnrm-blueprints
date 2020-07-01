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

updated_files = git.get_changed_files(commit_sha)

# TODO: Do not filter out patch packages. Instead, add validation to the patch packages using anthoscli export and kustomize
packages = UpdatedPackages(clone_directory, updated_files).filter_out_patch_packages()

if len(packages) == 0:
  print("No Blueprints are updated with commit %s" % commit_sha)
  update_state(state, {"new_rc": False})
  # test infrastructure update, only run one package for validation
  defaultBlueprint = ["asm-1.5"]
  packages = UpdatedPackages(clone_directory, defaultBlueprint).filter_out_patch_packages()
else:
  update_state(state, {"new_rc": True})
print("The packages to be validated:")
print(packages)

anthoscli_versions = set()
for k, v in packages.items():
  release_candidate = ReleaseCandidate(clone_directory, v.name)
  anthoscli_versions.add(release_candidate.get_anthos_cli_version())

if len(anthoscli_versions) == 0:
  raise Exception("No Anthoscli versions found. Please check anthoscli-release-candidates.json file and make sure the blueprints are added.")
if len(anthoscli_versions) > 1:
  raise Exception("Multiple Anthoscli versions found for the updated packages!")
anthoscli_version = list(anthoscli_versions)[0]
print("anthoscli_version: %s" % anthoscli_version)

if not anthoscli_version:
  update_state(state, {"anthoscli_version": anthoscli_version})
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
gcloud.add_to_path(kpt.env)
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
clusters = []
for package_path in packages:
  cluster_name = "btc-%s" % randint(0, 100) #btc stands for blueprints-test-cluster
  package_full_path = "%s.git/%s" % (repo_url, package_path)
  kpt.get(package_full_path, cluster_name)
  for setter in packages[package_path].setters:
    if "gcloud.container.cluster" == setter or "cluster-name" in setter:
      kpt.set(cluster_name, setter, cluster_name)
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
  if state["new-rc"]:
    git.checkout(branch)
    release_candidate.update_release_candidate()
    new_tag = release_candidate.get_current_release_candidate()
    git.commit_and_push(branch, CONFIG_FILE, "Update the anthoscli release version to " + new_tag)
    git.create_remote_tag(new_tag)
else:
  print("Errors occurred while running validation test")

```
