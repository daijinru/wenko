## Action

Plan: plan_mode_respond
> SSE: ask (Writer <-> Client)
> API: response (Client -> Writer)

Action: ask
> SSE: Writer -> Client

Action: tool_use
> SSE: Writer -> Client

Action: response
> API: Client -> Writer
