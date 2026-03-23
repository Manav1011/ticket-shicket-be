package handler

import (
"errors"
"net/http"

"github.com/gin-gonic/gin"
"github.com/manav1011/ticket-shicket-be/internal/guest/model"
"github.com/manav1011/ticket-shicket-be/internal/guest/service"
"github.com/manav1011/ticket-shicket-be/pkg/utils"
)

type GuestHandler struct {
	svc *service.GuestService
}

func NewGuestHandler(svc *service.GuestService) *GuestHandler {
	return &GuestHandler{svc: svc}
}

// Register creates a new guest and returns access and refresh tokens.
// @Summary      Guest registration
// @Description  Registers a guest user and returns JWT access and refresh tokens.
// @Tags         guest
// @Accept       json
// @Produce      json
// @Param        body  body      model.GuestRegisterRequest  true  "User agent and IP address"
// @Success      200   {object}  model.GuestRegisterSuccessEnvelope
// @Failure      400   {object}  utils.APIResponse
// @Failure      500   {object}  utils.APIResponse
// @Router       /guests/register [post]
func (h *GuestHandler) Register(c *gin.Context) {
	var req model.GuestRegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Error(c, "invalid request body", http.StatusBadRequest)
		return
	}

	data, err := h.svc.Register(c.Request.Context(), req.UserAgent, req.IpAddress)
	if err != nil {
		if errors.Is(err, service.ErrGuestRegistrationFailed) {
			utils.Error(c, "guest registration failed", http.StatusInternalServerError)
			return
		}
		utils.Error(c, "internal server error", http.StatusInternalServerError)
		return
	}

	utils.Success(c, data)
}
