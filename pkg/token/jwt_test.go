package token

import (
	"strings"
	"testing"
)

func TestGenerateAccessTokenForGuest(t *testing.T) {
	guestID := "550e8400-e29b-41d4-a716-446655440000"
	token, err := GenerateAccessTokenGuest(guestID)
	if err != nil {
		t.Fatalf("GenerateAccessTokenGuest failed: %v", err)
	}
	if token == "" {
		t.Fatal("Expected token, got empty string")
	}
	if !strings.HasPrefix(token, "eyJ") {
		t.Fatal("Invalid JWT format")
	}

	claims, err := ParseToken(token)
	if err != nil {
		t.Fatalf("ParseToken failed: %v", err)
	}
	if claims["guest_id"] != guestID {
		t.Fatalf("Expected guest_id %s, got %v", guestID, claims["guest_id"])
	}
	if claims["type"] != "access" {
		t.Fatalf("Expected type 'access', got %v", claims["type"])
	}
}

func TestGenerateRefreshTokenForGuest(t *testing.T) {
	guestID := "550e8400-e29b-41d4-a716-446655440000"
	token, err := GenerateRefreshTokenGuest(guestID)
	if err != nil {
		t.Fatalf("GenerateRefreshTokenGuest failed: %v", err)
	}
	if token == "" {
		t.Fatal("Expected token, got empty string")
	}

	claims, err := ParseToken(token)
	if err != nil {
		t.Fatalf("ParseToken failed: %v", err)
	}
	if claims["guest_id"] != guestID {
		t.Fatalf("Expected guest_id %s, got %v", guestID, claims["guest_id"])
	}
	if claims["type"] != "refresh" {
		t.Fatalf("Expected type 'refresh', got %v", claims["type"])
	}
}

func TestGenerateRefreshTokenIsUniqueForSameUser(t *testing.T) {
	userID := "63bdcfa3-5b91-4fd9-a870-8d4a86528ee3"
	t1, err := GenerateRefreshToken(userID)
	if err != nil {
		t.Fatalf("first token error: %v", err)
	}
	t2, err := GenerateRefreshToken(userID)
	if err != nil {
		t.Fatalf("second token error: %v", err)
	}
	if t1 == t2 {
		t.Fatal("expected different refresh tokens for same user")
	}
}

func TestGenerateRefreshTokenIsUniqueForSameGuest(t *testing.T) {
	guestID := "550e8400-e29b-41d4-a716-446655440000"
	t1, err := GenerateRefreshTokenGuest(guestID)
	if err != nil {
		t.Fatalf("first token error: %v", err)
	}
	t2, err := GenerateRefreshTokenGuest(guestID)
	if err != nil {
		t.Fatalf("second token error: %v", err)
	}
	if t1 == t2 {
		t.Fatal("expected different refresh tokens for same guest")
	}
}

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
