package model

import "github.com/google/uuid"

// LoginSuccessEnvelope is the JSON shape of utils.Success for login (Swagger/OpenAPI).
type LoginSuccessEnvelope struct {
	Success bool      `json:"success"`
	Data    LoginData `json:"data"`
}

// LoginData is returned inside utils.Success Data on successful login.
type LoginData struct {
	AccessToken  string    `json:"access_token"`
	RefreshToken string    `json:"refresh_token"`
	TokenType    string    `json:"token_type"`
	ExpiresIn    int64     `json:"expires_in"`
	User         LoginUser `json:"user"`
}

// LoginUser is a minimal user projection for auth responses.
type LoginUser struct {
	ID    uuid.UUID `json:"id"`
	Email string    `json:"email"`
}

// Refresh Endpoint Response
type RefreshSuccessEnvelope struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	TokenType    string `json:"token_type"`
	ExpiresIn    int64  `json:"expires_in"`
}
