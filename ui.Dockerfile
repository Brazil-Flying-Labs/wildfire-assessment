FROM node:18-alpine AS build

# set working directory
WORKDIR /ui

# install app dependencies
COPY ui/package.json ./
COPY ui/package-lock.json ./


RUN apk update && apk add --no-cache curl
RUN npm install

# build app
CMD ["npm", "start"]