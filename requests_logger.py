#!/usr/bin/env python3

import argparse
import hashlib
import os
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

from publicsuffixlist import PublicSuffixList

import selenium
from seleniumwire import webdriver


class RequestsLogger:
    def __init__(self):
        self.id = None
        self.messages = []
        self.results = {
            'url': '',
            'host': '',
            'domain': '',
            'first_party_urls': [],
            'first_party_hosts': [],
            'third_party_urls': [],
            'third_party_hosts': [],
            'third_party_domains': []}

    def log_message(self, message):
        if self.id:
            message = f'{self.id} {message}'
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        message = f'{timestamp} {message}'
        print(message)
        self.messages.append(message)

    def reset(self):
        self.__init__()
        if self._driver is not None:
            del self._driver.requests
            try:
                self._driver.delete_all_cookies()
            except Exception:
                self.quit()

    def quit(self):
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

    _driver = None

    def _get_requests(self, url):
        if self._driver is None:
            o = webdriver.ChromeOptions()
            o.add_argument('--disable-http2')
            o.add_argument('--disk-cache-size=0')
            o.add_argument('--headless')
            o.add_argument('--incognito')
            o.add_argument('--temp-profile')
            o.add_experimental_option('prefs', {'download.default_directory': '/dev/null'})
            self._driver = webdriver.Chrome(options=o)
            self._driver.set_page_load_timeout(30)
        try:
            self._driver.get(url)
        except selenium.common.exceptions.TimeoutException:
            try:
                if len(self._driver.requests) == 0:
                    return False
            except Exception:
                return False
            self.log_message('some requests may be missing')
        except Exception:
            return False
        try:
            return self._driver.requests
        except Exception:
            return False

    def _get_host(self, url):
        return urllib.parse.urlparse(url).netloc

    _psl = None

    def _get_domain(self, host):
        if self._psl is None:
            self._psl = PublicSuffixList(only_icann=True)
        return self._psl.privatesuffix(host)

    def _divide_requests(self, requests):
        self.log_message('dividing requests')
        for request in requests:
            url = request.url
            if url.rstrip('/') == self.results['url']:
                continue
            host = self._get_host(url)
            domain = self._get_domain(host)
            if not host or not domain:
                continue
            if self.results['domain'] == domain:
                urls_result_key = 'first_party_urls'
                hosts_result_key = 'first_party_hosts'
                domains_result_key = None
            else:
                urls_result_key = 'third_party_urls'
                hosts_result_key = 'third_party_hosts'
                domains_result_key = 'third_party_domains'
            if url in self.results[urls_result_key]:
                continue
            self.results[urls_result_key].append(url)
            if host in self.results[hosts_result_key] \
                    or host == f'www.{domain}':
                continue
            self.results[hosts_result_key].append(host)
            if domains_result_key:
                if domain in self.results[domains_result_key]:
                    continue
                self.results[domains_result_key].append(domain)

    def log_requests(self, url):
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'http://{url}'
        self.log_message(f'logging requests from {url}')
        self.results['url'] = url
        self.results['host'] = self._get_host(self.results['url'])
        self.results['domain'] = self._get_domain(self.results['host'])
        if not self.results['host'] or not self.results['domain']:
            self.log_message('unable to parse host or domain')
            return False
        try:
            self.log_message('liveness check')
            urllib.request.urlopen(
                urllib.request.Request(
                    self.results['url'],
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36'}),
                    timeout=10)
        except Exception:
            self.log_message('site seems to be down or broken')
            return False
        self.log_message('start logging requests')
        requests = self._get_requests(self.results['url'])
        if not requests:
            self.log_message('no requests logged')
            return False
        self.log_message('{} requests'.format(len(requests)))
        self._divide_requests(requests)
        if not self.results['first_party_urls'] and not self.results['third_party_urls']:
            self.log_message('no requests left after division')
            return False
        for key in self.results:
            if isinstance(self.results[key], list):
                self.log_message('{} {}'.format(len(self.results[key]), key))
                self.results[key].sort()
        self.log_message('logging requests successful')
        return True

    def dump(self, dump_dir):
        os.makedirs(dump_dir, exist_ok=True)
        self.results['messages'] = self.messages.copy()
        self.log_message(f'dumping to {dump_dir}')
        for key in self.results:
            if not self.results[key]:
                continue
            handle = open(os.path.join(dump_dir, key), 'w')
            content = self.results[key]
            if isinstance(content, list):
                for line in content:
                    handle.write(f'{line}\n')
            elif isinstance(content, str):
                handle.write(f'{content}\n')
            handle.close()
        return True

    def log_requests_and_dump(self, url, dump_dir=None):
        if dump_dir is None:
            if self.id is None:
                self.id = hashlib.md5(url.encode('utf-8')).hexdigest()[0:15]
            dump_dir = f'dumps/{self.id[0]}/{self.id[1]}/{self.id}'
        if os.path.isdir(dump_dir) and os.path.isfile(os.path.join(dump_dir, 'messages')):
            self.log_message(f'already dumped to {dump_dir}')
            return False
        self.log_requests(url)
        self.dump(dump_dir)
        return True


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('input', help='URL or FILE with URLs')
    args = cli.parse_args()
    if os.path.isfile(args.input):
        urls = []
        handle = open(args.input, 'r')
        for url in handle:
            urls.append(url)
        handle.close()
    else:
        urls = [args.input]
    RL = RequestsLogger()
    for url in urls:
        if os.path.isfile('stop'):
            break
        url = url.strip()
        try:
            RL.log_requests_and_dump(url)
            RL.reset()
        except Exception:
            traceback.print_exc()
            break
    RL.quit()
