# apps/competitions/scoring.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from django.utils import timezone

SCORING_VERSION = 1


class ScoringMode:
    COUNT = "COUNT"
    SUM_LENGTH = "SUM_LENGTH"
    BEST_LENGTH = "BEST_LENGTH"
    BEST_WEIGHT = "BEST_WEIGHT"
    SUM_WEIGHT = "SUM_WEIGHT"
    SPECIES_TABLE = "SPECIES_TABLE"
    COMBO = "COMBO"


SCORING_MODE_CHOICES = [
    (ScoringMode.COUNT, "Počet úlovkov"),
    (ScoringMode.SUM_LENGTH, "Súčet dĺžok"),
    (ScoringMode.BEST_LENGTH, "Najväčšia ryba podľa dĺžky"),
    (ScoringMode.BEST_WEIGHT, "Najväčšia ryba podľa váhy"),
    (ScoringMode.SUM_WEIGHT, "Súčet váhy"),
    (ScoringMode.SPECIES_TABLE, "Bodovanie podľa druhu"),
    (ScoringMode.COMBO, "Kombinované bodovanie"),
]

# Zoznam režimov, ktoré je možné skladať do kombinovaného bodovania.
COMBO_COMPONENT_CHOICES = [
    (ScoringMode.COUNT, "Počet úlovkov"),
    (ScoringMode.SUM_LENGTH, "Súčet dĺžok"),
    (ScoringMode.BEST_LENGTH, "Najväčšia ryba podľa dĺžky"),
    (ScoringMode.BEST_WEIGHT, "Najväčšia ryba podľa váhy"),
    (ScoringMode.SUM_WEIGHT, "Súčet váhy"),
    (ScoringMode.SPECIES_TABLE, "Bodovanie podľa druhu"),
]

# Mapa režim -> názov pre jednoduchší popis bodovania.
SCORING_MODE_LABELS = dict(SCORING_MODE_CHOICES)

class TieBreakerPreset:
    AUTO = "AUTO"
    BIGGEST_FISH_THEN_EARLIEST = "BIGGEST_FISH_THEN_EARLIEST"
    EARLIEST_CATCH = "EARLIEST_CATCH"
    MOST_CATCHES_THEN_BIGGEST = "MOST_CATCHES_THEN_BIGGEST"


TIE_BREAKER_CHOICES = [
    (TieBreakerPreset.AUTO, "Automaticky podľa zvoleného bodovania"),
    (TieBreakerPreset.BIGGEST_FISH_THEN_EARLIEST, "Najväčšia ryba → potom skorší čas úlovku"),
    (TieBreakerPreset.EARLIEST_CATCH, "Skorší čas úlovku vyhráva"),
    (TieBreakerPreset.MOST_CATCHES_THEN_BIGGEST, "Viac úlovkov → potom najväčšia ryba"),
]

# Mapa presetov remízy -> text pre zobrazenie v UI.
TIE_BREAKER_LABELS = dict(TIE_BREAKER_CHOICES)

def _d(val: Any, default: Decimal = Decimal("0")) -> Decimal:
    if val is None or val == "":
        return default
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return default


def normalize_species_key(s: str) -> str:
    return (s or "").strip().lower()


def parse_species_points(text: str) -> dict[str, int]:
    """
    Očakávaný input (riadok = 1 druh):
      Kapor=50
      Šťuka: 80
      Pstruh ; 30

    Povolené separátory: '=', ':', ';'
    """
    out: dict[str, int] = {}
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        sep = None
        for candidate in ("=", ":", ";"):
            if candidate in line:
                sep = candidate
                break
        if not sep:
            # ak user dá len "Kapor 50", skúsime posledné "slovo" ako číslo
            parts = line.split()
            if len(parts) >= 2 and parts[-1].isdigit():
                key = " ".join(parts[:-1]).strip()
                val = parts[-1]
            else:
                continue
        else:
            left, right = line.split(sep, 1)
            key = left.strip()
            val = right.strip()

        if not key:
            continue
        try:
            points = int(val)
        except ValueError:
            continue
        out[normalize_species_key(key)] = points

    return out


def normalize_rules(rules: dict | None) -> dict:
    rules = rules or {}
    mode = rules.get("mode") or ScoringMode.COUNT
    params = rules.get("params") or {}
    tie = rules.get("tie_breaker") or {}

    normalized = {
        "version": int(rules.get("version") or SCORING_VERSION),
        "mode": mode,
        "params": params,
        "tie_breaker": {
            "preset": tie.get("preset") or TieBreakerPreset.AUTO,
        },
        "requirements": rules.get("requirements") or {},
    }

    # doplň requirements defaultmi (fallback)
    req = normalized["requirements"]
    if "length_required" not in req or "weight_required" not in req:
        if mode in (ScoringMode.SUM_LENGTH, ScoringMode.BEST_LENGTH):
            req.setdefault("length_required", True)
            req.setdefault("weight_required", False)
        elif mode in (ScoringMode.SUM_WEIGHT, ScoringMode.BEST_WEIGHT):
            req.setdefault("length_required", False)
            req.setdefault("weight_required", True)
        else:
            req.setdefault("length_required", False)
            req.setdefault("weight_required", False)

    return normalized


def describe_rules(rules: dict | None) -> str:
    # Vráti používateľský popis pravidiel bodovania pre detail súťaže a scoreboard.
    r = normalize_rules(rules)
    mode = r["mode"]
    p = r["params"]

    if mode == ScoringMode.COUNT:
        return f"Počet úlovkov – {int(p.get('points_per_catch', 10))} bodov za každý úlovok."

    if mode == ScoringMode.SUM_LENGTH:
        return f"Súčet dĺžok – {_d(p.get('points_per_cm', '1'))} bodov za 1 cm."

    if mode == ScoringMode.BEST_LENGTH:
        return (
            f"Najväčšia ryba podľa dĺžky – {_d(p.get('points_per_cm', '1'))} bodov za 1 cm. "
            f"Počíta sa len najdlhšia ryba."
        )

    if mode == ScoringMode.BEST_WEIGHT:
        return (
            f"Najväčšia ryba podľa váhy – {_d(p.get('points_per_kg', '10'))} bodov za 1 kg. "
            f"Počíta sa len najťažšia ryba."
        )

    if mode == ScoringMode.SUM_WEIGHT:
        return f"Súčet váhy – {_d(p.get('points_per_kg', '10'))} bodov za 1 kg."

    if mode == ScoringMode.SPECIES_TABLE:
        return "Bodovanie podľa druhu – každý druh ryby má pridelený vlastný počet bodov."

    if mode == ScoringMode.COMBO:
        selected_modes = p.get("selected_modes") or []
        labels = [SCORING_MODE_LABELS.get(item, item) for item in selected_modes]
        if labels:
            return f"Kombinované bodovanie – {' + '.join(labels)}."
        return "Kombinované bodovanie – bez zvolených pravidiel."

    return "Pravidlá bodovania nie sú nastavené."

def build_rules_detail(rules: dict | None) -> dict:
    # Poskladá detailné pravidlá bodovania do štruktúry pripravenej pre modal v detaile súťaže.
    r = normalize_rules(rules)
    mode = r["mode"]
    p = r["params"] or {}
    req = r.get("requirements") or {}
    tie_preset = (r.get("tie_breaker") or {}).get("preset") or TieBreakerPreset.AUTO

    species_points = p.get("species_points") or {}
    species_rows = [
        {
            "species": species,
            "points": int(points),
        }
        for species, points in sorted(species_points.items(), key=lambda item: item[0])
    ]

    combo_selected_modes = p.get("selected_modes") or []
    combo_mode_labels = [SCORING_MODE_LABELS.get(item, item) for item in combo_selected_modes]

    detail = {
        "mode": mode,
        "mode_label": SCORING_MODE_LABELS.get(mode, mode),
        "summary": describe_rules(rules),
        "tie_breaker_label": TIE_BREAKER_LABELS.get(tie_preset, tie_preset),
        "length_required": bool(req.get("length_required")),
        "weight_required": bool(req.get("weight_required")),
        "uses_count_points": False,
        "uses_length_points": False,
        "uses_weight_points": False,
        "uses_species_points": False,
        "count_points_per_catch": None,
        "length_points_per_cm": None,
        "weight_points_per_kg": None,
        "default_species_points": int(p.get("default_species_points", 0)),
        "species_rows": species_rows,
        "combo_mode_labels": combo_mode_labels,
    }

    if mode == ScoringMode.COUNT:
        detail["uses_count_points"] = True
        detail["count_points_per_catch"] = int(p.get("points_per_catch", 10))

    elif mode in (ScoringMode.SUM_LENGTH, ScoringMode.BEST_LENGTH):
        detail["uses_length_points"] = True
        detail["length_points_per_cm"] = _d(p.get("points_per_cm", "1"))

    elif mode in (ScoringMode.SUM_WEIGHT, ScoringMode.BEST_WEIGHT):
        detail["uses_weight_points"] = True
        detail["weight_points_per_kg"] = _d(p.get("points_per_kg", "10"))

    elif mode == ScoringMode.SPECIES_TABLE:
        detail["uses_species_points"] = True

    elif mode == ScoringMode.COMBO:
        if ScoringMode.COUNT in combo_selected_modes:
            detail["uses_count_points"] = True
            detail["count_points_per_catch"] = int(p.get("points_per_catch", 10))

        if (
            ScoringMode.SUM_LENGTH in combo_selected_modes
            or ScoringMode.BEST_LENGTH in combo_selected_modes
        ):
            detail["uses_length_points"] = True
            detail["length_points_per_cm"] = _d(p.get("points_per_cm", "1"))

        if (
            ScoringMode.SUM_WEIGHT in combo_selected_modes
            or ScoringMode.BEST_WEIGHT in combo_selected_modes
        ):
            detail["uses_weight_points"] = True
            detail["weight_points_per_kg"] = _d(p.get("points_per_kg", "10"))

        if ScoringMode.SPECIES_TABLE in combo_selected_modes:
            detail["uses_species_points"] = True

    return detail

@dataclass
class ScoreRow:
    user: Any
    points: Decimal
    catches_count: int
    sum_length: Decimal
    sum_weight: Decimal
    best_length: Decimal
    best_weight: Decimal
    earliest_caught_at: Any


def _safe_dt(dt):
    # aby sort fungoval aj keď je None
    return dt or timezone.make_aware(timezone.datetime.max)


def build_scoreboard(*, approved_catches: Iterable[Any], rules: dict | None) -> list[ScoreRow]:
    r = normalize_rules(rules)
    mode = r["mode"]
    p = r["params"]
    tie_preset = (r.get("tie_breaker") or {}).get("preset") or TieBreakerPreset.AUTO

    # zoskupenie úlovkov podľa usera
    by_user: dict[int, list[Any]] = {}
    user_obj: dict[int, Any] = {}

    for c in approved_catches:
        uid = int(getattr(c, "user_id"))
        by_user.setdefault(uid, []).append(c)
        user_obj[uid] = getattr(c, "user")

    rows: list[ScoreRow] = []

    # predpripravené parametre
    points_per_catch = int(p.get("points_per_catch", 10))

    points_per_cm = _d(p.get("points_per_cm", "1"))
    points_per_kg = _d(p.get("points_per_kg", "10"))
    combo_selected_modes = set(p.get("selected_modes") or [])

    species_points = p.get("species_points") or {}
    species_points = {normalize_species_key(k): int(v) for k, v in species_points.items()}
    species_default = int(p.get("default_species_points", 0))

    base_points = int(p.get("base_points_per_catch", 0))
    length_mult = _d(p.get("length_multiplier", "0"))
    weight_mult = _d(p.get("weight_multiplier", "0"))
    combo_species_points = p.get("species_points") or {}
    combo_species_points = {normalize_species_key(k): int(v) for k, v in combo_species_points.items()}
    combo_species_default = int(p.get("default_species_points", 0))
    top_n = p.get("top_n")
    top_n = int(top_n) if (top_n is not None and str(top_n).isdigit()) else None

    for uid, catches in by_user.items():
        cnt = len(catches)

        lengths = [(_d(getattr(c, "length_cm", None))) for c in catches if getattr(c, "length_cm", None) is not None]
        weights = [(_d(getattr(c, "weight_kg", None))) for c in catches if getattr(c, "weight_kg", None) is not None]

        sum_len = sum(lengths, Decimal("0"))
        sum_w = sum(weights, Decimal("0"))
        best_len = max(lengths) if lengths else Decimal("0")
        best_w = max(weights) if weights else Decimal("0")

        earliest = None
        for c in catches:
            dt = getattr(c, "caught_at", None)
            if earliest is None or (dt is not None and dt < earliest):
                earliest = dt

        points = Decimal("0")

        if mode == ScoringMode.COUNT:
            points = Decimal(points_per_catch * cnt)

        elif mode == ScoringMode.SUM_LENGTH:
            points = (sum_len * points_per_cm)

        elif mode == ScoringMode.BEST_LENGTH:
            points = (best_len * points_per_cm)

        elif mode == ScoringMode.BEST_WEIGHT:
            points = (best_w * points_per_kg)    

        elif mode == ScoringMode.SUM_WEIGHT:
            points = (sum_w * points_per_kg)

        elif mode == ScoringMode.SPECIES_TABLE:
            s = 0
            for c in catches:
                key = normalize_species_key(getattr(c, "species", ""))
                s += int(species_points.get(key, species_default))
            points = Decimal(s)

        elif mode == ScoringMode.COMBO:
            # Spočíta body zo všetkých zvolených bodovacích režimov.
            if combo_selected_modes:
                if ScoringMode.COUNT in combo_selected_modes:
                    points += Decimal(points_per_catch * cnt)

                if ScoringMode.SUM_LENGTH in combo_selected_modes:
                    points += (sum_len * points_per_cm)

                if ScoringMode.BEST_LENGTH in combo_selected_modes:
                    points += (best_len * points_per_cm)

                if ScoringMode.BEST_WEIGHT in combo_selected_modes:
                    points += (best_w * points_per_kg)    

                if ScoringMode.SUM_WEIGHT in combo_selected_modes:
                    points += (sum_w * points_per_kg)

                if ScoringMode.SPECIES_TABLE in combo_selected_modes:
                    species_sum = 0
                    for c in catches:
                        key = normalize_species_key(getattr(c, "species", ""))
                        species_sum += int(species_points.get(key, species_default))
                    points += Decimal(species_sum)
            else:
                # Fallback pre starý COMBO formát, aby sa nerozbili staré uložené dáta.
                per_catch_points: list[Decimal] = []
                for c in catches:
                    key = normalize_species_key(getattr(c, "species", ""))
                    sp = int(combo_species_points.get(key, combo_species_default))
                    lc = _d(getattr(c, "length_cm", None))
                    wk = _d(getattr(c, "weight_kg", None))
                    per = Decimal(base_points) + (lc * length_mult) + (wk * weight_mult) + Decimal(sp)
                    per_catch_points.append(per)

                per_catch_points.sort(reverse=True)
                if top_n:
                    per_catch_points = per_catch_points[:top_n]
                points = sum(per_catch_points, Decimal("0"))

        rows.append(
            ScoreRow(
                user=user_obj[uid],
                points=points,
                catches_count=cnt,
                sum_length=sum_len,
                sum_weight=sum_w,
                best_length=best_len,
                best_weight=best_w,
                earliest_caught_at=earliest,
            )
        )

    # --- sorting: points DESC + tie-breaker preset ---
    def key(row: ScoreRow):
        # points desc
        base = (-row.points,)

        if tie_preset == TieBreakerPreset.EARLIEST_CATCH:
            # skorší vyhráva
            return base + (_safe_dt(row.earliest_caught_at), -row.best_length, -row.best_weight, -Decimal(row.catches_count))

        if tie_preset == TieBreakerPreset.MOST_CATCHES_THEN_BIGGEST:
            return base + (-Decimal(row.catches_count), -row.best_length, -row.best_weight, _safe_dt(row.earliest_caught_at))

        if tie_preset == TieBreakerPreset.BIGGEST_FISH_THEN_EARLIEST:
            return base + (-row.best_length, -row.best_weight, _safe_dt(row.earliest_caught_at), -Decimal(row.catches_count))

        # AUTO podľa mode
        if mode == ScoringMode.COUNT:
            return base + (-Decimal(row.catches_count), -row.best_length, _safe_dt(row.earliest_caught_at))
        if mode in (ScoringMode.SUM_LENGTH,):
            return base + (-row.best_length, _safe_dt(row.earliest_caught_at))
        if mode in (ScoringMode.SUM_WEIGHT,):
            return base + (-row.best_weight, _safe_dt(row.earliest_caught_at))
        if mode in (ScoringMode.BEST_LENGTH,):
            return base + (-row.best_length, _safe_dt(row.earliest_caught_at))
        if mode in (ScoringMode.BEST_WEIGHT,):
            return base + (-row.best_weight, _safe_dt(row.earliest_caught_at))

        if mode == ScoringMode.COMBO:
            if ScoringMode.BEST_LENGTH in combo_selected_modes or ScoringMode.SUM_LENGTH in combo_selected_modes:
                return base + (-row.best_length, _safe_dt(row.earliest_caught_at))
            if ScoringMode.BEST_WEIGHT in combo_selected_modes or ScoringMode.SUM_WEIGHT in combo_selected_modes:
                return base + (-row.best_weight, _safe_dt(row.earliest_caught_at))
            if ScoringMode.COUNT in combo_selected_modes:
                return base + (-Decimal(row.catches_count), -row.best_length, _safe_dt(row.earliest_caught_at))
            return base + (-row.best_length, _safe_dt(row.earliest_caught_at))
        
        # SPECIES_TABLE / COMBO fallback
        return base + (-row.best_length, _safe_dt(row.earliest_caught_at))

    rows.sort(key=key)
    return rows
