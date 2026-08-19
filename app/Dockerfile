FROM node:22-alpine AS build

WORKDIR /app

# There is currently no lockfile in the project, so install from package.json.
COPY package.json ./
RUN npm install --no-audit --no-fund

COPY . .
RUN npm run build

FROM node:22-alpine

WORKDIR /app

# There is currently no lockfile in the project, so install from package.json.
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

COPY server.js ./
COPY --from=build /app/dist ./dist

EXPOSE 3000

CMD ["node", "server.js"]
