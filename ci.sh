export REPO="rbroker/pulumi-lab"
TAG="$(git rev-parse --short HEAD)"
#export VERSION="3.1.1"
if [ -z "${TAG}" ]
then
  echo "VERSION not set"
  TAG=latest
fi
echo "Version = ${TAG}"
IMAGE="${REPO}:${TAG}"

echo "docker build -t ${IMAGE} -f Dockerfile ."
docker build -t ${IMAGE}:${TAG} .
docker login --username $DOCKER_USER --password $DOCKER_PASSWORD docker.io
echo "docker push ${IMAGE}"
docker push ${IMAGE}
#docker-compose up -d