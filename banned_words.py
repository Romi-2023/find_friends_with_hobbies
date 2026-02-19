# -*- coding: utf-8 -*-
"""
Baza wykluczonych słów (PL/EN) – używana do filtrowania treści i loginu.
Źródła: LDNOOBW, rozszerzenia własne.
"""

# Słowa polskie (wulgarne, obraźliwe)
BANNED_PL = [
    "burdel", "burdelmama", "chuj", "chujnia", "ciota", "cipa", "cyc", "debil",
    "dmuchać", "dupa", "dupek", "duperele", "dziwka", "fiut", "gówno", "huj",
    "jajco", "jajko", "jebać", "jebany", "kurwa", "kurwy", "kutafon", "kutas",
    "lizać pałę", "obciągać chuja", "obciągać fiuta", "obciągać loda", "pieprzyć",
    "pierdolec", "pierdolić", "pierdolnąć", "pierdolnięty", "pierdoła", "pierdzieć",
    "pizda", "pojeb", "pojebany", "popierdolony", "robić loda", "ruchać", "rzygać",
    "skurwysyn", "sraczka", "srać", "suka", "syf", "wkurwiać", "zajebisty",
    "pierdol", "kurewski", "kurwisko", "chujek", "chujowy", "jebac", "jebany",
    "kurde", "kurde", "kurdę", "kutasy", "dupki", "dupy", "gowno", "chujowy",
]

# Słowa angielskie i międzynarodowe (wulgarne, obraźliwe, NSFW)
BANNED_EN = [
    "2g1c", "anal", "anus", "apeshit", "arsehole", "ass", "asshole", "assmunch",
    "babeland", "ball sack", "bastard", "bastardo", "bdsm", "beaner", "beaners",
    "beastiality", "bestiality", "bitch", "bitches", "blowjob", "blow job",
    "bollocks", "bondage", "boner", "boob", "boobs", "booty call", "bullshit",
    "bung hole", "bunghole", "busty", "butt", "buttcheeks", "butthole",
    "camgirl", "camslut", "camwhore", "carpet muncher", "carpetmuncher",
    "circlejerk", "clit", "clitoris", "clusterfuck", "cock", "cocks",
    "coon", "coons", "creampie", "cum", "cumming", "cumshot", "cumshots",
    "cunnilingus", "cunt", "darkie", "date rape", "daterape", "dick", "dildo",
    "dingleberry", "dingleberries", "doggie style", "doggiestyle", "doggy style",
    "doggystyle", "domination", "dominatrix", "dp action", "ejaculation",
    "erotic", "escort", "fag", "faggot", "fecal", "fellatio", "fingering",
    "fisting", "footjob", "fuck", "fuckin", "fucking", "fucktards",
    "fudge packer", "fudgepacker", "gangbang", "gang bang", "genitals",
    "goatse", "god damn", "gokkun", "golden shower", "grope", "group sex",
    "hand job", "handjob", "hard core", "hardcore", "hentai", "honkey",
    "hooker", "horny", "how to kill", "how to murder", "humping", "incest",
    "intercourse", "jack off", "jail bait", "jailbait", "jerk off",
    "jigaboo", "jiggaboo", "jiggerboo", "jizz", "juggs", "kike", "kinkster",
    "kinky", "knobbing", "lolita", "male squirting", "masturbate",
    "masturbating", "masturbation", "milf", "mong", "motherfucker",
    "muff diver", "muffdiving", "nambla", "negro", "neonazi", "nigga",
    "nigger", "nig nog", "nipple", "nipples", "nsfw", "nude", "nudity",
    "nympho", "nymphomania", "orgasm", "orgy", "paedophile", "paki",
    "panties", "panty", "pedobear", "pedophile", "pegging", "penis",
    "phone sex", "piece of shit", "pikey", "pissing", "piss pig", "pisspig",
    "playboy", "pole smoker", "poof", "poon", "poontang", "punany",
    "poop chute", "poopchute", "porn", "porno", "pornography", "pubes",
    "pussy", "queef", "quim", "raghead", "rape", "raping", "rapist",
    "rectum", "rimjob", "rimming", "sadism", "scat", "schlong", "scissoring",
    "semen", "sex", "sexcam", "sexo", "sexy", "sexual", "sexually", "sexuality",
    "shemale", "shit", "shitblimp", "shitty", "shota", "skeet", "slanteye",
    "slut", "smut", "snatch", "sodomize", "sodomy", "spastic", "spic",
    "splooge", "spooge", "spunk", "strap on", "strapon", "strip club",
    "suck", "sucks", "swastika", "swinger", "threesome", "throating",
    "tit", "tits", "titties", "titty", "tosser", "towelhead", "tranny",
    "twat", "twink", "twinkie", "undressing", "upskirt", "vagina",
    "viagra", "vibrator", "voyeur", "vulva", "wank", "wetback", "whore",
    "xx", "xxx", "yaoi", "zoophilia",
]

# Wspólna pula (obrazliwe w wielu językach / krótkie)
BANNED_COMMON = [
    "idiot", "moron", "debil", "suka", "bitch", "shit", "fuck", "killer",
    "murder", "rape", "nazi", "hitler", "terror", "bomb", "hate",
]

# Struktura zgodna z app.py: język -> lista słów
BANNED_WORDS = {
    "pl": BANNED_PL,
    "en": BANNED_EN,
    "common": BANNED_COMMON,
}


def get_all_banned_words():
    """Zwraca zbiór wszystkich wykluczonych słów (małe litery) do sprawdzania loginu."""
    out = set()
    for key in ("pl", "en", "common"):
        for w in BANNED_WORDS.get(key, []):
            if w and len(w.strip()) >= 2:  # pomijamy bardzo krótkie
                out.add(w.lower().strip())
    return out


# Prekomputowana lista do szybkiego sprawdzania
_ALL_BANNED = None


def all_banned_words_cached():
    global _ALL_BANNED
    if _ALL_BANNED is None:
        _ALL_BANNED = get_all_banned_words()
    return _ALL_BANNED
