#!/usr/bin/env python3

# THIS IS WORK IN PROGRESS

import argparse
import os
import re


class RequestsLoggerDump:
    def __init__(self, dump_path):
        for file in [
                'url',
                'host',
                'domain',
                'first_party_urls',
                'first_party_hosts',
                'third_party_urls',
                'third_party_hosts',
                'third_party_domains']:
            read = self._read_file(os.path.join(dump_path, file))
            if read and file in ['url', 'host', 'domain']:
                read = read[0]
            setattr(self, file, read)
        dirname = os.path.dirname(os.path.realpath(__file__))
        groups_file = os.path.join(dirname, 'requests_logger_dump.groups')
        excludes_file = os.path.join(dirname, 'requests_logger_dump.excludes')
        self._load_groups(groups_file)
        self._load_excludes(excludes_file)
        self._process_third_party_domains()

    def _read_file(self, file_path):
        if not os.path.isfile(file_path):
            return False
        handle = open(file_path, 'r')
        content = []
        for line in handle:
            content.append(line.strip())
        handle.close()
        if len(content) == 0:
            return False
        return content

    _groups = None

    def _load_groups(self, groups_file):
        groups = self._read_file(groups_file)
        if not groups:
            return False
        self._groups = {}
        for group in groups:
            group_name, group_regex = group.split()
            if group_name not in self._groups.keys():
                self._groups[group_name] = []
            self._groups[group_name].append(re.compile(group_regex))
        return True

    def _get_group(self, host_or_domain):
        for group_name in self._groups:
            group_regexes = self._groups[group_name]
            if any(group_regex.match(host_or_domain) for group_regex in group_regexes):
                return group_name
        return False

    _excludes = None

    def _load_excludes(self, excludes_file):
        excludes = self._read_file(excludes_file)
        if not excludes:
            return False
        self._excludes = []
        for exclude in excludes:
            self._excludes.append(re.compile(exclude))
        return True

    def _is_excluded(self, host_or_domain):
        if any(regex.match(host_or_domain) for regex in self._excludes):
            return True
        return False

    def _process_third_party_domains(self):
        if not self.third_party_domains:
            return False
        new_third_party_domains = []
        for domain in self.third_party_domains.copy():
            group = self._get_group(domain)
            if group:
                domain = group
            if self._is_excluded(domain):
                continue
            if domain in new_third_party_domains:
                continue
            new_third_party_domains.append(domain)
        self.third_party_domains = new_third_party_domains
        return True

    def _get_third_party_hosts(self, domain):
        if not self.third_party_hosts:
            return False
        hosts = []
        for host in self.third_party_hosts:
            if domain in self._groups.keys():
                regexes = self._groups[domain]
                if any(regex.match(host) for regex in regexes):
                    hosts.append(host)
            else:
                if not re.search('{}$'.format(re.escape(f'.{domain}')), host):
                    continue
                hosts.append(host)
        return hosts

    def print_third_parties(self):
        if not self.third_party_domains:
            return
        print(self.domain)
        for third_party_domain in self.third_party_domains:
            print(f'  {third_party_domain}')
            for third_party_host in self._get_third_party_hosts(third_party_domain):
                print(f'    {third_party_host}')

    def print_third_party_hosts(self):
        if not self.third_party_hosts:
            return
        for third_party_host in self.third_party_hosts:
            print('{} {}'.format(self.domain, third_party_host))

    def print_third_party_domains(self):
        if not self.third_party_domains:
            return
        for third_party_domain in self.third_party_domains:
            print('{} {}'.format(self.domain, third_party_domain))


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('-h3', action='store_true')
    cli.add_argument('-d3', action='store_true')
    cli.add_argument('dump_path')
    args = cli.parse_args()
    dump = RequestsLoggerDump(args.dump_path)
    if args.h3:
        dump.print_third_party_hosts()
    elif args.d3:
        dump.print_third_party_domains()
    else:
        dump.print_third_parties()
