from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, model_validator
from urllib.parse import urlsplit, quote

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Login(Input):
    username: Name
    password: str = Field(default='', max_length=256)
    remember: bool = False


class Activate(Input):
    username: Name
    system_password: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=10, max_length=72)


class ActivationLookup(Input):
    system_password: str = Field(min_length=1, max_length=256)


class CreateParticipant(Input):
    source_id: str | None = None
    name: Name
    team: str = Field(default='', max_length=100)
    potential: int = Field(default=4, ge=1, le=10)
    guest: bool = False


class CrestConfig(Input):
    schema_version: Literal[1] = 1
    shape: Literal['shield', 'circle', 'rounded', 'badge'] = 'shield'
    primary: str = Field(default='#173b67', pattern=r'^#[0-9a-fA-F]{6}$')
    secondary: str = Field(default='#f4e8cb', pattern=r'^#[0-9a-fA-F]{6}$')
    border: str = Field(default='#d5a83d', pattern=r'^#[0-9a-fA-F]{6}$')
    text: str = Field(default='#ffffff', pattern=r'^#[0-9a-fA-F]{6}$')
    title: str = Field(default='', max_length=22)
    initials: str = Field(default='', max_length=4)
    subtitle: str = Field(default='', max_length=18)
    year: str = Field(default='', pattern=r'^(|1[8-9][0-9]{2}|20[0-9]{2})$')
    icon: Literal['none', 'initials', 'ball', 'star', 'trophy', 'crown', 'flag', 'sport'] = 'ball'
    stripe: Literal['none', 'horizontal', 'vertical'] = 'none'
    double_border: bool = False


class TeamBadge(Input):
    kind: Literal['none', 'flag', 'club', 'custom']
    ref: str | None = Field(default=None, max_length=240)
    url: str | None = Field(default=None, max_length=500)
    credit: str | None = Field(default=None, max_length=240)
    license: str | None = Field(default=None, max_length=100)
    config: CrestConfig | None = None

    @model_validator(mode='after')
    def valid_source(self):
        if self.kind in ('none', 'custom'):
            if any((self.ref, self.url, self.credit, self.license)) or (self.kind == 'none' and self.config) or (self.kind == 'custom' and not self.config):
                raise ValueError('Configurazione stemma non valida.')
            return self
        if self.config:
            raise ValueError('Configurazione stemma non valida.')
        if not self.ref or len(self.ref) < 2:
            raise ValueError('Riferimento immagine non valido.')
        if self.kind == 'flag':
            if len(self.ref) != 2 or not self.ref.isascii() or not self.ref.isalpha() or self.ref != self.ref.upper() or self.url:
                raise ValueError('Codice bandiera non valido.')
        else:
            parsed = urlsplit(self.url or '')
            if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port
                    or parsed.query or parsed.fragment or not parsed.path.lower().endswith(('.svg', '.png', '.jpg', '.jpeg', '.webp'))):
                raise ValueError('URL dello stemma non valido.')
            if self.ref.startswith('File:'):
                valid = parsed.hostname in ('upload.wikimedia.org', 'thumb.wikimedia.org')
            elif self.ref.startswith('football-logos:'):
                path = self.ref.removeprefix('football-logos:')
                valid = (parsed.hostname == 'raw.githubusercontent.com' and
                         parsed.path == '/JoseArroyave/football-logos/main/' + quote(path, safe='/') and
                         path.startswith('logos/') and path.endswith('.svg') and
                         '..' not in path.split('/'))
            elif self.ref.startswith('sportmonks:'):
                valid = (self.ref.removeprefix('sportmonks:').isdigit() and
                         parsed.hostname == 'cdn.sportmonks.com' and
                         parsed.path.startswith('/images/soccer/teams/'))
            elif self.ref.startswith('football-data:'):
                valid = (self.ref.removeprefix('football-data:').isdigit() and
                         parsed.hostname in ('crests.football-data.org', 'upload.wikimedia.org'))
            elif self.ref.startswith('thesportsdb:'):
                valid = (self.ref.removeprefix('thesportsdb:').isdigit() and
                         parsed.hostname == 'www.thesportsdb.com' and
                         parsed.path.startswith('/images/media/team/'))
            elif self.ref.startswith('seeklogo:'):
                valid = (self.ref.removeprefix('seeklogo:').isdigit() and
                         parsed.hostname in ('images.seeklogo.com', 'seeklogo.com') and
                         parsed.path.startswith(('/logo-png/', '/images/')))
            else:
                valid = False
            if not valid:
                raise ValueError('Fonte dello stemma non valida.')
        return self


class SaveBadges(Input):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')
    badges: dict[str, TeamBadge] = Field(max_length=64)


class CreateTournament(Input):
    name: Name
    groups: list[list[Name]] = Field(min_length=1, max_length=8)
    return_matches: bool = False
    participants: list[CreateParticipant] | None = None
    badges: dict[str, TeamBadge] = Field(default_factory=dict, max_length=64)
    request_id: str = Field(pattern=r'^[0-9a-f-]{36}$')


class Result(Input):
    index: int = Field(ge=0, strict=True)
    home: int = Field(ge=0, le=20, strict=True)
    away: int = Field(ge=0, le=20, strict=True)
    valid: StrictBool


class SaveResults(Input):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')
    results: list[Result] = Field(min_length=1, max_length=1000)


class Withdrawal(Input):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')
    teams: list[Name] = Field(min_length=1, max_length=128)


class Rename(Input):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')
    name: Name


class Complete(Input):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')
