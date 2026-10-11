FROM node:24-bookworm-slim
WORKDIR /app
COPY package.json ./
COPY src ./src
COPY public ./public
RUN mkdir /app/data && chown -R node:node /app
USER node
ENV HOST=0.0.0.0 PORT=4318 DATA_DIR=/app/data
EXPOSE 4318
CMD ["node", "src/server.js"]
