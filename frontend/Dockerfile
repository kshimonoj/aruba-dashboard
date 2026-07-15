FROM node:20-alpine

WORKDIR /app

# NEXT_PUBLIC_* はビルド時にバンドルへ埋め込まれるため build 前に設定する
ENV NEXT_PUBLIC_BACKEND_URL=ws://localhost:8001

COPY package.json package-lock.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
