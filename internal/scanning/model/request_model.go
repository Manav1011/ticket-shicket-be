package model

// ScanningRequest Model

type ScanningRequest struct {
	QRCodePayload string `json:"qr_code_payload" validate:"required"`
}
