package scanning

import (
	"github.com/gin-gonic/gin"
	"github.com/manav1011/ticket-shicket-be/internal/scanning/handler"
)

func RegisterRoutes(rg *gin.RouterGroup, h *handler.ScanningHandler) {
	rg.POST("/scanning/scan", h.ScanQRCode)
}
