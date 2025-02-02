docker build -t producer_ui .

# Delete Images named <None>
docker images -f "dangling=true" -q | ForEach-Object { docker rmi $_ }