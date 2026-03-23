package handler

import (
"testing"
)

func TestNewGuestHandler(t *testing.T) {
	handler := NewGuestHandler(nil)
	if handler == nil {
		t.Fatal("Expected handler to be initialized")
	}
}
