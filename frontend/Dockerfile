FROM node:20-alpine

WORKDIR /app

COPY package.json /app/package.json
RUN npm install --no-audit --no-fund

COPY . /app
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start", "--", "-p", "3000"]
