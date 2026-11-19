"""Reproducible ETA uncertainty benchmark with independent synthetic voyages."""
from math import ceil
from random import Random
from statistics import mean, median

LEVELS = (80, 90, 95)
GROUPS = ("short", "medium", "long")
METHODS = ("fixed", "pooled", "grouped")


def voyages(seed, count, stressed=False):
    rng = Random(seed)
    records = []
    for i in range(count):
        distance = rng.randint(45, 650)
        speed = rng.randint(12, 17)
        plan = distance / speed
        weather = rng.choice(("fair", "rough"))
        queue = rng.choice(("light", "light", "busy"))
        movement = 1 + (.09 if weather == "rough" else 0)
        movement += rng.uniform(-.10, .16) if weather == "rough" else rng.uniform(-.09, .09)
        waiting = rng.uniform(0, 1.6) if queue == "light" else rng.uniform(.6, 4.5)
        if stressed:
            movement += rng.uniform(.02, .14)
            waiting += rng.uniform(0, 3.5)
        group = "short" if distance < 175 else "medium" if distance < 375 else "long"
        records.append({"id": i + 1, "distance": distance, "speed": speed, "plan": plan,
                        "weather": weather, "queue": queue, "group": group,
                        "observed": plan * movement + waiting})
    return records


def fit_point(training):
    """Learn a median correction to scheduled sailing hours by observable category."""
    return {
        (group, weather, queue): median(r["observed"] - r["plan"] for r in training
                                       if (r["group"], r["weather"], r["queue"]) == (group, weather, queue))
        for group in GROUPS for weather in ("fair", "rough") for queue in ("light", "busy")
    }


def predict(row, corrections):
    return row["plan"] + corrections[row["group"], row["weather"], row["queue"]]


def conformal_radius(errors, level):
    rank = ceil((len(errors) + 1) * level / 100)
    if not 1 <= rank <= len(errors):
        raise ValueError("Calibration sample too small for the requested level")
    return sorted(errors)[rank - 1]


def calibrate(calibration, corrections, level):
    paired = [(r["group"], abs(r["observed"] - predict(r, corrections))) for r in calibration]
    return {
        "fixed": dict.fromkeys(GROUPS, 2.0),
        "pooled": dict.fromkeys(GROUPS, conformal_radius([e for _, e in paired], level)),
        "grouped": {group: conformal_radius([e for g, e in paired if g == group], level)
                    for group in GROUPS},
    }


def evaluate(rows, corrections, radii):
    cases = []
    for r in rows:
        point = predict(r, corrections)
        intervals = {}
        for method in METHODS:
            radius = radii[method][r["group"]]
            lower, upper = max(0, point - radius), point + radius
            intervals[method] = {"lower": round(lower, 4), "upper": round(upper, 4),
                                 "width": upper - lower,
                                 "covered": lower <= r["observed"] <= upper}
        cases.append({**r, "point": point, "intervals": intervals})
    return cases


def metrics(cases):
    return {
        method: {"count": len(cases),
                 "covered": sum(c["intervals"][method]["covered"] for c in cases),
                 "width": round(mean(c["intervals"][method]["width"] for c in cases), 4)}
        for method in METHODS
    }


def experiment():
    training = voyages(102, 1800)
    calibration = voyages(203, 900)
    corrections = fit_point(training)
    cohorts = {"reference": voyages(304, 1200), "stress": voyages(405, 1200, stressed=True)}
    results = {}
    for level in LEVELS:
        radii = calibrate(calibration, corrections, level)
        profiles = {}
        for name, rows in cohorts.items():
            cases = evaluate(rows, corrections, radii)
            groups = {"all": cases, **{g: [c for c in cases if c["group"] == g] for g in GROUPS}}
            profiles[name] = {
                g: {"metrics": metrics(subset),
                    "mae_raw": round(mean(abs(c["plan"]-c["observed"]) for c in subset), 4),
                    "mae_corrected": round(mean(abs(c["point"]-c["observed"]) for c in subset), 4),
                    "examples": [
                        {**{k: round(v, 4) if isinstance(v, float) else v
                            for k, v in c.items() if k != "intervals"},
                         "intervals": {m: {k: v for k, v in c["intervals"][m].items() if k != "width"}
                                       for m in METHODS}}
                        for c in subset[:12]]}
                for g, subset in groups.items()
            }
        results[str(level)] = {"profiles": profiles,
                               "radii": {m: {g: round(v, 4) for g, v in rs.items()}
                                         for m, rs in radii.items()}}
    return {"levels": results, "train": len(training), "calibration": len(calibration)}
