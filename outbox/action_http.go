package outbox

import "net/http"

func NewActionHttp() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {

	}
}
