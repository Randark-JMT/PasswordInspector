# Stage 1: Build the Vue 3 / Vite frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm config set registry https://registry.npmmirror.com/ && npm install
COPY frontend/ .
RUN npm run build

# Stage 2: nginx serving built assets + SSL
FROM nginx:1.27-alpine
COPY --from=frontend-builder /app/dist /usr/share/nginx/html
# nginx.conf and certs are mounted at runtime via docker-compose volumes
