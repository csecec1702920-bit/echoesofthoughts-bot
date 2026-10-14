"""Build an engagement-oriented caption with a rotating hashtag set."""
import random


def hashtags(cfg, seed):
    h = cfg["hashtags"]
    rng = random.Random(seed)
    core = rng.sample(h["core"], min(3, len(h["core"])))
    niche = rng.sample(h["niche"], min(h["per_post"] - len(core), len(h["niche"])))
    return core + niche


def build_caption(q, cfg, seed):
    tags = " ".join(hashtags(cfg, seed))
    return (
        f"“{q['quote']}”\n\n"
        f"{q['reflection']}\n\n"
        f"\U0001F4AD {q['question']}\n\n"
        f"Save this for a day you need it. Share it with someone who thinks deeply.\n"
        f"Follow {cfg['page_handle']} for one thought a day.\n"
        f".\n.\n.\n"
        f"{tags}"
    )
