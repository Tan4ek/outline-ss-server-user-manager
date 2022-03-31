## How to run
```
git clone git@github.com:Jigsaw-Code/outline-ss-server.git 
cp outline-ss-server/config_example.yml outline-ss-server/config.yml
pip3 install -r requirements.txt
supervisord -c supervisord.conf
```