package token

import (
	"testing"
)

func TestGenerateAccessToken(t *testing.T) {
	userID := "test-user-123"
	token, err := GenerateAccessToken(userID)
	t.Log(token)
	if err != nil {
		t.Fatalf("Failed to generate token: %v", err)
	}

	if token == "" {
		t.Error("Token should not be empty")
	}
}

func TestParseToken(t *testing.T) {
	userID := "63bdcfa3-5b91-4fd9-a870-8d4a86528ee3"
	token, _ := GenerateAccessToken(userID)

	claims, err := ParseToken(token)
	t.Log(claims)
	if err != nil {
		t.Fatalf("Failed to parse token: %v", err)
	}

	if claims["user_id"] != userID {
		t.Errorf("Expected user_id %s, got %v", userID, claims["user_id"])
	}

	if claims["type"] != "access" {
		t.Error("Token type should be 'access'")
	}
}

func TestParseInvalidToken(t *testing.T) {
	_, err := ParseToken("invalid-token-string")
	t.Log(err)
	if err == nil {
		t.Error("Should return error for invalid token")
	}
}
