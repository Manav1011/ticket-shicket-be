package middleware

import (
	"github.com/gin-gonic/gin"
	"github.com/manav1011/ticket-shicket-be/pkg/token"
	"github.com/manav1011/ticket-shicket-be/pkg/utils"
)

func GuestAuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Implementation for guest auth middleware
		// get the authorization header from the request
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			utils.Error(c, "Authorization header is missing", 401)
			c.Abort()
			return
		}

		const prefix = "Bearer "
		if len(authHeader) < len(prefix) || authHeader[:len(prefix)] != prefix {
			utils.Error(c, "Invalid authorization format", 401)
			c.Abort()
			return
		}
		tokenString := authHeader[len(prefix):]
		// validate the token
		claims, err := token.ParseToken(tokenString)
		if err != nil {
			utils.Error(c, "Invalid or expired token", 401)
			c.Abort()
			return
		}
		// check if guest_id is present in claims
		if _, ok := claims["guest_id"]; !ok {
			utils.Error(c, "Invalid token claims", 401)
			c.Abort()
			return
		}
		c.Set("guest_id", claims["guest_id"])
		c.Next()
	}
}

func UserAuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Implementation for user auth middleware
		// get the authorization header from the request
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			utils.Error(c, "Authorization header is missing", 401)
			c.Abort()
			return
		}

		const prefix = "Bearer "
		if len(authHeader) < len(prefix) || authHeader[:len(prefix)] != prefix {
			utils.Error(c, "Invalid authorization format", 401)
			c.Abort()
			return
		}
		tokenString := authHeader[len(prefix):]
		// validate the token
		claims, err := token.ParseToken(tokenString)
		if err != nil {
			utils.Error(c, "Invalid or expired token", 401)
			c.Abort()
			return
		}
		// check if user_id is present in claims
		if _, ok := claims["user_id"]; !ok {
			utils.Error(c, "Invalid token claims", 401)
			c.Abort()
			return
		}
		c.Set("user_id", claims["user_id"])
		c.Next()
	}
}
