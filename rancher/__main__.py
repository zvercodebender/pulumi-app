import pulumi
import pulumi_kubernetes as k8s

# Namespace (optional, modify as needed)
namespace = k8s.core.v1.Namespace("pulumi-app-ns",
    metadata={"name": "pulumi-app"})

# Deployment
app_labels = {"app": "pulumi-app"}
deployment = k8s.apps.v1.Deployment("pulumi-app-deployment",
    metadata={"namespace": namespace.metadata["name"]},
    spec={
        "selector": {"matchLabels": app_labels},
        "replicas": 2,
        "template": {
            "metadata": {"labels": app_labels},
            "spec": {
                "containers": [{
                    "name": "pulumi-app",
                    "image": "rbroker/pulumi-lab",
                    "ports": [{"containerPort": 8080}],
                    "env": [{"name": "MESSAGE", "value": "from Rick!"}]
                }]
            }
        }
    })

# Service
service = k8s.core.v1.Service("pulumi-app-service",
    metadata={"namespace": namespace.metadata["name"]},
    spec={
        "selector": app_labels,
        "ports": [{"port": 8080, "targetPort": 8080}],
    })

# Ingress
ingress = k8s.networking.v1.Ingress("pulumi-app-ingress",
    metadata={
        "namespace": namespace.metadata["name"],
        "annotations": {
            "kubernetes.io/ingress.class": "traefik"
        }
    },
    spec={
        "rules": [{
            "host": "pulumi.lab.192.168.17.11.nip.io",
            "http": {
                "paths": [{
                    "path": "/",
                    "pathType": "Prefix",
                    "backend": {
                        "service": {
                            "name": service.metadata["name"],
                            "port": {"number": 8080}
                        }
                    }
                }]
            }
        }]
    })

pulumi.export("namespace", namespace.metadata["name"])
pulumi.export("service_name", service.metadata["name"])
pulumi.export("ingress_url", "http://pulumi.lab.192.168.17.11.nip.io")
