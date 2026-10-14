FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM python:3.11-slim

WORKDIR /app

COPY --from=build /app/dist /app/static
COPY serve.py /app/serve.py

EXPOSE 8080

CMD ["python", "/app/serve.py"]