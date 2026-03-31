package model

// ScanningResponse Model

type ScanningResponse struct {
	Valid   bool   `json:"valid"`
	Message string `json:"message,omitempty"`
}
