"""Generate StealthHumanizer class and append to audit_portal.py"""
import pathlib

TARGET = pathlib.Path('d:/notion-live-analyzer/modules/audit_portal.py')

# Read current file
current = TARGET.read_text(encoding='utf-8')

# Only append if StealthHumanizer is not already there
if 'class StealthHumanizer' in current:
    print('StealthHumanizer already exists, skipping')
else:
    with TARGET.open('a', encoding='utf-8') as f:
        f.write("""

# ═══════════════════════════════════════════════════════════════════════
# 2. STEALTH HUMANIZER — Multi-Layer AI-Detection Evasion
# ═══════════════════════════════════════════════════════════════════════
class StealthHumanizer:
    \"\"\"Advanced multi-layer AI-text humanizer covering all tell-tale traces.\"\"\"

    def __init__(self):
        # Contractions
        self._contractions = {
            "cannot": "can't", "will not": "won't", "do not": "don't",
            "does not": "doesn't", "did not": "didn't", "is not": "isn't",
            "are not": "aren't", "was not": "wasn't", "were not": "weren't",
            "have not": "haven't", "has not": "hasn't", "had not": "hadn't",
            "could not": "couldn't", "would not": "wouldn't", "should not": "shouldn't",
            "might not": "mightn't", "must not": "mustn't", "it is": "it's",
            "that is": "that's", "there is": "there's", "here is": "here's",
            "i am": "I'm", "i will": "I'll", "i would": "I'd",
            "i have": "I've", "you are": "you're", "you will": "you'll",
            "you have": "you've", "we are": "we're", "we will": "we'll",
            "they are": "they're", "they will": "they'll", "they have": "they've",
            "let us": "let's",
        }
        # Hedging phrases
        self._hedges = [
            "arguably", "broadly", "comparatively", "conceivably", "could be argued that",
            "essentially", "generally", "in many cases", "in some respects",
            "indicatively", "largely", "mostly", "notably",
            "observably", "on the whole", "plausibly", "potentially", "presumably",
            "putatively", "relatively", "reportedly", "roughly",
            "seemingly", "somewhat", "suggestively", "tentatively",
            "to some extent", "typically", "usually", "virtually",
        ]
        # Transition phrases
        self._transitions = [
            "Additionally,", "Alternatively,", "As a consequence,",
            "As a result,", "By contrast,", "Concurrently,",
            "Consequently,", "Conversely,", "Correspondingly,",
            "Equally important,", "Furthermore,", "Hence,",
            "In addition,", "In comparison,", "In contrast,",
            "In other words,", "In particular,", "In practice,",
            "In that regard,", "Indeed,", "More precisely,",
            "Moreover,", "Nevertheless,", "Nonetheless,",
            "Notably,", "On the contrary,", "On the one hand,",
            "On the other hand,", "Rather,", "Similarly,",
            "Specifically,", "Subsequently,", "Thus,",
            "To illustrate,", "Ultimately,", "Whereas,",
        ]
        # Vocabulary upgrades (common -> sophisticated)
        self._vocab = {
            "big": "substantial", "good": "noteworthy", "bad": "suboptimal",
            "new": "novel", "old": "established", "many": "numerous",
            "show": "demonstrate", "use": "employ", "get": "obtain",
            "make": "generate", "give": "provide", "help": "facilitate",
            "change": "modify", "need": "necessitate", "try": "endeavor",
            "look": "examine", "think": "contend", "find": "identify",
            "way": "approach", "part": "component", "thing": "element",
            "important": "significant", "different": "distinct",
            "clear": "evident", "right": "appropriate",
            "wrong": "erroneous", "simple": "straightforward",
            "hard": "challenging", "easy": "accessible",
            "quick": "expeditious", "slow": "gradual",
            "start": "initiate", "end": "conclude",
            "first": "primary", "second": "secondary",
            "before": "previously", "after": "subsequently",
        }

    def compute_stats(self, text: str) -> Dict[str, Any]:
        \"\"\"Compute statistical profile of text.\"\"\"
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        words = text.split()
        word_lens = [len(w) for w in words]
        sent_lens = [len(s.split()) for s in sentences]
        return {
            "words": len(words),
            "sentences": len(sentences),
            "avg_word_len": round(statistics.mean(word_lens), 2) if word_lens else 0,
            "avg_sent_len": round(statistics.mean(sent_lens), 2) if sent_lens else 0,
            "burstiness": round(statistics.stdev(sent_lens), 2) if len(sent_lens) > 1 else 0,
            "perplexity": round(len(set(w.lower() for w in words)) / max(len(words), 1) * 100, 1),
            "contractions": sum(1 for c in self._contractions for p in [c.split()] if all(w in words for w in p)),
            "hedges": sum(1 for h in self._hedges if h in text.lower()),
        }

    def full_humanize(self, text: str, burstiness: float = 0.6,
                      perplexity_noise: float = 0.3) -> str:
        \"\"\"Apply all humanization layers.\"\"\"
        result = text
        # Layer 1: Contractions
        for formal, contraction in sorted(self._contractions.items(), key=lambda x: -len(x[0])):
            if np.random.random() < burstiness + 0.2:
                result = re.sub(r'\\b' + formal + r'\\b', contraction, result, flags=re.IGNORECASE)
        # Layer 2: Vocabulary upgrades
        for common, advanced in self._vocab.items():
            if np.random.random() < perplexity_noise:
                result = re.sub(r'\\b' + common + r'\\b', advanced, result, flags=re.IGNORECASE)
        # Layer 3: Hedging
