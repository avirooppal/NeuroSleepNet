FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose port and run dev server bound to 0.0.0.0
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
