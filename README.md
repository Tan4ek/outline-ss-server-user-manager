## How to run
```
git clone git@github.com:Jigsaw-Code/outline-ss-server.git 
cp default_config.yml outline-ss-server/config.yml
pip3 install -r requirements.txt
supervisord -c supervisord.conf
```

### Docker
```
docker build -t ss-server-user-manager . 
docker run --rm --name ss-server-user-manager -v $(pwd)/config.yml:/user-manager/outline-ss-server/config.yml -p 8080:8080 -p 9000:9000 -p 9091:9091 ss-server-user-manager
```