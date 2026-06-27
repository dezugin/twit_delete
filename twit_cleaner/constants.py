from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEYWORD_PROFILES_PATH = PROJECT_ROOT / "keyword_profiles.json"

MENU_LABELS = ("More", "Mais", "More options", "Mais opcoes", "Mais opções")
DELETE_LABELS = ("Delete", "Excluir", "Delete post", "Excluir post", "Delete Tweet", "Excluir Tweet")
CONFIRM_DELETE_LABELS = ("Delete", "Excluir")
UNREPOST_LABELS = (
    "Undo repost",
    "Undo reposts",
    "Undo Retweet",
    "Desfazer repostagem",
    "Desfazer repost",
    "Desfazer Retweet",
)

