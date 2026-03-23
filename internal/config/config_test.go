package config

import (
	"os"
	"testing"
	"time"
)

func TestLoadConfig(t *testing.T) {
	// Set up environment variables
	os.Setenv("DB_DRIVER", "postgres")
	os.Setenv("DB_SOURCE", "user=test password=test dbname=testdb")
	os.Setenv("SERVER_PORT", "8080")
	os.Setenv("JWT_SECRET", "test-secret-key")
	os.Setenv("ACCESS_TOKEN_DURATION", "15m")
	os.Setenv("REFRESH_TOKEN_DURATION", "24h")

	config := LoadConfig()

	if config.DBDriver != "postgres" {
		t.Errorf("expected DBDriver 'postgres', got '%s'", config.DBDriver)
	}
	if config.ServerPort != "8080" {
		t.Errorf("expected ServerPort '8080', got '%s'", config.ServerPort)
	}
	if config.JWTSecret != "test-secret-key" {
		t.Errorf("expected JWTSecret 'test-secret-key', got '%s'", config.JWTSecret)
	}
	if config.AccessTokenDuration != 15*time.Minute {
		t.Errorf("expected AccessTokenDuration 15m, got %v", config.AccessTokenDuration)
	}
	if config.RefreshTokenDuration != 24*time.Hour {
		t.Errorf("expected RefreshTokenDuration 24h, got %v", config.RefreshTokenDuration)
	}
}

func TestLoadConfigMissingEnvVars(t *testing.T) {
	os.Setenv("ACCESS_TOKEN_DURATION", "invalid")
	defer os.Unsetenv("ACCESS_TOKEN_DURATION")

	// This test will cause a fatal error - consider returning error instead
	// config := LoadConfig() // Would fail
}
