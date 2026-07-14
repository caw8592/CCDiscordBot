### Building and running your application

docker build -t <image-name> .

docker run -it --rm -e DISCORD_BOT_TOKEN='<bot-token>' <image-name>

### Requirements

A spotify_credentials.txt file in the root directory with first line client id second client secret of your dev app

### Export command for arm64

docker buildx build --platform linux/amd64,linux/arm64/v8 -t kaydall/discord_bot:latest --push .