package outbox

// 会话
type Session struct {
	sessionIDMap map[string][]struct {
		Type     string
		Payload  string
		ActionID string
	}
}

func NewSession() *Session {
	return &Session{
		sessionIDMap: make(map[string][]struct {
			Type     string
			Payload  string
			ActionID string
		}),
	}
}
func (s *Session) AddEntry(sessionID string, entry struct {
	Type     string
	Payload  string
	ActionID string
}) {
	s.sessionIDMap[sessionID] = append(s.sessionIDMap[sessionID], entry)
}

func (s *Session) GetEntries(sessionID string) ([]struct {
	Type     string
	Payload  string
	ActionID string
}, bool) {
	entries, exists := s.sessionIDMap[sessionID]
	return entries, exists
}

func (s *Session) DeleteEntries(sessionID string) {
	delete(s.sessionIDMap, sessionID)
}
