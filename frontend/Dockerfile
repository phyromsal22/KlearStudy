FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM nginxinc/nginx-unprivileged:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# ចម្លង Config ផ្ទាល់ខ្លួនទៅជំនួស default.conf ដែលមានស្រាប់
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

# មិនកំណត់ CMD ទេ ដើម្បីឱ្យវាប្រើ Entrypoint ដើមរបស់ Image