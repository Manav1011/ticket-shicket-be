package model

import "github.com/google/uuid"

// GuestRegisterData is returned on successful guest registration
type GuestRegisterData struct {
	AccessToken  string    `json:"access_token"`
	RefreshToken string    `json:"refresh_token"`
	TokenType    string    `json:"token_type"`
	ExpiresIn    int64     `json:"expires_in"`
	Guest        GuestInfo `json:"guest"`
}

// GuestInfo is a minimal guest projection for auth responses
type GuestInfo struct {
	ID        uuid.UUID `json:"id"`
	Slug      uuid.UUID `json:"slug"`
	CreatedAt int64     `json:"created_at"`
}

// GuestRegisterSuccessEnvelope is the JSON shape for Swagger/OpenAPI
type GuestRegisterSuccessEnvelope struct {
	Success bool              `json:"success"`
	Data    GuestRegisterData `json:"data"`
}

type GuestRefreshSuccessEnvelope struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	TokenType    string `json:"token_type"`
	ExpiresIn    int64  `json:"expires_in"`
}
