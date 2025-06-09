package outbox

type PayloadType struct {
	Content string                 `json:"content"`
	Meta    map[string]interface{} `json:"meta"`
}

type MessageType struct {
	Type     string      `json:"type"`
	Payload  PayloadType `json:"payload"`
	ActionID string      `json:"actionID"`
}

// 会话
type Session struct {
	sessionIDMap map[string][]MessageType
}

func NewSession() *Session {
	return &Session{
		sessionIDMap: make(map[string][]MessageType),
	}
}
func (s *Session) AddEntry(sessionID string, entry MessageType) {
	s.sessionIDMap[sessionID] = append(s.sessionIDMap[sessionID], entry)
}

func (s *Session) GetEntries(sessionID string) ([]MessageType, bool) {
	entries, exists := s.sessionIDMap[sessionID]
	return entries, exists
}

func (s *Session) DeleteEntries(sessionID string) {
	delete(s.sessionIDMap, sessionID)
}
