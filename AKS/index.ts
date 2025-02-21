import * as pulumi from "@pulumi/pulumi";
import * as azure from "@pulumi/azure-native";
import * as k8s from "@pulumi/kubernetes";
import * as k8sHelm from "@pulumi/kubernetes/helm/v3";
import * as fs from "fs";

// Read configuration from JSON file
const configData = JSON.parse(fs.readFileSync("config.json", "utf-8"));

// Resource group
const resourceGroup = new azure.resources.ResourceGroup("resourceGroup", {
    resourceGroupName: configData.resourceGroup,
    location: configData.location,
});

// Virtual Network & Subnet
const vnet = new azure.network.VirtualNetwork("vnet", {
    resourceGroupName: resourceGroup.name,
    location: resourceGroup.location,
    addressSpace: { addressPrefixes: ["10.0.0.0/16"] },
});

const subnet = new azure.network.Subnet("subnet", {
    resourceGroupName: resourceGroup.name,
    virtualNetworkName: vnet.name,
    addressPrefix: "10.0.1.0/24",
});

// AKS Cluster
const aksCluster = new azure.containerservice.ManagedCluster("aksCluster", {
    resourceGroupName: resourceGroup.name,
    location: resourceGroup.location,
    dnsPrefix: configData.dnsPrefix,
    agentPoolProfiles: [{
        name: "agentpool",
        count: configData.nodeCount,
        vmSize: configData.nodeSize,
        mode: "System",
        vnetSubnetID: subnet.id,
    }],
    identity: { type: "SystemAssigned" },
    enableRBAC: true,
    networkProfile: {
        networkPlugin: "azure",
        serviceCidr: "10.0.2.0/24",
        dnsServiceIP: "10.0.2.10",
   }    
});


// Get kubeconfig
const kubeconfig = pulumi.all([aksCluster.name, resourceGroup.name]).apply(([clusterName, rgName]) =>
    azure.containerservice.listManagedClusterUserCredentials({ resourceGroupName: rgName, resourceName: clusterName })
        .then(creds => Buffer.from(creds.kubeconfigs[0].value, "base64").toString())
);
// Kubernetes Provider
const k8sProvider = new k8s.Provider("k8sProvider", { kubeconfig });

// Install Traefik via Helm
const traefik = new k8sHelm.Chart("traefik", {
    chart: "traefik",
    version: "21.0.0",
    fetchOpts: { repo: "https://traefik.github.io/charts" },
    namespace: "kube-system",
    values: {
        service: { type: "LoadBalancer" },
    },
}, { provider: k8sProvider });

// Get the Traefik Service
const traefikService = traefik.getResource("v1/Service", "kube-system/traefik");

// Extract the External IP dynamically
const traefikExternalIp = traefikService.status.apply(status => 
    status?.loadBalancer?.ingress?.[0]?.ip || "Pending"
);
// Create public host name
const ingressHost = traefikExternalIp.apply(ip => `pulumi-lab.${ip}.nip.io`);

// Deploy Application
const appLabels = { app: "rbroker-app" };

const deployment = new k8s.apps.v1.Deployment("appDeployment", {
    metadata: { name: "rbroker-app" },
    spec: {
        replicas: 2,
        selector: { matchLabels: appLabels },
        template: {
            metadata: { labels: appLabels },
            spec: {
                containers: [{
                    name: "rbroker-app",
                    image: "rbroker/pulumi-lab",
                    ports: [{ containerPort: 8080 }], // Updated from 80 to 8080
                    env: [{ name: "MESSAGE", value: configData.message }],
                }],
            },
        },
    },
}, { provider: k8sProvider });

// Service for the app
const appService = new k8s.core.v1.Service("appService", {
    metadata: { name: "rbroker-app-service" },
    spec: {
        selector: appLabels,
        ports: [{ port: 8080, targetPort: 8080 }], // Updated from 80 to 8080
    },
}, { provider: k8sProvider });

// Ingress Route for the application
const ingress = new k8s.networking.v1.Ingress("appIngress", {
    metadata: {
        name: "app-ingress",
        annotations: { "traefik.ingress.kubernetes.io/router.entrypoints": "web" },
    },
    spec: {
        rules: [{
            host: ingressHost, 
            http: {
                paths: [{
                    path: "/",
                    pathType: "Prefix",
                    backend: {
                        service: {
                            name: appService.metadata.name,
                            port: { number: 8080 }, // Updated from 80 to 8080
                        },
                    },
                }],
            },
        }],
    },
}, { provider: k8sProvider });

// Export Outputs
export const aksName = aksCluster.name;
export const kubeConfig = kubeconfig;
export const ingressUrl = pulumi.interpolate`http://${ingressHost}/`;
