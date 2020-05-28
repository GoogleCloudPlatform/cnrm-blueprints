#### Set global environment variables
```jupyter
%env GCS_TRUSTED_MIRROR=gs://anthoscli-test-cloudbuild-mirror
```

#### Load current state
```python
import os
import sys
sys.path.insert(0, os.path.abspath('../lib'))

from state import *
from e2e import *
from downloads import *
from anthoscli import *
from gcloud import *
from kpt import *
from kubectl import *

state = load_state()
state
```

#### Install gcloud


```python
if not "gcloud_version" in state:
    update_state(state, { "gcloud_version": "281.0.0" }) # TODO: how to query latest version?
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
if not "anthoscli_version" in state:
    update_state(state, { "anthoscli_version": "0.0.13" }) # TODO: how to query latest version?
anthoscli = download_anthoscli(state["anthoscli_version"], gcloud=gcloud)
kubectl.add_to_path(anthoscli.env)
gcloud.add_to_path(anthoscli.env)
anthoscli.env["PATH"]
```


```python
v = anthoscli.version()
update_state(state, { "anthoscli_reported_version": v} )
v
```

#### Install kpt


```python
workdir = workspace_dir()
statedir = os.path.join(workdir, "my-anthos")
os.makedirs(statedir, exist_ok=True)
kpt = download_kpt("0.4.0", gcloud=gcloud, statedir=statedir) # TODO: How to get tagged version?
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
```


```python
if not "zone" in state:
    update_state(state, { "zone": "us-central1-f" })
```


```python
save_state(state)
state
```

#### Get the asm kpt package


```python
# TODO: Get latest package?
asm_package = "https://github.com/GoogleCloudPlatform/anthos-service-mesh-packages.git/asm@v1.4.2"
kpt.get(asm_package, "cluster1/")
```


```python
kpt.set("cluster1/", "gcloud.compute.zone", state["zone"])
```

#### Apply it using anthoscli


```python
anthoscli.apply(statedir)
```

#### Perform some basic sanity checks 


```python
cluster = gcloud.describe_gke_cluster(state["zone"], "asm-cluster")
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
gcloud.delete_gke_cluster(state["zone"], "asm-cluster")
```
