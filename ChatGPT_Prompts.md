# Rancher Kubernetes

`
Using Pulumi python, create and deploy a web application (pulumi-app) using the docker image `rbroker/pulumi-lab` running in a Rancher Kubernetes instance. The container exposes port 8080 so there should be a kubernetes service that exposes that port to the trafik ingress controller which uses the url http://pulumi.lab.192.168.17.11.nip.io.  The web application should display a customized web page that returns a configurable value in its web page response.
`
