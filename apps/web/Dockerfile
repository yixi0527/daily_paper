FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_APP_MODE=live
ARG VITE_API_BASE_URL=http://localhost:8000/api
ARG VITE_STATIC_DATA_BASE=/data
ARG VITE_GITHUB_PAGES_BASE=/

ENV VITE_APP_MODE=${VITE_APP_MODE}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_STATIC_DATA_BASE=${VITE_STATIC_DATA_BASE}
ENV VITE_GITHUB_PAGES_BASE=${VITE_GITHUB_PAGES_BASE}

COPY package.json ./
COPY apps/web/package.json ./apps/web/package.json
COPY apps/web/tsconfig.json ./apps/web/tsconfig.json
COPY apps/web/tsconfig.app.json ./apps/web/tsconfig.app.json
COPY apps/web/vite.config.ts ./apps/web/vite.config.ts
COPY apps/web/eslint.config.js ./apps/web/eslint.config.js
COPY apps/web/index.html ./apps/web/index.html
COPY apps/web/src ./apps/web/src
COPY apps/web/public ./apps/web/public

RUN npm install && npm --workspace apps/web run build

FROM nginx:1.27-alpine

COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/web/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

