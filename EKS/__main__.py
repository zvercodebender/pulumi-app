import pulumi
import pulumi_aws as aws
import pulumi_eks as eks
import pulumi_kubernetes as k8s
import json

# Load configuration from JSON file
with open("config.json", "r") as f:
    config_data = json.load(f)

# Extract values from config.json
aws_region = config_data["aws_region"]
eks_cluster_name = config_data["eks_cluster_name"]
node_count = config_data["node_count"]
message = config_data["message"]

# Ensure instance_types is a flat list
instance_types = config_data["instance_types"]

# Set AWS provider region (optional)
aws_provider = aws.Provider("aws-provider", region=aws_region)

# Create EKS Cluster 
eks_cluster = eks.Cluster(eks_cluster_name,
    instance_type=instance_types,  
    desired_capacity=node_count,
    min_size=1,
    max_size=3
)

# Create a Managed Node Group
node_group = eks.ManagedNodeGroup("eks-nodegroup",
    cluster=eks_cluster,
    node_group_name="eks-ng",
    node_role_arn=eks_cluster.instance_roles[0].arn,
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=node_count,
        min_size=1,
        max_size=3
    ),
    instance_types=[instance_types],
    opts=pulumi.ResourceOptions(parent=eks_cluster)
)

# Get Kubernetes provider
k8s_provider = k8s.Provider("k8s-provider", kubeconfig=eks_cluster.kubeconfig)

# Create a namespace
namespace = k8s.core.v1.Namespace("pulumi-app-ns",
    metadata={"name": "pulumi-app"},
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# Define Kubernetes deployment
app_labels = {"app": "pulumi-lab"}
deployment = k8s.apps.v1.Deployment("app-deployment",
    metadata={
        "name": "app-deployment",
        "namespace": namespace.metadata["name"]  # FIXED: Assign namespace
    },
    spec=k8s.apps.v1.DeploymentSpecArgs(
        replicas=1,
        selector=k8s.meta.v1.LabelSelectorArgs(match_labels=app_labels),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata={"labels": app_labels},
            spec=k8s.core.v1.PodSpecArgs(
                containers=[k8s.core.v1.ContainerArgs(
                    name="pulumi-lab",
                    image="rbroker/pulumi-lab",
                    env=[k8s.core.v1.EnvVarArgs(
                        name="MESSAGE",
                        value=message
                    )],
                    ports=[k8s.core.v1.ContainerPortArgs(container_port=8080)]
                )]
            )
        )
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace])
)

# Create LoadBalancer service
service = k8s.core.v1.Service("app-service",
    metadata={
        "name": "app-service",
        "namespace": namespace.metadata["name"],  
        "labels": app_labels
    },
    spec=k8s.core.v1.ServiceSpecArgs(
        selector=app_labels,  # Ensure it matches Deployment labels
        ports=[k8s.core.v1.ServicePortArgs(
            port=80,  
            target_port=8080,  
            protocol="TCP"
        )],
        type="LoadBalancer"
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[deployment])  # Ensure Service waits for Deployment
)


# Export outputs
pulumi.export("kubeconfig", eks_cluster.kubeconfig)
pulumi.export("eks_cluster_name", eks_cluster.eks_cluster.name)
pulumi.export("load_balancer_dns", service.status.load_balancer.ingress[0].hostname)

# Function to write kubeconfig to a file
def write_kubeconfig(kubeconfig):
    with open("../eks-config", "w") as f:
       f.write(json.dumps(kubeconfig, indent=4))

# Apply function to kubeconfig output
eks_cluster.kubeconfig.apply(lambda config: write_kubeconfig(config))