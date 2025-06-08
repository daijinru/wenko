package outbox

import (
	"bufio"
	"bytes"
	"encoding/xml"
	"fmt"
	"strings"
)

type ToolUse struct {
	XMLName     xml.Name `xml:"tool_use"`
	Params      string   `xml:"params"`
	ToolUseName string   `xml:"tool_use_name"`
}

func processSSEStream(stream string) {
	scanner := bufio.NewScanner(strings.NewReader(stream))
	var eventData bytes.Buffer
	var inEvent bool

	for scanner.Scan() {
		line := scanner.Text()

		if strings.HasPrefix(line, "data: ") {
			inEvent = true
			eventData.WriteString(strings.TrimPrefix(line, "data: "))
		} else if line == "" && inEvent {
			// 空行表示事件结束
			processEventData(eventData.String())
			eventData.Reset()
			inEvent = false
		} else if inEvent {
			eventData.WriteString(line)
		}
	}
}

func processEventData(data string) {
	if strings.Contains(data, "<tool_use>") {
		var tool ToolUse
		err := xml.Unmarshal([]byte(data), &tool)
		if err != nil {
			fmt.Println("Error parsing tool_use:", err)
			return
		}

		fmt.Println("Parsed Tool Use:")
		fmt.Println("Params:", tool.Params)
		fmt.Println("Tool Name:", tool.ToolUseName)
	}
}
