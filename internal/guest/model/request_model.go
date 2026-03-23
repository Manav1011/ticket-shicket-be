package model

// GuestRegisterRequest is the body for POST /guests/register
type GuestRegisterRequest struct {
	UserAgent string `json:"user_agent" binding:"required"`
	IpAddress string `json:"ip_address" binding:"required"`
}

type GuestRefreshRequest struct {
	RefreshToken string `json:"refresh_token" binding:"required"`
}
