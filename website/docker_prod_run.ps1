docker run --rm `
    -dp 8000:8000 `
    --name producer_ui_container_prod `
    -w /producer_ui `
    -v "$(Get-Location):/producer_ui" `
    producer_ui `
    sh -c "gunicorn --reload -c python:config.gunicorn startup:app"

docker logs producer_ui_container_prod --follow