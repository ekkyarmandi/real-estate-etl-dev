# Build the image
docker build -t dashboard --build-arg NEXT_PUBLIC_API_URL=https://your-api-url.com .

# Run the container
docker run -p 3000:3000 dashboard
