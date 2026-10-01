"""Published editorial pages; sections without content have no public navigation."""

from dataclasses import dataclass
from enum import StrEnum


class ContentSection(StrEnum):
    GUIDES = "guides"
    HELP = "help"
    NEWS = "news"


@dataclass(frozen=True)
class PublicContentPage:
    path: str
    title: str
    summary: str
    section: ContentSection
    analytics_surface: str


GUIDES_PATH = "/guides"
GUIDE_PATH = "/guides/zapis-vstrechi-na-mac-bez-bota"
PROTOCOL_GUIDE_PATH = "/guides/protokol-vstrechi-iz-zapisi"
MAC_MEETING_GUIDE = PublicContentPage(
    GUIDE_PATH,
    "Как записать встречу на Mac без бота и получить итоги",
    "Подготовьте Mac, проверьте обе стороны разговора и пройдите путь от записи к расшифровке и итогам.",
    ContentSection.GUIDES,
    "public_mac_meeting_guide",
)
MEETING_PROTOCOL_GUIDE = PublicContentPage(
    PROTOCOL_GUIDE_PATH,
    "Как составить протокол встречи из записи: пример решений и задач",
    "Разберите учебный диалог, отделите решения от предложений и соберите протокол по готовому шаблону.",
    ContentSection.GUIDES,
    "public_protocol_guide",
)
PUBLIC_CONTENT_PAGES = (MAC_MEETING_GUIDE, MEETING_PROTOCOL_GUIDE)
PUBLISHED_CONTENT_PATHS = (GUIDES_PATH, *(page.path for page in PUBLIC_CONTENT_PAGES))
PUBLIC_CONTENT_SURFACES = {
    GUIDES_PATH: "public_guides",
    **{page.path: page.analytics_surface for page in PUBLIC_CONTENT_PAGES},
}


def content_for_section(section: ContentSection) -> tuple[PublicContentPage, ...]:
    return tuple(page for page in PUBLIC_CONTENT_PAGES if page.section == section)
