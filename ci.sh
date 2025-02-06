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

echo "docker build -t ${REPO}:${TAG} -f Dockerfile ."
docker build -t ${REPO}:${TAG} .
docker build -t ${REPO}:latest .
docker login --username $DOCKER_USER --password $DOCKER_PASSWORD docker.io
echo "docker push ${REPO}:${TAG}"
docker push ${REPO}:${TAG}
docker push ${REPO}:latest
#docker-compose up -d