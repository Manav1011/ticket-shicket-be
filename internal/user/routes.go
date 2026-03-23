package user

import (
	"github.com/gin-gonic/gin"
	"github.com/manav1011/ticket-shicket-be/internal/user/handler"
)

// RegisterRoutes mounts user routes under the given API group (e.g. /v1 from main).
// Paths are relative to that group: /users/login, not /v1/users/login here.
func RegisterRoutes(v1 *gin.RouterGroup, h *handler.UserHandler) {
	users := v1.Group("/users")
	users.POST("/login", h.Login)
	users.POST("/signup", h.Signup)
	users.POST("/refresh", h.Refresh)
}
