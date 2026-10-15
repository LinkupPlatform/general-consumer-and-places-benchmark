import asyncio, json, os, sys, time
import httpx
from dotenv import load_dotenv

load_dotenv()
N, MAXC, QPS = 5, 1500, float(os.environ.get("QPS", "10"))


def norm(items):
    return [{"title": (t or "")[:200], "url": u, "content": (c or "")[:MAXC]} for t, u, c in items][:N]


async def linkup_fast(cl, q):
    r = await cl.post("https://api.linkup.so/v1/search", headers={"Authorization": f"Bearer {os.environ['LINKUP_API_KEY']}"},
                      json={"q": q, "depth": "fast", "outputType": "searchResults", "includeImages": True, "maxResults": 10})
    r.raise_for_status(); res = r.json()["results"]
    return (norm([(x.get("name"), x.get("url"), x.get("content")) for x in res if x.get("type") != "image"]),
            [x["url"] for x in res if x.get("type") == "image"][:5])


async def perplexity(cl, q):
    r = await cl.post("https://api.perplexity.ai/search", headers={"Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}"},
                      json={"query": q, "max_results": N, "country": "US"})
    r.raise_for_status()
    return norm([(x.get("title"), x.get("url"), x.get("snippet")) for x in r.json()["results"]]), []


async def exa_fast(cl, q):
    r = await cl.post("https://api.exa.ai/search", headers={"x-api-key": os.environ["EXA_API_KEY"]},
                      json={"query": q, "type": "fast", "numResults": N, "userLocation": "US", "contents": {"text": {"maxCharacters": MAXC}}})
    r.raise_for_status(); res = r.json()["results"]
    return norm([(x.get("title"), x.get("url"), x.get("text")) for x in res]), [x["image"] for x in res if x.get("image")][:5]


ENGINES = {"linkup_fast": linkup_fast, "perplexity": perplexity, "exa_fast": exa_fast}


class Limiter:
    def __init__(self, qps): self.gap, self.next, self.lock = 1.0 / qps, 0.0, asyncio.Lock()
    async def wait(self):
        async with self.lock:
            now = time.monotonic(); t = max(now, self.next); self.next = t + self.gap
        if t > now: await asyncio.sleep(t - now)


async def run(rows):
    lim = {e: Limiter(QPS) for e in ENGINES}
    async with httpx.AsyncClient(timeout=60, limits=httpx.Limits(max_connections=200)) as cl:
        async def call(e, q):
            err = None
            for attempt in range(4):
                await lim[e].wait()
                try:
                    res, imgs = await ENGINES[e](cl, q)
                    return {"results": res, "images": imgs}
                except Exception as ex:
                    err = f"{type(ex).__name__}: {str(ex)[:150]}"; await asyncio.sleep(1 + 2 * attempt)
            return {"results": [], "images": [], "error": err}

        async def one(r):
            outs = await asyncio.gather(*[call(e, r["query"]) for e in ENGINES])
            return {**r, "engines": dict(zip(ENGINES, outs))}
        return await asyncio.gather(*[one(r) for r in rows])


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    rows = [json.loads(l) for l in open(src)]
    out = asyncio.run(run(rows))
    with open(dst, "w") as f:
        for r in out: f.write(json.dumps(r) + "\n")
    print(f"wrote {len(out)} rows to {dst}")
