FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ប្តូរពី nginx-unprivileged ទៅ nginx:alpine ធម្មតា
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# ជំនួស default.conf ដែលមានស្រាប់
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

# ប្តូរ Port នៅក្នុង nginx.conf ទៅ 8080 (ឬក៏ប្តូរទៅ 80)