"""Independent SCORE_FONTE calculation. Scores describe signals, not truth."""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from urllib.parse import urljoin, urlsplit

from lxml import html as html_parser

from news_analysis.criteria.credibility_config import CONFIG, CredibilityConfig
from news_analysis.criteria.credibility_io import SourceNetwork, TTLCache, load_domain_base, normalize_url, registrable_domain
from news_analysis.criteria.credibility_policy import policy_hash, scoring_policy
from news_analysis.criteria.recognition import RecognitionProvider, recognition_detail

logger = logging.getLogger(__name__)
NAMES = ('veiculo_reconhecido', 'transparencia_editorial', 'idade_dominio', 'tld_institucional', 'https')


def criterion(name: str, points: int, maximum: int, detail: str, unavailable: bool = False) -> dict[str, Any]:
    """Build a transparent criterion record."""
    return dict(nome=name, pontos=points, maximo=maximum,
                status='indisponivel' if unavailable else 'ok' if points else 'negativo', detalhe=detail)


def recognized_vehicle(result: dict[str, Any], config: CredibilityConfig) -> dict:
    """Award recognition from a provable Atlas/local match; preserve missingness."""
    return criterion(NAMES[0], config.weights[0] if result['status'] == 'matched' else 0,
                     config.weights[0], recognition_detail(result), result['status'] in {'unavailable', 'ambiguous'})


def editorial_transparency(html: str, url: str, config: CredibilityConfig) -> dict:
    """Inspect explicit metadata and same-domain about/contact links."""
    tree = html_parser.fromstring(html or '<html/>')
    author = date = contact = False
    for meta in tree.xpath('//meta'):
        key = (meta.get('name') or meta.get('property') or meta.get('itemprop') or '').lower()
        value = (meta.get('content') or '').strip()
        author |= bool(value) and key in {'author', 'article:author'}
        date |= bool(value) and key in {'date', 'datepublished', 'article:published_time', 'pubdate'}
    author |= any(el.text_content().strip() for el in tree.xpath('//*[@rel="author" or @itemprop="author"]'))
    date |= any(el.get('datetime') for el in tree.xpath('//time[@datetime]'))

    def inspect(value: Any) -> None:
        nonlocal author, date
        if isinstance(value, list):
            for item in value:
                inspect(item)
        elif isinstance(value, dict):
            types = value.get('@type', [])
            types = [types] if isinstance(types, str) else types
            if any(t in ('Article', 'NewsArticle', 'BlogPosting', 'ReportageNewsArticle') for t in types):
                people = value.get('author', [])
                people = people if isinstance(people, list) else [people]
                author |= any(bool(p.strip()) if isinstance(p, str) else bool(p.get('name')) if isinstance(p, dict) else False for p in people)
                date |= bool(value.get('datePublished'))
            if '@graph' in value:
                inspect(value['@graph'])
    for script in tree.xpath('//script[@type="application/ld+json"]'):
        try:
            inspect(json.loads(script.text or ''))
        except (ValueError, TypeError):
            continue
    for link in tree.xpath('//a[@href]'):
        target = urljoin(url, link.get('href'))
        label = (link.text_content() + ' ' + urlsplit(target).path).lower()
        if urlsplit(target).scheme in {'http', 'https'}:
            try:
                contact |= registrable_domain(target) == registrable_domain(url) and any(word in label for word in ('sobre', 'contato', 'about', 'contact', 'quem-somos', 'quem somos'))
            except ValueError:
                pass
    points = sum(weight for present, weight in zip((author, date, contact), config.transparency_weights) if present)
    detail = '; '.join(f'{name}: {"encontrado" if found else "não encontrado"}' for name, found in [('autor', author), ('data', date), ('link Sobre/Contato', contact)])
    return criterion(NAMES[1], points, config.weights[1], detail)


def domain_age(created: datetime, recognized: bool, transparency: int, config: CredibilityConfig,
               now: datetime | None = None) -> tuple[dict, list[str]]:
    """Evaluate age bands and cap age without supporting editorial signals."""
    days = ((now or datetime.now(timezone.utc)) - created).total_seconds() / 86400
    if days < 0:
        raise ValueError('Data de criação do domínio está no futuro')
    points = next(points for limit, points in config.age_bands if days < limit)
    capped = not recognized and transparency < config.transparency_threshold
    if capped:
        points = min(points, config.age_cap)
    detail = f'Domínio com {int(days)} dias' + (f'; limite de {config.age_cap} pontos sem sinais complementares' if capped else '')
    return criterion(NAMES[2], points, config.weights[2], detail), ['dominio_recem_criado'] if days < config.age_bands[0][0] else []


def institutional_tld(domain: str, config: CredibilityConfig) -> dict:
    """Require an exact suffix boundary, never a substring match."""
    matched = any(domain.endswith('.' + suffix) for suffix in config.institutional_tlds)
    if matched:
        return criterion(NAMES[3], config.weights[3], config.weights[3],
                         'Domínio institucional oficial reconhecido')
    return dict(nome=NAMES[3], pontos=0, maximo=config.weights[3], status='neutro',
                detalhe='Domínio institucional não identificado; sem penalidade')


def https_criterion(url: str, config: CredibilityConfig) -> dict:
    """Called only after a successful fetch with default TLS validation."""
    secure = urlsplit(url).scheme == 'https'
    return criterion(NAMES[4], config.weights[4] if secure else 0, config.weights[4],
                     'HTTPS com certificado validado' if secure else 'Página final usa HTTP')


class SourceCredibility:
    """Reusable orchestrator with domain-age and per-page caches."""
    def __init__(self, config: CredibilityConfig = CONFIG, network: SourceNetwork | None = None,
                 recognition: RecognitionProvider | None = None):
        self.config = config
        self.network = network or SourceNetwork(config)
        self.ages = TTLCache(config.cache_size)
        self.pages = TTLCache(config.cache_size)
        self.recognition = recognition or RecognitionProvider(config)

    def calculate(self, url: str, *, page: tuple[str, str] | None = None) -> dict[str, Any]:
        """Return the original public SCORE_FONTE schema, without extra keys."""
        return self.calculate_with_evidence(url, page=page)[0]

    def calculate_with_evidence(self, url: str, *, page: tuple[str, str] | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Return SCORE_FONTE and recognition evidence together, including on failures.

        `page` may reuse HTML already fetched by a TLS-verifying trusted caller.
        Independent callers should use calculate(url) or calcular_score_fonte(url).
        """
        config = self.config
        errors: list[str] = []
        flags: list[str] = []
        results = [criterion(name, 0, weight, 'Não foi possível avaliar', True) for name, weight in zip(NAMES, config.weights)]
        final, domain = url, ''
        recognition_evidence = dict(status='unavailable', reason_code='destination_unavailable',
                                    checked_at=datetime.now(timezone.utc).isoformat(), providers=[], evidence=[])
        blocklist_evidence = dict(status='not_configured', content_hash=None, matched_domains=[])

        def attempt(name, operation):
            try:
                return operation()
            except Exception as exc:
                message = f'{name}: {type(exc).__name__}: {exc}'
                errors.append(message)
                logger.warning('Credibilidade indisponível: %s', message)
                return None

        normalized = attempt('url', lambda: normalize_url(url, config))
        blocked = False
        if normalized:
            final = normalized
            blocklist = None
            if config.blocklist_path is not None:
                blocklist_evidence['status'] = 'unavailable'
                base = attempt('lista_desinformacao', lambda: load_domain_base(config.blocklist_path))
                if base is not None:
                    blocklist, digest = base
                    blocklist_evidence.update(status='available', content_hash=digest)
            original_domain = attempt('dominio_original', lambda: registrable_domain(normalized))
            blocked = blocklist is not None and original_domain in blocklist
            if blocked:
                blocklist_evidence['matched_domains'].append(original_domain)
            # Resolve first: metadata must describe the destination, not the shortener.
            fetched = attempt('pagina', lambda: page or self.pages.get(normalized, config.page_ttl, lambda: self.network.fetch(normalized)))
            if fetched:
                body, destination = fetched
                final = attempt('url_final', lambda: normalize_url(destination, config)) or normalized
                domain = attempt('dominio', lambda: registrable_domain(final)) or ''
                results[1] = attempt(NAMES[1], lambda: editorial_transparency(body, final, config)) or results[1]
                results[4] = https_criterion(final, config)
            else:
                # Unresolved redirects make destination-domain metadata unavailable.
                domain = ''
            if domain:
                with ThreadPoolExecutor(max_workers=3) as executor:
                    recognized_future = executor.submit(attempt, NAMES[0], lambda: self.recognition.lookup(domain))
                    age_future = executor.submit(attempt, NAMES[2], lambda: self.ages.get(domain, config.age_ttl, lambda: self.network.creation_date(domain)))
                    recognized, created = recognized_future.result(), age_future.result()
                if recognized is not None:
                    recognition_evidence = recognized
                    results[0] = recognized_vehicle(recognized, config)
                blocked |= blocklist is not None and domain in blocklist
                if blocklist is not None and domain in blocklist and domain not in blocklist_evidence['matched_domains']:
                    blocklist_evidence['matched_domains'].append(domain)
                if created is not None:
                    age = attempt(NAMES[2], lambda: domain_age(created, bool(results[0]['pontos']), results[1]['pontos'], config))
                    if age:
                        results[2], age_flags = age
                        flags.extend(age_flags)
                results[3] = institutional_tld(domain, config)
        available = sum(item['maximo'] for item in results if item['status'] not in {'indisponivel', 'neutro'})
        score = round(sum(item['pontos'] for item in results) / available * 100) if available else None
        if blocked:
            score = 0
            flags.append('dominio_em_lista_desinformacao')
        coverage = available / sum(config.weights)
        confidence = 'baixa' if coverage < config.low_coverage else 'alta' if coverage >= config.high_coverage else 'media'
        veto = blocked or (score is not None and score < config.veto_threshold)
        policy = scoring_policy(config)
        recognition_evidence.update(policy=policy, policy_hash=policy_hash(policy), blocklist=blocklist_evidence,
                                    veto=dict(applied=veto, reason_code='blocklist_match' if blocked else
                                              'score_below_threshold' if veto else
                                              'source_unavailable' if score is None else 'score_above_threshold'))
        return dict(url_original=url, url_final=final, dominio=domain, score_fonte=score,
                    confianca_fonte=confidence, criterios=results, flags=flags,
                    veto_dominio_suspeito=veto, erros=sorted(errors)), recognition_evidence


def calcular_score_fonte(url: str) -> dict[str, Any]:
    """Calculate source credibility using the default configuration and caches."""
    from news_analysis.config import Settings
    settings = Settings.from_env()
    return configured_source(settings.credibility_config(), settings.db_path).calculate(url)


@lru_cache(maxsize=4)
def configured_source(config: CredibilityConfig, db_path: str) -> SourceCredibility:
    """Share domain/page caches without coupling independent scoring to FastAPI."""
    from news_analysis.storage.atlas_repository import AtlasRepository
    return SourceCredibility(config, recognition=RecognitionProvider(
        config, AtlasRepository(db_path) if config.atlas.enabled else None))
