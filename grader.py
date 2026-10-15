import argparse, concurrent.futures as cf, json, random
import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()
TODAY = "2026-10-14"
FIELDS = {
    "Restaurants": "restaurant_name*, cuisine_type, restaurant_address*, restaurant_description*, rating*, number_of_ratings, price_range, opening_hours, phone_number*, website, directions*, images",
    "Local Business": "business_name*, business_type, address*, phone_number*, website, directions*, rating*, number_of_ratings, opening_hours_details, description*, images",
    "Home Services": "service_name*, service_type, address*, phone_number*, website, directions*, rating*, number_of_ratings, opening_hours_details, description*, images",
    "Hotels": "hotel_name*, address*, phone_number*, website, rating*, number_of_ratings, star_rating, price_range, opening_hours_details, amenities*, description*, images",
    "Sports": "league_name, date, time, team_name, team_logo_image, team_score",
    "News": "headline, publisher, publish date, summary of the story, article URL, images",
    "Shopping": "product_name*, product_price, ratings*, number_of_ratings, website_urls, features, description, images",
    "Finance": "ticker_name, last_updated_time, index_name, stock_price, stock_open, stock_high, stock_low, stock_year_high, stock_year_low, stock_market_cap, stock_volume, stock_P/E_ratio, stock_dividend_yield",
    "General Search": "a direct, correct answer to the question with supporting sources",
}
CRITERIA = """Samsung evaluation criteria:
- Relevance: does the result match the user's stated needs (cuisine, price, ambiance, constraints)?
- Information completeness: are the required attributes for the domain returned (fields marked * are required)? At least one image per list item is expected for local/place/shopping domains.
- Data accuracy: are factual details (address, phone, hours, prices, scores, figures, dates) accurate?
Defaults: US region only. Default user location is Mountain View, CA unless the query specifies another place."""
PROMPT = """You are an impartial evaluator for Samsung, comparing web search APIs that will feed an AI phone assistant. Today is {today}.

{criteria}

Domain: {domain}
Attributes expected for this domain (* = required): {fields}

User query: "{query}"

Below are the raw results returned by {n} anonymous search engines (labels {labels}). Each shows up to 5 results (title, URL, content excerpt) plus any image URLs. The assistant will answer ONLY from these results, so judge how well each engine's results let the assistant answer the query correctly and completely.

{blocks}

Score every engine 0-10 on:
- relevance: results address the query and its constraints
- completeness: the required attributes / the specific facts asked for are actually present in the content (not just a link). Count images for place/shopping domains.
- accuracy: facts are correct, current as of today, from credible/official sources, and consistent; penalize stale info, wrong entity, or contradictions. Many facts post-date your training: do not penalize a recent fact just because you don't know it; use cross-source agreement and source credibility.
- overall: how good an answer the assistant could give from these results alone.
Use the full scale and be discriminating. Keep each note under 25 words. Then name the single best label (or "tie")."""


class Score(BaseModel):
    label: str; relevance: int; completeness: int; accuracy: int; overall: int; note: str


class Verdict(BaseModel):
    scores: list[Score]; best: str; reasoning: str


def block(label, e):
    lines = [f"=== Engine {label} ==="] + [f"[{i}] {r['title']}\nURL: {r['url']}\n{r['content']}" for i, r in enumerate(e["results"], 1)]
    if not e["results"]: lines.append("(no results)")
    lines.append(f"Images returned: {len(e['images'])}")
    return "\n".join(lines)


def grade(client, row, model):
    names = list(row["engines"]); random.Random(row["query"] + model).shuffle(names)
    labels = "ABCDE"[:len(names)]; mp = dict(zip(labels, names))
    prompt = PROMPT.format(today=TODAY, criteria=CRITERIA, domain=row["domain"], fields=FIELDS[row["domain"]], query=row["query"], n=len(names),
                           labels=", ".join(labels), blocks="\n\n".join(block(l, row["engines"][mp[l]]) for l in labels))
    v = client.messages.parse(model=model, max_tokens=16000, messages=[{"role": "user", "content": prompt}], output_format=Verdict).parsed_output
    scores = {mp[s.label.strip()[-1]]: s.model_dump(exclude={"label"}) for s in v.scores if s.label.strip()[-1:] in mp}
    return {"domain": row["domain"], "query": row["query"], "judge_model": model, "scores": scores, "best": mp.get(v.best.strip()[-1:], "tie")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--model", default="claude-opus-5-5"); ap.add_argument("--workers", type=int, default=48)
    a = ap.parse_args()
    client = anthropic.Anthropic(max_retries=10)
    rows = [json.loads(l) for l in open(a.src)]
    out = []
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for f in cf.as_completed([ex.submit(grade, client, r, a.model) for r in rows]):
            try: out.append(f.result())
            except Exception as e: print("grade failed:", type(e).__name__, str(e)[:150])
    with open(a.dst, "w") as f:
        for g in sorted(out, key=lambda g: g["query"]): f.write(json.dumps(g) + "\n")
    print(f"graded {len(out)}/{len(rows)} -> {a.dst}")
