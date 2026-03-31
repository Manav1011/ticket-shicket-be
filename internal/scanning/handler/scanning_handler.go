package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/manav1011/ticket-shicket-be/internal/scanning/model"
	"github.com/manav1011/ticket-shicket-be/internal/scanning/service"
	"github.com/manav1011/ticket-shicket-be/pkg/utils"
)

type ScanningHandler struct {
	svc *service.ScanningService
}

func NewScanningHandler(svc *service.ScanningService) *ScanningHandler {
	return &ScanningHandler{svc: svc}
}

// ScanQRCode validates and marks a QR code as used
// @Summary      Scan QR code
// @Description  Validates and marks a QR code as used
// @Tags         scanning
// @Accept       json
// @Produce      json
// @Param        body  body      model.ScanningRequest  true  "QR code payload"
// @Success      200   {object}  model.ScanningResponse
// @Failure      400   {object}  utils.APIResponse
// @Failure      500   {object}  utils.APIResponse
// @Router       /scanning/scan [post]
func (h *ScanningHandler) ScanQRCode(c *gin.Context) {
	var req model.ScanningRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Error(c, "invalid request body", http.StatusBadRequest)
		return
	}
	valid, err := h.svc.ValidateQRCode(c.Request.Context(), req.QRCodePayload)
	if err != nil {
		utils.Error(c, "internal server error", http.StatusInternalServerError)
		return
	}
	resp := model.ScanningResponse{
		Valid:   valid,
		Message: "",
	}
	if !valid {
		resp.Message = "Invalid or already used QR code"
		utils.Error(c, resp.Message, http.StatusBadRequest)
		return
	}
	utils.Success(c, resp)
}
