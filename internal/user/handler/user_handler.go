package handler

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/manav1011/ticket-shicket-be/internal/user/model"
	"github.com/manav1011/ticket-shicket-be/internal/user/service"
	"github.com/manav1011/ticket-shicket-be/pkg/utils"
)

type UserHandler struct {
	svc *service.UserService
}

func NewUserHandler(svc *service.UserService) *UserHandler {
	return &UserHandler{svc: svc}
}

// Login authenticates a user and returns access and refresh tokens.
// @Summary      User login
// @Description  Validates email and password; returns JWT access and refresh tokens.
// @Tags         user
// @Accept       json
// @Produce      json
// @Param        body  body      model.LoginRequest  true  "Email and password"
// @Success      200   {object}  model.LoginSuccessEnvelope
// @Failure      400   {object}  utils.APIResponse
// @Failure      401   {object}  utils.APIResponse
// @Failure      500   {object}  utils.APIResponse
// @Router       /users/login [post]
func (h *UserHandler) Login(c *gin.Context) {
	var req model.LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Error(c, "invalid request body", http.StatusBadRequest)
		return
	}

	data, err := h.svc.Login(c.Request.Context(), req.Email, req.Password)
	if err != nil {
		if errors.Is(err, service.ErrInvalidCredentials) {
			utils.Error(c, "invalid credentials", http.StatusUnauthorized)
			return
		}
		utils.Error(c, "internal server error", http.StatusInternalServerError)
		return
	}

	utils.Success(c, data)
}

// Signup creates a new user.
// @Summary      User signup
// @Description  Creates a new user.
// @Tags         user
// @Accept       json
// @Produce      json
// @Param        body  body      model.SignupRequest  true  "Name, email and password"
// @Success      200   {object}  model.LoginSuccessEnvelope
// @Failure      400   {object}  utils.APIResponse
// @Failure      409   {object}  utils.APIResponse
// @Failure      500   {object}  utils.APIResponse

// @Router       /users/signup [post]
func (h *UserHandler) Signup(c *gin.Context) {
	var req model.SignupRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Error(c, "invalid request body", http.StatusBadRequest)
		return
	}
	data, err := h.svc.Signup(c.Request.Context(), req.Name, req.Email, req.Password)
	if err != nil {
		if errors.Is(err, service.ErrUserAlreadyExists) {
			utils.Error(c, "email already registered", http.StatusConflict)
			return
		}
		utils.Error(c, "internal server error", http.StatusInternalServerError)
		return
	}

	utils.Success(c, data)
}

// Refresh validates a refresh token and issues new access and refresh tokens.
// @Summary      Refresh tokens
// @Description  Validates a refresh token and issues new access and refresh tokens.
// @Tags         user
// @Accept       json
// @Produce      json
// @Param        body  body      model.RefreshRequest  true  "Refresh token"
// @Success      200   {object}  model.RefreshSuccessEnvelope
// @Failure      400   {object}  utils.APIResponse
// @Failure      401   {object}  utils.APIResponse
// @Failure      500   {object}  utils.APIResponse
// @Router       /users/refresh [post]
func (h *UserHandler) Refresh(c *gin.Context) {
	var req model.RefreshRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Error(c, "invalid request body", http.StatusBadRequest)
		return
	}
	data, err := h.svc.Refresh(c.Request.Context(), req.RefreshToken)
	if err != nil {
		if errors.Is(err, service.ErrInvalidCredentials) {
			utils.Error(c, "invalid refresh token", http.StatusUnauthorized)
			return
		}
		utils.Error(c, "internal server error", http.StatusInternalServerError)
		return
	}

	utils.Success(c, data)
}
