FROM node:18-alpine

# set working directory
WORKDIR /ui

RUN apk update && apk add --no-cache curl && rm -rf /var/cache/apk/*

# Dependencies are installed at startup since ./ui is volume-mounted,
# overwriting anything COPYed at build time. This keeps the image small
# and build fast while ensuring node_modules always matches package-lock.json.
CMD ["sh", "-c", "npm install && npm start"]
