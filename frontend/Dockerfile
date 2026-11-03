# Çok aşamalı build: Node ile derle, Nginx ile statik dosya olarak sun.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# VITE_API_BASE_URL build zamanında gömülür (Vite statik site derlemesi).
# docker-compose.yml içindeki build.args ile override edilebilir.
ARG VITE_API_BASE_URL=http://localhost:8010/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# React Router kullanılmıyor ama ileride eklenirse tek sayfa uygulaması
# fallback'ı için hazır olsun.
RUN printf 'server { listen 80; root /usr/share/nginx/html; location / { try_files $uri /index.html; } }' \
  > /etc/nginx/conf.d/default.conf
EXPOSE 80
