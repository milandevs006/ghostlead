"""Stage 3.3: deny-by-default destination planning. No target HTTP requests.
A plan is advisory and short-lived, not a reusable authorisation or a scan result.
Future HTTP workers must enforce numeric-address socket pinning and re-check proof.
"""
from dataclasses import dataclass
import ipaddress
import re
from urllib.parse import urlsplit, urljoin
import dns.exception
import dns.resolver
from .domain_verification import hostname_for, public_resolve

MAX_ADDRESSES = 32
DNS_LIFETIME = 3.0
MAX_REDIRECTS = 3
# Proposed worker budgets: not enforced on HTTP because there is no HTTP worker yet.
CONNECT_TIMEOUT = 5
RESPONSE_LIMIT = 512 * 1024

class SafetyError(ValueError):
    pass

@dataclass(frozen=True)
class Target:
    url: str
    hostname: str
    scheme: str
    port: int


def validate_url(raw: str) -> Target:
    if not isinstance(raw, str) or not raw or len(raw) > 2048:
        raise SafetyError('Invalid destination URL length.')
    if any(ord(c) <= 32 or ord(c) >= 127 or c == '\\' for c in raw) or re.search(r'%(?:0[0-9a-f]|1[0-9a-f]|7f|5c)', raw, re.I):
        raise SafetyError('Unsafe URL characters; use an ASCII, percent-encoded URL.')
    try:
        p = urlsplit(raw)
        host = hostname_for(raw)
        if p.fragment or '#' in raw or '@' in p.netloc or '%' in p.netloc or p.netloc.endswith('.'):
            raise ValueError()
        port = 443 if p.scheme == 'https' else 80
        if p.netloc.lower() not in (host, f'{host}:{port}'):
            raise ValueError()
    except ValueError:
        raise SafetyError('Only canonical public HTTP(S) hostnames and default ports are allowed.') from None
    return Target(raw, host, p.scheme, port)


def address_allowed(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    if not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_loopback or ip.is_link_local or ip.is_unspecified:
        return False
    if ip.version == 6:
        # Fail closed on mapped/transition/translation and non-global-unicast space.
        if '%' in value or ip.ipv4_mapped or ip.sixtofour or ip.teredo or ip not in ipaddress.ip_network('2000::/3'):
            return False
        if any(ip in ipaddress.ip_network(n) for n in ('2001::/23','2001:db8::/32','3fff::/20')):
            return False
    return True


def resolve_addresses(target: Target) -> tuple[str, ...]:
    values = []
    for kind in ('A', 'AAAA'):
        try:
            answer = public_resolve(target.hostname + '.', kind, lifetime=DNS_LIFETIME)
            for record in answer:
                address = str(record.address)
                if not address_allowed(address):
                    raise SafetyError('DNS returned a non-public or disallowed address. Destination blocked.')
                values.append(str(ipaddress.ip_address(address)))
                if len(values) > MAX_ADDRESSES:
                    raise SafetyError('DNS answer exceeds the address limit.')
        except dns.resolver.NoAnswer:
            continue
        except (dns.exception.DNSException, OSError, AttributeError, ValueError) as exc:
            if isinstance(exc, SafetyError):
                raise
            raise SafetyError('DNS resolution incomplete; destination blocked.') from None
    if not values:
        raise SafetyError('No public A or AAAA addresses returned.')
    return tuple(dict.fromkeys(values))


def validate_redirect(origin: Target, current: Target, location: str, hops: int) -> Target:
    """Future worker must call before each redirect and resolve/pin again."""
    if hops >= MAX_REDIRECTS or not location or any(ord(c) <= 32 or ord(c) >= 127 or c == '\\' for c in location):
        raise SafetyError('Redirect limit or unsafe redirect location.')
    target = validate_url(urljoin(current.url, location))
    if (target.hostname, target.scheme, target.port) != (origin.hostname, origin.scheme, origin.port):
        raise SafetyError('Cross-origin redirects and protocol changes are blocked.')
    return target
