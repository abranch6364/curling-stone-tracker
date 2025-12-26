ARG NODE_VERSION=24.7.0-alpine

FROM node:${NODE_VERSION}

WORKDIR /app

COPY package.json package-lock.json ./

RUN --mount=type=cache,target=/root/.npm npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]