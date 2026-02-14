FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Allow API base override at build time; defaults to backend service name in Compose
ARG VITE_API_BASE=http://localhost:8001
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm run build

FROM nginx:stable-alpine AS runtime
ARG OCI_IMAGE_SOURCE=https://github.com/ieaves/llm-council
LABEL org.opencontainers.image.source=$OCI_IMAGE_SOURCE
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
