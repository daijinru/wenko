package outbox

import (
	"bufio"
	"bytes"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

const (
	SIGNAL_STOP = "stop"
)

var (
	globalSession  *Session
	FlusherWriter  http.Flusher
	ResponseWriter http.ResponseWriter

	id int = 0 // 初始化 0

	ModelProviderURI    string
	ModelProviderModel  string
	ModelProviderAPIKey string
)

func InitGlobalSession() {
	globalSession = NewSession()
}

func InitModelProvider(providerURI string, providerModel string, providerAPIKey string) {
	ModelProviderURI = providerURI
	ModelProviderModel = providerModel
	ModelProviderAPIKey = providerAPIKey
}

type OutMessage struct {
	Type     string `json:"type"`
	Payload  string `json:"payload"`
	ActionID string `json:"actionID"`
}

func GenerateUUID() string {
	u := make([]byte, 16)
	_, err := rand.Read(u)
	if err != nil {
		return ""
	}
	// 设置版本 (4) 和变体 (RFC4122)
	u[6] = (u[6] & 0x0f) | 0x40
	u[8] = (u[8] & 0x3f) | 0x80

	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		u[0:4],
		u[4:6],
		u[6:8],
		u[8:10],
		u[10:16])
}

func waitUntil(timeout time.Duration, codition func() bool) {
	start := time.Now()
	for {
		fmt.Println("等待中...")
		out := codition()
		if out {
			return
		}
		if time.Since(start) > timeout {
			return
		}
		time.Sleep(2000 * time.Millisecond)
	}
}

func PrintOut(eventType string, data string) {
	fmt.Fprintf(ResponseWriter, "id: %d\n", id)
	fmt.Fprintf(ResponseWriter, "event: %s\n", eventType)
	fmt.Fprintf(ResponseWriter, "data: %s\n\n", data)
	FlusherWriter.Flush()
	id++
}

type StopReason struct {
	Type    string `json:"type"`
	Payload string `json:"payload"`
}

var (
	maxOuterLoop     = 3 // 外层最大循环次数
	maxInnerLoop     = 2 // 内层最大循环次数
	currentLoop      = 0 // 当前循环计数器（可被重置）
	currentInnerLoop = 0 // 当前内层循环计数器（可被重置）
)

func NewTask(w http.ResponseWriter, r *http.Request) {

	fmt.Println("创建新任务...")
	id = 0 // 重置 id
	// 从 body 中读取请求体
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "读取请求体失败", http.StatusBadRequest)
	}
	// 解析请求体，取出 text
	var ChatRequest struct {
		Text string `json:"text"`
	}
	if err := json.Unmarshal(body, &ChatRequest); err != nil {
		http.Error(w, "解析请求体失败", http.StatusBadRequest)
	}
	// 每个新任务都覆盖全局会话，暂时支持单任务
	ResponseWriter = w
	// 添加 text/event-stream 响应头
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	flusher, ok := w.(http.Flusher)
	FlusherWriter = flusher
	if !ok {
		http.Error(w, "Streaming 不支持", http.StatusInternalServerError)
	}

	// data := OutMessage{
	// 	Type:     "text",
	// 	Payload:  "连接成功，请稍后",
	// 	ActionID: "",
	// }
	// dataBytes, _ := json.Marshal(data)
	// PrintOut("200", string(dataBytes))

	// taskDone := false
	breakDone := false
	doneMessage := ""

	// !重置内外循环计数器
	currentLoop = 0
	currentInnerLoop = 0

	for {
		fmt.Println("当前循环次数: ", currentLoop)

		if ok := CheckInterrupt(); ok {
			data := OutMessage{
				Type:     "statusText",
				Payload:  "任务中断: 用户中断",
				ActionID: "",
			}
			dataBytes, _ := json.Marshal(data)
			PrintOut("200", string(dataBytes))
			break
		}

		if currentLoop >= maxOuterLoop {
			data := OutMessage{
				Type:     "statusText",
				Payload:  "任务中断: 最大循环数",
				ActionID: "",
			}
			dataBytes, _ := json.Marshal(data)
			PrintOut("200", string(dataBytes))
			break
		}

		if breakDone {
			data := OutMessage{
				Type:     "statusText",
				Payload:  doneMessage,
				ActionID: "",
			}
			dataBytes, _ := json.Marshal(data)
			PrintOut("200", string(dataBytes))
			break
		}

		// 执行用于任务计划的递归函数
		planningTaskCompletion := recursivePlanningTask(ChatRequest.Text)
		fmt.Println("planningIsEnd: ", planningTaskCompletion)
		// 如果 planningIsEnd 为 true，则退出循环
		if planningTaskCompletion.Break {
			breakDone = true
			doneMessage = planningTaskCompletion.Text
		}
		if planningTaskCompletion.Done {
			breakDone = true
			doneMessage = planningTaskCompletion.Text
		}
		currentLoop++
	}
}

type ProviderStreamResponse struct {
	Choices []struct {
		Delta struct {
			Content   string `json:"content"`
			ToolCalls []struct {
				Function struct {
					Arguments string `json:"arguments"`
					Name      string `json:"name"`
				} `json:"function"`
			} `json:"tool_calls"`
		} `json:"delta"`
	} `json:"choices"`
}

type RecursiveTaskCompletion struct {
	Text  string `json:"text"`
	Done  bool   `json:"done"`
	Break bool   `json:"break"`
}

func recursivePlanningTask(text string) RecursiveTaskCompletion {
	// 限制内层循环
	if currentInnerLoop >= maxInnerLoop {
		return RecursiveTaskCompletion{
			Text:  "任务中断: 最大内层循环数",
			Break: true,
		}
	}

	if ok := CheckInterrupt(); ok {
		return RecursiveTaskCompletion{
			Text:  "任务中断: 用户中断",
			Break: true,
		}
	}

	modelRequestBody, err := json.Marshal(map[string]interface{}{
		"model": ModelProviderModel,
		// 创建 system 和 user 角色的消息
		"messages": []map[string]string{
			{
				"role":    "system",
				"content": InteractivePlanningSystemPrompt,
			},
			{
				"role":    "user",
				"content": text,
			},
		},
		"stream":      true,
		"temperature": 0,
		// 需大模型支持 tool call
		"tools":       Tool_Use_Case_Prompt["tools"],
		"tool_choice": Tool_Use_Case_Prompt["tool_choice"],
	})
	if err != nil {
		fmt.Println("创建请求体失败: ", err)
		return RecursiveTaskCompletion{
			Text:  "创建请求体失败: " + err.Error(),
			Break: true,
		}
	}
	fmt.Println("🌍 大模型请求体: ", string(modelRequestBody), "\n\n", "大模型请求地址: ", ModelProviderURI, "\n\n", "")
	// Planning Task: 请求 openrouter 并传入 InteractivePlanningSystemPrompt
	// 将返回的内容写入会话
	req, _ := http.NewRequest("POST", ModelProviderURI, bytes.NewBuffer(modelRequestBody))
	req.Header.Set("Authorization", "Bearer "+ModelProviderAPIKey)
	req.Header.Set("Content-Type", "application/json")

	// 发送请求
	// 将返回的内容写入会话
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		// http.Error(ResponseWriter, "调用大模型失败: "+err.Error(), http.StatusInternalServerError)
		return RecursiveTaskCompletion{
			Text:  "调用大模型失败: " + err.Error(),
			Break: true,
		}
	}
	defer resp.Body.Close()

	// 存储工具调用信息的变量
	toolCallDetected := false
	var toolCallArguments strings.Builder

	// 为本次消息创建一个唯一ID
	textMessageID := GenerateUUID()
	// 流式返回
	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		// 在流式输出找到中断信号
		// if ok := CheckInterrupt(); ok {
		// 	return RecursiveTaskCompletion{
		// 		Text: "任务中断: 用户中断",
		// 		Break: true,
		// 	}
		// }

		line := scanner.Text()
		// fmt.Println("line: ", line)
		if len(line) > 6 && line[:6] == "data: " {
			data := line[6:]
			if data == "[DONE]" {
				break
			}
			var orResp ProviderStreamResponse
			if err := json.Unmarshal([]byte(data), &orResp); err == nil {
				if len(orResp.Choices) > 0 {
					content := orResp.Choices[0].Delta.Content
					if content != "" && content != "\n" {
						payload := MessageType{
							Type: "text",
							Payload: PayloadType{
								Content: content,
								Meta: map[string]interface{}{
									"id": textMessageID,
								},
							},
						}
						payloadStr, _ := json.Marshal(payload)
						data := OutMessage{
							Type:     "text",
							Payload:  string(payloadStr),
							ActionID: "",
						}
						dataBytes, _ := json.Marshal(data)
						PrintOut("200", string(dataBytes))
					}
					// fmt.Println("><检测工具调用", orResp.Choices[0].Delta.ToolCalls)
					// 累加工具调用参数
					if len(orResp.Choices[0].Delta.ToolCalls) > 0 {
						fmt.Println("><检测到工具调用", orResp.Choices[0].Delta.ToolCalls[0].Function.Arguments)
						toolCallDetected = true
						toolCallArguments.WriteString(orResp.Choices[0].Delta.ToolCalls[0].Function.Arguments)
					}
				}
			}
		}
	}

	if !toolCallDetected {
		return RecursiveTaskCompletion{
			Text: "没有检测到工具调用 --> 对话结束",
			Done: true,
		}
	}

	var toolArgs struct {
		Question string `json:"question"`
	}
	if err := json.Unmarshal([]byte(toolCallArguments.String()), &toolArgs); err != nil {
		return RecursiveTaskCompletion{
			Text:  "解析工具参数失败: " + err.Error(),
			Break: true,
		}
	}

	// 将工具调用参数写入会话
	// 添加一个 ask 消息
	actionID := GenerateUUID()
	payload := MessageType{
		Type: "ask",
		Payload: PayloadType{
			Content: toolArgs.Question,
			Meta: map[string]interface{}{
				"answer": false,
				"reason": "",
				"id":     actionID,
			},
		},
		ActionID: actionID,
	}
	payloadStr, _ := json.Marshal(payload)
	data := OutMessage{
		Type:     "text",
		Payload:  string(payloadStr),
		ActionID: actionID,
	}
	dataBytes, _ := json.Marshal(data)
	PrintOut("200", string(dataBytes))
	globalSession.AddEntry("ask", payload)

	lastEntry := MessageType{}
	waitUntil(60*time.Second, func() bool {
		if ok := CheckInterrupt(); ok {
			return true
		}

		entries, exists := globalSession.GetEntries("ask")
		if !exists || len(entries) == 0 {
			return false
		}

		for i := len(entries) - 1; i >= 0; i-- {
			if entries[i].ActionID == actionID {
				entry := entries[i]
				fmt.Println("waiting entry: ", entry.ActionID)
				// 仅当 answer 为 true 时才返回 true
				if answer, ok := entry.Payload.Meta["answer"].(bool); ok && answer {
					lastEntry = entry
					return true
				}
				return false
			}
		}

		return false
	})

	// 如果 lastEntry.Type 为空说明超时
	if lastEntry.Type == "" {
		return RecursiveTaskCompletion{
			Text:  "回答超时",
			Break: true,
		}
	}
	// 如果 answer 为 true 且 reason 为空，说明用户同意，可继续
	if lastEntry.Payload.Meta["answer"] == true && lastEntry.Payload.Meta["reason"] == "" {
		return RecursiveTaskCompletion{
			Text:  "用户取消",
			Break: true,
		}
	}
	reason := lastEntry.Payload.Meta["reason"].(string)
	currentInnerLoop++
	return recursivePlanningTask(reason)
}

func PlanningTaskAnswer(w http.ResponseWriter, r *http.Request) {
	// 从 body 中读取请求体
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "读取请求体失败", http.StatusBadRequest)
		return
	}
	// 解析请求体，取出 text
	var ChatRequest struct {
		Text     string `json:"text"`
		ActionID string `json:"actionID"`
	}
	if err := json.Unmarshal(body, &ChatRequest); err != nil {
		http.Error(w, "解析请求体失败", http.StatusBadRequest)
		return
	}

	entries, _ := globalSession.GetEntries("ask")
	// fmt.Println("entries: ", entries)
	if (entries == nil) || (len(entries) == 0) {
		http.Error(w, "没有找到相应的 ask 消息", http.StatusBadRequest)
	} else {
		lastEntry := entries[len(entries)-1]

		askMessage := MessageType{
			Type: "ask",
			Payload: PayloadType{
				Content: lastEntry.Payload.Content,
				Meta: map[string]interface{}{
					"answer": true,
					"reason": ChatRequest.Text,
				},
			},
			ActionID: ChatRequest.ActionID,
		}
		globalSession.AddEntry("ask", askMessage)
	}
}

// 客户端发起中断信号
func InterruptTask(w http.ResponseWriter, r *http.Request) {
	askMessage := MessageType{
		Type: "signal",
		Payload: PayloadType{
			Content: "",
			Meta: map[string]interface{}{
				"action": SIGNAL_STOP,
			},
		},
		ActionID: "",
	}
	globalSession.AddEntry("ask", askMessage)
	// 返回 200
	w.WriteHeader(http.StatusOK)
	// 返回 json
	w.Header().Set("Content-Type", "application/json")
	response := map[string]string{
		"message": "中断信号已发送",
		"status":  "200",
	}
	json.NewEncoder(w).Encode(response)
}

// 执行后从最新一条信息检查 signal 类型的消息，如果有则中断
func CheckInterrupt() bool {
	entries, _ := globalSession.GetEntries("ask")
	if (entries == nil) || (len(entries) == 0) {
		return false
	}

	lastEntry := entries[len(entries)-1]
	if lastEntry.Type == "signal" {
		if action, ok := lastEntry.Payload.Meta["action"].(string); ok && action == SIGNAL_STOP {
			// 删除该消息
			globalSession.DeleteLastEntry("ask")
			return true
		}
	}
	return false
}
