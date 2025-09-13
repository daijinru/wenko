"""
A minimal serial workflow engine using Python + Starlette (+ Uvicorn) with pluggable steps.
- Supports a JSON DSL for sequential steps.
- Provides REST endpoints to list steps and run a workflow.
- Includes an example workflow that matches the user's scenario.
- Now integrated with LangGraph to run the same workflow as a LangGraph graph.

Run:
  uvicorn app:app --reload --port 8000

Open demo UI:
  http://127.0.0.1:8000/ui
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, PlainTextResponse
from starlette.routing import Route

# LangGraph integration
from langgraph.graph import StateGraph, END
from typing import TypedDict

# -----------------------------
# Core workflow primitives
# -----------------------------

Context = Dict[str, Any]


class StepError(RuntimeError):
    pass


@dataclass
class Step:
    name: str
    params: Dict[str, Any] = field(default_factory=dict)

    async def run(self, ctx: Context) -> Context:
        raise NotImplementedError

    def get(self, ctx: Context, key: str, default: Any = None) -> Any:
        return ctx.get(key, default)

    def put(self, ctx: Context, key: str, value: Any) -> None:
        ctx[key] = value


# -----------------------------
# Built-in steps
# -----------------------------

class EchoInput(Step):
    async def run(self, ctx: Context) -> Context:
        src = self.params.get("source_key", "input")
        dst = self.params.get("target_key", "echo")
        self.put(ctx, dst, self.get(ctx, src))
        return ctx


class SetVar(Step):
    async def run(self, ctx: Context) -> Context:
        key = self.params["key"]
        if "from_key" in self.params:
            self.put(ctx, key, self.get(ctx, self.params["from_key"]))
        else:
            self.put(ctx, key, self.params.get("value"))
        return ctx


class FetchURL(Step):
    async def run(self, ctx: Context) -> Context:
        url = self.params.get("url") or self.get(ctx, self.params.get("url_key", "url"))
        if not url:
            raise StepError("FetchURL requires url or url_key")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            text = resp.text
        self.put(ctx, self.params.get("target_key", "url_content"), text)
        return ctx


class ParseJSONToDict(Step):
    async def run(self, ctx: Context) -> Context:
        src = self.params.get("source_key", "url_content")
        dst = self.params.get("target_key", "dict")
        raw = self.get(ctx, src)
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise StepError("ParseJSONToDict: JSON root is not dict")
        self.put(ctx, dst, data)
        return ctx


class DictGetAllValues(Step):
    async def run(self, ctx: Context) -> Context:
        dkey = self.params.get("dict_key", "dict")
        dst = self.params.get("target_key", "dict_values")
        data = self.get(ctx, dkey)
        if not isinstance(data, dict):
            raise StepError("DictGetAllValues: not a dict")
        self.put(ctx, dst, list(data.values()))
        return ctx


class SelectFromList(Step):
    async def run(self, ctx: Context) -> Context:
        lkey = self.params["list_key"]
        lst = self.get(ctx, lkey)
        if not isinstance(lst, list):
            raise StepError("SelectFromList: not a list")
        idx = self.params.get("index", 0)
        self.put(ctx, self.params.get("target_key", "selected"), lst[idx])
        return ctx


class DictGetValue(Step):
    async def run(self, ctx: Context) -> Context:
        dk = self.params.get("dict_key", "dict")
        data = self.get(ctx, dk)
        if not isinstance(data, dict):
            raise StepError("DictGetValue: not a dict")
        key = self.params.get("key")
        if key is None:
            key = self.get(ctx, self.params.get("key_key", "selected"))
        self.put(ctx, self.params.get("target_key", "dict_value"), data[key])
        return ctx


class ReplaceTemplatePlaceholders(Step):
    async def run(self, ctx: Context) -> Context:
        src = self.params["source_key"]
        raw = self.get(ctx, src)
        result = str(raw)
        repl: Dict[str, str] = self.params.get("replacements", {})
        for placeholder, ctx_key in repl.items():
            val = self.get(ctx, ctx_key)
            result = result.replace(placeholder, str(val))
        self.put(ctx, self.params.get("target_key", src), result)
        return ctx


class CustomPythonFunction(Step):
    async def run(self, ctx: Context) -> Context:
        src = self.params["source_key"]
        dst = self.params["target_key"]
        func_name = self.params["function"]
        if func_name not in CUSTOM_FUNCS:
            raise StepError(f"Custom function {func_name} not registered")
        fn = CUSTOM_FUNCS[func_name]
        self.put(ctx, dst, fn(self.get(ctx, src)))
        return ctx


class MergeTexts(Step):
    async def run(self, ctx: Context) -> Context:
        parts = self.params.get("parts", [])
        sep = self.params.get("sep", "")
        rendered: List[str] = []
        for p in parts:
            if "literal" in p:
                rendered.append(str(p["literal"]))
            elif "key" in p:
                rendered.append(str(self.get(ctx, p["key"], "")))
        out = sep.join(rendered)
        self.put(ctx, self.params.get("target_key", "merged"), out)
        return ctx


class ReplaceNewlinesWithWord(Step):
    async def run(self, ctx: Context) -> Context:
        src = self.params["source_key"]
        word = self.params.get("word", "世界")
        txt = str(self.get(ctx, src, ""))
        result = txt.replace("\n", word)
        self.put(ctx, self.params.get("target_key", src), result)
        return ctx


# -----------------------------
# Step registry & runner
# -----------------------------

STEP_REGISTRY: Dict[str, Callable[[str, Dict[str, Any]], Step]] = {}


def register_step(cls):
    STEP_REGISTRY[cls.__name__] = lambda name, params: cls(name=name, params=params)
    return cls


for _cls in [
    EchoInput,
    SetVar,
    FetchURL,
    ParseJSONToDict,
    DictGetAllValues,
    SelectFromList,
    DictGetValue,
    ReplaceTemplatePlaceholders,
    CustomPythonFunction,
    MergeTexts,
    ReplaceNewlinesWithWord,
]:
    register_step(_cls)


@dataclass
class Workflow:
    name: str
    steps: List[Step]

    @classmethod
    def from_dsl(cls, dsl: Dict[str, Any]) -> "Workflow":
        steps: List[Step] = []
        for i, s in enumerate(dsl.get("steps", [])):
            stype = s["type"]
            name = s.get("name", f"step_{i}_{stype}")
            params = s.get("params", {})
            if stype not in STEP_REGISTRY:
                raise StepError(f"Unknown step type: {stype}")
            steps.append(STEP_REGISTRY[stype](name, params))
        return cls(name=dsl.get("name", "workflow"), steps=steps)

    async def run(self, ctx: Optional[Context] = None) -> Context:
        ctx = ctx or {}
        for step in self.steps:
            ctx = await step.run(ctx)
        return ctx


# -----------------------------
# Custom function registry
# -----------------------------

CUSTOM_FUNCS: Dict[str, Callable[[Any], Any]] = {}


def custom_func(name: str):
    def _wrap(fn: Callable[[Any], Any]):
        CUSTOM_FUNCS[name] = fn
        return fn
    return _wrap


@custom_func("strip_and_upper")
def strip_and_upper(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip().upper()


# -----------------------------
# LangGraph integration
# -----------------------------

class WorkflowState(TypedDict, total=False):
    context: dict

def step_to_node(step: Step):
    async def node_fn(state: WorkflowState) -> WorkflowState:
        ctx = state.get("context", {})
        new_ctx = await step.run(ctx)
        return {"context": new_ctx}
    return node_fn

def build_langgraph(workflow: Workflow):
    g = StateGraph(WorkflowState)
    prev = None
    for step in workflow.steps:
        node_name = step.name
        g.add_node(node_name, step_to_node(step))
        if prev is not None:
            g.add_edge(prev, node_name)
        prev = node_name
    if prev:
        g.add_edge(prev, END)
    return g.compile()


# -----------------------------
# Starlette app & endpoints
# -----------------------------

app = Starlette(debug=True)


@app.route("/steps", methods=["GET"])
async def list_steps(request: Request):
    return JSONResponse({"registered_steps": sorted(STEP_REGISTRY.keys())})


@app.route("/workflows/run", methods=["POST"])
async def run_workflow(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    dsl = payload.get("workflow")
    context = payload.get("context", {})
    if not dsl:
        return JSONResponse({"error": "Missing `workflow`"}, status_code=400)

    try:
        wf = Workflow.from_dsl(dsl)
        result_ctx = await wf.run(context)
    except StepError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"Unhandled: {e}"}, status_code=500)
    return JSONResponse({"workflow": wf.name, "context": result_ctx})


@app.route("/workflows/run_langgraph", methods=["POST"])
async def run_workflow_langgraph(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    dsl = payload.get("workflow")
    context = payload.get("context", {})
    if not dsl:
        return JSONResponse({"error": "Missing `workflow`"}, status_code=400)

    try:
        wf = Workflow.from_dsl(dsl)
        graph = build_langgraph(wf)
        result = await graph.ainvoke({"context": context})
    except StepError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"Unhandled: {e}"}, status_code=500)
    return JSONResponse({"workflow": wf.name, "context": result["context"]})


@app.route("/ui", methods=["GET"])
async def ui(_: Request):
    return HTMLResponse("""
<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <title>Workflow Demo</title>
  </head>
  <body>
    <h1>串行 Workflow 引擎 Demo</h1>
    <textarea id=\"input\">你好，这是用户输入。</textarea>
    <input id=\"url\" value=\"https://httpbin.org/json\" />
    <button id=\"run\">运行 (内置)</button>
    <button id=\"runlg\">运行 (LangGraph)</button>
    <pre id=\"out\"></pre>
    <script>
      const EXAMPLE_WORKFLOW = {
        name: 'serial_demo',
        steps: [
          { type: 'EchoInput', params: { source_key: 'input', target_key: 'shown_input' } },
          { type: 'SetVar', params: { key: 'service', from_key: 'input' } },
          { type: 'FetchURL', params: { url_key: 'url', target_key: 'url_content' } },
          { type: 'ParseJSONToDict', params: { source_key: 'url_content', target_key: 'dict' } },
          { type: 'DictGetAllValues', params: { dict_key: 'dict', target_key: 'dict_values' } },
          { type: 'SelectFromList', params: { list_key: 'dict_values', index: 0, target_key: 'selected_value' } },
          { type: 'DictGetValue', params: { dict_key: 'dict', key_key: 'selected_value', target_key: 'selected_item_value' } },
          { type: 'ReplaceTemplatePlaceholders', params: { source_key: 'selected_item_value', replacements: { '[[INPUT]]': 'input' }, target_key: 'templated' }},
          { type: 'CustomPythonFunction', params: { source_key: 'templated', target_key: 'customized', function: 'strip_and_upper' }},
          { type: 'MergeTexts', params: { parts: [ {key: 'shown_input'}, {literal: ' | '}, {key: 'customized'} ], target_key: 'merged_text' }},
          { type: 'ReplaceNewlinesWithWord', params: { source_key: 'merged_text', word: '世界', target_key: 'final_text' }}
        ]
      };
      async function run(url) {
        const body = { context: { input: document.getElementById('input').value, url: document.getElementById('url').value }, workflow: EXAMPLE_WORKFLOW };
        const res = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
        const data = await res.json();
        document.getElementById('out').textContent = JSON.stringify(data, null, 2);
      }
      document.getElementById('run').addEventListener('click', () => run('/workflows/run'));
      document.getElementById('runlg').addEventListener('click', () => run('/workflows/run_langgraph'));
    </script>
  </body>
</html>
""")


@app.route("/health", methods=["GET"])
async def health(_: Request):
    return PlainTextResponse("ok")
