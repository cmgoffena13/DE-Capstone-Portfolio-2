docker run --rm `
    -dp 5000:5000 `
    --name producer_ui_container_dev `
    -w /website/producer_ui `
    -v "$(Get-Location):/website/producer_ui" `
    producer_ui `
    sh -c "flask run --host=0.0.0.0"

docker logs producer_ui_container_dev --follow