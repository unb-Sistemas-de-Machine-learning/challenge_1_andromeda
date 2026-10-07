"""All source scoring policy and operational limits in one configuration."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AtlasConfig:
    """Atlas transport, cache and matching policy; secrets never enter repr/logs."""
    enabled: bool = False
    auth_mode: str = 'dummy'
    email: str | None = field(default=None, repr=False)
    password: str | None = field(default=None, repr=False)
    base_url: str = 'https://api.atlas.jor.br/api/v1'
    timeout: float = 20
    sync_budget: float = 120
    retries: int = 2
    retry_delay: float = 0.25
    max_bytes: int = 32 * 1024 * 1024
    max_records: int = 100_000
    refresh_after: float = 86400
    max_age: float = 7 * 86400
    max_redirects: int = 5
    max_shorteners: int = 20
    max_record_drop: float = 0.5
    mapping_version: str = 'atlas-active-online-site-v1'
    shortener_domains: tuple[str, ...] = ('t.co', 'bit.ly', 'tinyurl.com', 'goo.gl', 'ow.ly', 'is.gd', 'buff.ly', 'cutt.ly', 'linktr.ee')
    shared_domains: tuple[str, ...] = ('facebook.com', 'instagram.com', 'twitter.com', 'x.com', 'youtube.com', 'youtu.be', 'tiktok.com', 'telegram.me', 't.me', 'whatsapp.com', 'wa.me', 'blogspot.com', 'wordpress.com', 'wixsite.com', 'medium.com', 'substack.com', 'sites.google.com', 'github.io', 'netlify.app', 'vercel.app', 'google.com')

    def __post_init__(self) -> None:
        if self.auth_mode not in {'dummy', 'account'}:
            raise ValueError('atlas_invalid_auth_mode')
        if self.auth_mode == 'account' and (not self.email or not self.password):
            raise ValueError('atlas_missing_credentials')
        if self.timeout <= 0 or self.sync_budget <= 0 or not 0 < self.refresh_after <= self.max_age:
            raise ValueError('atlas_invalid_limits')


@dataclass(frozen=True)
class CredibilityConfig:
    recognized_path: Path | None = None
    blocklist_path: Path | None = None
    atlas: AtlasConfig = field(default_factory=AtlasConfig)
    # Recognition, transparency, age, institutional bonus, HTTPS.
    # The four base criteria total 100; the bonus is added afterward.
    weights: tuple[int, ...] = (40, 30, 25, 100, 5)
    transparency_weights: tuple[int, ...] = (12, 6, 12)
    age_bands: tuple[tuple[float, int], ...] = ((30, 0), (183, 5), (730, 13), (1826, 20), (float('inf'), 25))
    age_cap: int = 13
    transparency_threshold: int = 18
    institutional_tlds: tuple[str, ...] = ('gov.br', 'edu.br', 'jus.br', 'leg.br', 'mp.br')
    tracking_parameters: tuple[str, ...] = ('fbclid', 'gclid', 'dclid', 'msclkid', 'mc_cid', 'mc_eid')
    timeout: float = 6
    max_redirects: int = 5
    max_bytes: int = 5 * 1024 * 1024
    age_ttl: float = 86400
    page_ttl: float = 300
    cache_size: int = 512
    user_agent: str = 'Andromeda-SourceCredibility/1.0'
    rdap_br: str = 'https://rdap.registro.br/domain/'
    rdap_other: str = 'https://rdap.org/domain/'
    low_coverage: float = 0.5
    high_coverage: float = 0.8
    veto_threshold: int = 20


CONFIG = CredibilityConfig()
