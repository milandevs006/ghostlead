"""Public DNS snapshots only: no target HTTP, port scans or arbitrary resolver selection."""
from concurrent.futures import ThreadPoolExecutor
import dns.exception
import dns.resolver
from .domain_verification import public_resolve

RECORDS = ('A', 'AAAA', 'NS', 'CNAME', 'MX', 'TXT', 'SOA', 'DS')
RESOLVER = '8.8.8.8'
MAX_RECORDS = 20
MAX_TEXT = 1024


def query(name, kind, label=None):
    result = {'name': name, 'type': label or kind, 'status': 'found', 'values': [], 'ttl': None, 'truncated': False}
    try:
        answer = public_resolve(name + '.', kind, lifetime=3.0)
        result['ttl'] = answer.rrset.ttl if answer.rrset is not None else None
        for i, record in enumerate(answer):
            if i >= MAX_RECORDS:
                result['truncated'] = True
                break
            value = record.to_text()
            if len(value) > MAX_TEXT:
                result['truncated'] = True
            result['values'].append(value[:MAX_TEXT])
        if not result['values']:
            result['status'] = 'no_answer'
    except dns.resolver.NXDOMAIN:
        result['status'] = 'nxdomain'
    except dns.resolver.NoAnswer:
        result['status'] = 'no_answer'
    except dns.exception.Timeout:
        result['status'] = 'timeout'
    except (dns.exception.DNSException, OSError):
        result['status'] = 'resolver_error'
    return result


def provider_hint(values):
    providers = {'domaincontrol.com': 'GoDaddy', 'cloudflare.com': 'Cloudflare',
                 'awsdns.com': 'Amazon Route 53', 'awsdns.net': 'Amazon Route 53',
                 'awsdns.org': 'Amazon Route 53', 'awsdns.co.uk': 'Amazon Route 53',
                 'dns-parking.com': 'Hostinger', 'googledomains.com': 'Google Cloud / Google Domains'}
    matches = {provider for v in values for suffix, provider in providers.items()
               if v.lower().rstrip('.') == suffix or v.lower().rstrip('.').endswith('.' + suffix)}
    return ', '.join(sorted(matches)) if matches else None


def collect(host):
    jobs = [(host, kind, kind) for kind in RECORDS] + [('_dmarc.' + host, 'TXT', 'DMARC TXT')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda args: query(*args), jobs))
    ns = next(r for r in records if r['type'] == 'NS')
    return {'hostname': host, 'resolver': RESOLVER, 'provider_hint': provider_hint(ns['values']), 'records': records}
