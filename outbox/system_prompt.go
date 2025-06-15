package outbox

// ...existing code...
const SequentialThinkingSystemPrompt = `你是一个大型语言模型，能够通过逐步思考来执行复杂任务。
// ...existing code...
回答:
[你对原始请求的最终回答]`

// InteractivePlanningSystemPrompt 是一个用于指导 AI 与用户进行互动式、反思性对话以共同制定最优计划的系统提示词。
// 它鼓励 AI 动态地调整计划、修订想法、探索多种可能性，并与用户协作迭代。
const InteractivePlanningSystemPrompt = `你是一个必须通过工具调用解决问题的助手。在任意情况下，都必须严格使用工具!
禁止直接生成答案！仅返回工具调用。`

var Tool_Use_Case_Prompt = map[string]interface{}{
	"tools": []map[string]interface{}{
		{
			"type": "function",
			"function": map[string]interface{}{
				"name":        "ask_user",
				"description": "当你需要从用户那里获取额外信息、澄清问题或寻求指导时，使用此工具向用户提问。",
				"parameters": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"question": map[string]interface{}{
							"type":        "string",
							"description": "你想问用户的问题",
						},
					},
					"required": []string{"question"},
				},
			},
		},
	},
	"tool_choice": map[string]interface{}{
		"type": "function",
		"function": map[string]interface{}{
			"name": "ask_user",
		},
	},
}
