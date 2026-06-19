"""캐시 로직 스모크 테스트 — Gemini 호출 0콜.

검증 항목:
  1. MISS: 처음 호출 시 generate_content 1회 불림, 결과가 캐시에 저장됨
  2. HIT:  같은 입력 재호출 시 generate_content 불리지 않음, 동일 결과 반환
  3. 다른 입력: 캐시 키가 달라 별도 MISS — 캐시 파일 2개 생성
  4. OFF:  GENAI_CACHE=0 이면 캐시 무시하고 매번 실제 호출

실행: python test_cache.py
"""
import sys, os, types as _types, re as _re, json, shutil, unittest.mock as _mock

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── 가짜 google.genai 심기 ────────────────────────────────────────────────────
class _FakeModels:
    def generate_content(self, **kw): pass   # 실제로는 mock으로 교체됨

class _FakeClient:
    models = _FakeModels()

class _FakeTypes:
    class GenerateContentConfig:
        def __init__(self, **kw): pass

_fake_genai = _types.ModuleType("google.genai")
_fake_genai.Client = lambda **kw: _FakeClient()
_fake_genai.types = _FakeTypes
sys.modules.setdefault("google", _types.ModuleType("google"))
sys.modules["google.genai"] = _fake_genai
os.environ.setdefault("GOOGLE_API_KEY", "mock-key")

# ── validation_agent 로딩 ─────────────────────────────────────────────────────
_src = open(os.path.join(os.path.dirname(__file__), "validation_agent.py"), encoding="utf-8").read()
_patched = _re.sub(
    r"nb = nbformat\.read.*?SYSTEM_INSTRUCTION = _ns\[.SYSTEM_INSTRUCTION.\]",
    'nb=None\nPERSONAS=[]\nbuild_prompt=lambda p:""\nSYSTEM_INSTRUCTION=""',
    _src, flags=_re.DOTALL,
)
_patched = _patched.replace("if len(sys.argv) > 1:", "if False:")

_va = _types.ModuleType("validation_agent")
_va.__dict__["__builtins__"] = __builtins__
exec(compile(_patched, "validation_agent.py", "exec"), _va.__dict__)

from pathlib import Path as _Path
_cache_path_fn = _va._cache_path

# 임시 캐시 디렉토리 (실제 .genai_cache 오염 방지)
TEST_CACHE = _Path(".test_cache_tmp")
_va._CACHE_DIR = TEST_CACHE

# ── 헬퍼 ─────────────────────────────────────────────────────────────────────
results = []

def check(name, cond, detail=""):
    results.append(cond)
    print(f"  {'✅' if cond else '❌'} {name}")
    if not cond and detail:
        print(f"       {detail}")

def make_resp(payload: dict):
    class _R:
        text = json.dumps(payload, ensure_ascii=False)
    return _R()

PAYLOAD_A = {"status": "OK", "근거": "mock-A"}
PAYLOAD_B = {"status": "NG", "근거": "mock-B"}

# ── 테스트 ────────────────────────────────────────────────────────────────────
print("=" * 60)
print("캐시 로직 스모크 테스트 — 0 API 콜")
print("=" * 60)

try:
    TEST_CACHE.mkdir(exist_ok=True)
    call_log = []

    def mock_gc(model, contents, config):
        call_log.append(contents)
        return make_resp(PAYLOAD_B if "입력B" in str(contents) else PAYLOAD_A)

    # generate_content를 _va.client.models 에 직접 심는다
    _va.client.models.generate_content = mock_gc

    os.environ["GENAI_CACHE"] = "1"
    _va._CACHE_ON = True

    # 1. MISS: 첫 호출
    call_log.clear()
    r1 = _va._gen_json("model-x", "입력A", system="sys", temperature=0.2)
    check("MISS: generate_content 1회 호출", len(call_log) == 1,
          f"호출 횟수={len(call_log)}")
    key_a = os.path.basename(_cache_path_fn("model-x", "입력A", "sys", 0.2))
    cf_a = TEST_CACHE / key_a
    check("MISS: 캐시 파일 생성됨", cf_a.exists(), f"경로={cf_a}")
    check("MISS: 반환값 정확함", r1 == PAYLOAD_A, f"실제={r1}")

    # 2. HIT: 같은 입력 재호출
    call_log.clear()
    r2 = _va._gen_json("model-x", "입력A", system="sys", temperature=0.2)
    check("HIT: generate_content 호출 없음", len(call_log) == 0,
          f"호출 횟수={len(call_log)}")
    check("HIT: 첫 호출과 동일 결과", r2 == r1, f"r1={r1} r2={r2}")

    # 3. 다른 입력: 별도 MISS
    call_log.clear()
    r3 = _va._gen_json("model-x", "입력B", system="sys", temperature=0.2)
    check("다른 입력: generate_content 1회 호출", len(call_log) == 1,
          f"호출 횟수={len(call_log)}")
    check("다른 입력: 다른 결과 반환", r3 == PAYLOAD_B, f"실제={r3}")
    n_files = len(list(TEST_CACHE.glob("*.json")))
    check("다른 입력: 캐시 파일 2개 (A·B 별도 저장)", n_files == 2,
          f"파일 수={n_files}")

    # 4. 캐시 OFF: GENAI_CACHE=0 → 매번 실제 호출
    os.environ["GENAI_CACHE"] = "0"
    _va._CACHE_ON = False
    call_log.clear()
    _va._gen_json("model-x", "입력A", system="sys", temperature=0.2)
    _va._gen_json("model-x", "입력A", system="sys", temperature=0.2)
    check("캐시 OFF: 같은 입력 2회 → generate_content 2회",
          len(call_log) == 2, f"호출 횟수={len(call_log)}")

finally:
    shutil.rmtree(TEST_CACHE, ignore_errors=True)
    os.environ.pop("GENAI_CACHE", None)

print()
print("=" * 60)
tp, tt = sum(results), len(results)
print(f"캐시 스모크: {tp}/{tt} 통과   |   API 호출: 0회")
print("=" * 60)
