"""Stage 3.1: DNS-only proof of control for an exact registered hostname."""
import ipaddress
import re
from urllib.parse import urlsplit
import dns.exception
import dns.resolver
import idna

PREFIX = '_ghostlead-verification.'
CHALLENGE_SECONDS = 24 * 3600
PROOF_SECONDS = 7 * 86400
RETRY_SECONDS = 10


def hostname_for(url: str) -> str:
    try:
        p = urlsplit(url)
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
            raise ValueError()
        if p.port not in (None, 443 if p.scheme == 'https' else 80):
            raise ValueError()
        host = idna.encode(p.hostname.rstrip('.'), uts46=True, std3_rules=True).decode('ascii').lower()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError()
        labels = host.split('.')
        if len(labels) < 2 or len(PREFIX + host) > 253 or not re.fullmatch(r'[a-z][a-z0-9-]*', labels[-1]):
            raise ValueError()
        if labels[-1] in {'localhost','local','internal','invalid','test','example','onion','arpa','lan','home','corp'}:
            raise ValueError()
        return host
    except (ValueError, UnicodeError, idna.IDNAError):
        raise ValueError('Verification requires a DNS hostname with a standard HTTP(S) port. IP addresses and local or reserved names are not supported.') from None


def lookup_txt(host: str, token: str) -> str:
    """One bounded DNS TXT lookup, using only the system resolver. No HTTP."""
    try:
        answer = dns.resolver.resolve(PREFIX + host + '.', 'TXT', search=False, lifetime=5.0)
        expected = token.encode('ascii')
        return 'matched' if any(b''.join(record.strings) == expected for record in answer) else 'not_found'
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return 'not_found'
    except (dns.exception.DNSException, OSError):
        return 'dns_error'
