package guest

import (
	"github.com/gin-gonic/gin"
	"github.com/manav1011/ticket-shicket-be/internal/guest/handler"
)

// RegisterRoutes mounts guest routes under the given API group (e.g. /v1 from main).
// Paths are relative to that group: /guests/register, not /v1/guests/register here.
func RegisterRoutes(v1 *gin.RouterGroup, h *handler.GuestHandler) {
	guests := v1.Group("/guests")
	guests.POST("/register", h.Register)
	guests.POST("/refresh", h.Refresh)
}
