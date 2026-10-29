The Python API uses Python 3.11.18 and patched FastAPI, Starlette, AnyIO and
filelock dependencies. Rebuild and redeploy the container to update its runtime;
restarting an existing image does not replace its certificate trust behavior.
The embedded Outline server v1.3.5 and Go 1.18 builder still require a separate
security upgrade. Keep the management API restricted to trusted callers.

## Tests

With Python 3.11.18 in an isolated virtual environment:

```bash
pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

The API tests use a temporary configuration and mock the Outline restart command.

## How to run
```
git clone git@github.com:Jigsaw-Code/outline-ss-server.git
cd outline-ss-server
git checkout v1.3.5
CGO_ENABLED=0 GOOS=linux go build -o outline-ss-server .
cd ..
cp default_config.yml outline-ss-server/config.yml
pip3 install -r requirements.txt
supervisord -c supervisord.conf
```

### Docker
```
docker build -t ss-server-user-manager . 
docker run --rm --name ss-server-user-manager -v $(pwd)/config.yml:/user-manager/outline-ss-server/config.yml -p 8080:8080 -p 9000:9000 -p 9091:9091 ss-server-user-manager
```
