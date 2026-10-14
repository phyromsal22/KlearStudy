FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM nginxinc/nginx-unprivileged:alpine

# បង្កើតឯកសារ PID ជាមុន និងកំណត់សិទ្ធិឱ្យអ្នកប្រើ nginx
USER root
RUN touch /tmp/nginx.pid && chown nginx:nginx /tmp/nginx.pid
USER nginx

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /app/nginx.conf

EXPOSE 8080

# ប្រើ -g ដើម្បីកំណត់ PID តែមួយគត់ និងធានាថា Nginx ដំណើរការនៅ foreground
CMD ["nginx", "-c", "/app/nginx.conf", "-g", "pid /tmp/nginx.pid; daemon off;"]