import csv, re
def build(name_lower):  # copy of Bot._build_technique_pattern
    words = name_lower.split(" ")
    return re.compile("[ \\-]?".join(re.escape(w) for w in words))
rows = list(csv.DictReader(open("judo_techniques_bot/data/techniques_fixtures.csv")))
data = {}
for r in rows:
    for jn in r["japanese_names"].split(","):
        data[jn] = r
pats = {n: build(n.lower()) for n in data}
tests = ["Seoi-nage","Ippon-seoi-nage","Juji-gatame","Ude-hishigi-juji-gatame","O-soto-gari","Osoto-gari","Ōsoto-gari","O-uchi-gari","Ko-uchi-gari","Ko-soto-gake","Ko-soto-gari","Ura-nage","Uchi-mata","Harai-goshi","Tai-otoshi","Sode-tsuri-komi-goshi","Sode-tsurikomi-goshi","Tsuri-komi-goshi","Okuri-eri-jime","Kesa-gatame","Yoko-shiho-gatame","Kata-guruma","Sumi-gaeshi","Tani-otoshi","Kuchiki-taoshi","Morote-gari","O-goshi","De-ashi-barai","Okuri-ashi-barai","Sasae-tsuri-komi-ashi","Ude-garami","Waki-gatame","Sankaku-jime","Hadaka-jime","Uki-goshi","Soto-maki-komi","Hane-goshi","Obi-otoshi","Seoi-otoshi","Yoko-tomoe-nage"]
for t in tests:
    hits = [n for n, p in pats.items() if p.search(t.lower())]
    print(f"{t:26} -> {hits}")
