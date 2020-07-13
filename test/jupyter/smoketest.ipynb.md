```python
state = {
    "project": "anthos-blueprints-validation",
    "project_number": "1074580744525",
    "location": "us-central1-c",
    "anthoscli_version": "0.1.10",
    "kustomize_version": "3.6.1",
    "kpt_version": "0.24.0",
    "gcloud_version": "287.0.0"
}

import os
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
from kustomize import *
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
gcloud = download_gcloud(state["gcloud_version"])
gcloud
```

#### Setup blueprint submodule


```python
gcloud.decrypt_key(["kms", "decrypt", "--ciphertext-file=/root/.ssh/id_rsa.enc",
                    "--plaintext-file=/root/.ssh/id_rsa", "--location=global",
                    "--keyring=cnrm-blueprints-cb-keyring", "--key=github-key"])

repo_url = "git@github.com:GoogleCloudPlatform/%s" % repo
git_user_email = "anthos-blueprints-validation-bot@google.com"
git_user_name = "anthos-blueprints-validation-bot"
clone_directory = "%s/%s" % (tempfile.gettempdir(), repo)

git = Git(git_user_email, git_user_name)
git.clone(repo_url, clone_directory)

if not commit_sha:
  commit_sha = git.get_last_commit_hash()

updated_files = git.get_changed_files(commit_sha)

updated_packages = UpdatedPackages(clone_directory, updated_files)

if len(updated_packages.packages) == 0:
  print("No Blueprints are updated with commit %s" % commit_sha)
  update_state(state, {"new_rc": False})
  # test infrastructure update, only run one package for validation
  defaultBlueprint = ["asm-1.5"]
  updated_packages = UpdatedPackages(clone_directory, defaultBlueprint)
else:
  update_state(state, {"new_rc": True})

packages = updated_packages.packages
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

kpt = download_kpt(state["kpt_version"], gcloud=gcloud, statedir=statedir) # TODO: How to get tagged version?
gcloud.add_to_path(kpt.env)
kpt
```

#### Configure project, location etc.


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
save_state(state)
state
```

#### vet the manifest using anthoscli


```python
anthoscli.vet(statedir)
anthoscli.env["ANTHOSCLI_STRICT_MODE"] = ""

```

#### Install kustomize


```python
kustomize = download_kustomize(state["kustomize_version"])
kustomize.version()
```

#### Prepare the existing clusters for patch packages


```python
patch_packages = updated_packages.filter_patch_packages()
patch_cluster_names = {}
for p, pkg in patch_packages.items():
  cluster_name = "btc-%s" % randint(0, 100) #btc stands for blueprints-test-cluster
  existing_package_path = "%s.git/%s" % (repo_url, "test/gke-cluster")
  kpt.get(existing_package_path, cluster_name)
  patch_cluster_names[pkg.name] = cluster_name
  for setter in pkg.setters:
    if "gcloud.container.cluster" == setter or "cluster-name" in setter:
      kpt.set(cluster_name, setter, cluster_name)
  kpt.list(cluster_name)

anthoscli.apply(statedir)

```

#### Get the kpt packages


```python
clusters = []
for package_path, pkg in packages.items():
  package_full_path = "%s.git/%s" % (repo_url, package_path)
  if pkg.is_patch:
    cluster_name = patch_cluster_names[pkg.name]
    existing_output_dir = "%s/%s" % (statedir, cluster_name)
    gcloud.describe_project(state["project"])
    anthoscli.export(cluster_name, state["project"], state["location"], existing_output_dir)
    exec(["cat", "%s/all.yaml" % existing_output_dir])
    patch_path = "%s-%s" % (pkg.name, os.path.basename(package_path))
    patch_full_path = "%s/%s" % (statedir, patch_path)
    kpt.get(package_full_path, patch_path)
    kpt.set(patch_path, "base-dir", "../%s" % cluster_name)
    kpt.list(patch_path)
    for setter in pkg.setters:
        if "gcloud.container.cluster" == setter or "cluster-name" in setter:
          kpt.set(patch_path, setter, cluster_name)
    kustomize.create_with_namespace(state["project"], existing_output_dir)
    kustomize.build("%s/all.yaml" % existing_output_dir, patch_full_path)
    exec(["rm", "-rf", patch_full_path])
  else:
    cluster_name = "btc-%s" % randint(0, 100) #btc stands for blueprints-test-cluster
    kpt.get(package_full_path, cluster_name)
    for setter in pkg.setters:
      if "gcloud.container.cluster" == setter or "cluster-name" in setter:
        kpt.set(cluster_name, setter, cluster_name)
    kpt.list(cluster_name)
  clusters.append(cluster_name)
```

#### Apply it using anthoscli sequentially. It has to be sequential, otherwise anthoscli will complain about duplicate objects


```python
for cluster in clusters:
  anthoscli.apply("%s/%s" %(statedir, cluster))
```

#### Perform some basic sanity checks 


```python
has_failure = False

for cluster_name in clusters:
  cluster = gcloud.describe_gke_cluster(state["location"], cluster_name)
  cluster
  status = cluster.get("status")
  if status != "RUNNING":
    has_failure = True
  # Disable the check for deployments for now as the event-exporter deployment in kube-system namespace always crashes
  # else:
  #   gcloud.get_gke_cluster_creds(cluster_name, state["location"], state["project"])
  #   checks = kubectl.exec(["wait", "--for=condition=available", "--timeout=600s", "deployment", "--all", "--all-namespaces"])
  #   print(checks)
  #   if "error" in checks or "timed out" in checks:
  #     has_failure = True
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
  gcloud.delete_gke_cluster(state["location"], cluster_name)

```

#### Pushing release tags for anthoscli


```python
if state["success"]:
  if state["new_rc"]:
    git.checkout(branch)
    release_candidate.update_release_candidate()
    new_tag = release_candidate.get_current_release_candidate()
    git.commit_and_push(branch, CONFIG_FILE, "Update the anthoscli release version to " + new_tag)
    git.create_remote_tag(new_tag)
else:
  print("Errors occurred while running validation test")

```
