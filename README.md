# requests-logger

The purpose of this tool is to log requests made by the website and divide them
info first and third party URLs, hosts and domains. The main motivation to
build this tool was the necessity for data which I could feed into an
[adblock-simulator](https://github.com/4nd3r/adblock-simulator)
to evaluate the effectiveness of adblock filters and the host blocking files.

I consider this tool feature complete, but not bug free. PRs are welcome.

## Installation and usage

```
sudo apt install \
    build-essential \
    chromium \
    chromium-driver \
    git \
    libssl-dev \
    python3-pip \
    rustc

git clone https://github.com/4nd3r/requests-logger
cd requests-logger

sudo pip3 install -r requirements.txt
./requests_logger.py github.com
find dumps/
```
