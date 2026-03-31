package main

import (
	// Standard library
	"log"

	// Third-party
	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5/stdlib"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"

	// Project/internal
	"github.com/manav1011/ticket-shicket-be/internal/config"
	"github.com/manav1011/ticket-shicket-be/internal/db"
	sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"

	// Guest module
	"github.com/manav1011/ticket-shicket-be/internal/guest"
	guestHandler "github.com/manav1011/ticket-shicket-be/internal/guest/handler"
	guestRepository "github.com/manav1011/ticket-shicket-be/internal/guest/repository"
	guestService "github.com/manav1011/ticket-shicket-be/internal/guest/service"

	// Scanning module
	"github.com/manav1011/ticket-shicket-be/internal/scanning"
	scanningHandler "github.com/manav1011/ticket-shicket-be/internal/scanning/handler"
	scanningRepository "github.com/manav1011/ticket-shicket-be/internal/scanning/repository"
	scanningService "github.com/manav1011/ticket-shicket-be/internal/scanning/service"

	// User module
	"github.com/manav1011/ticket-shicket-be/internal/user"
	userHandler "github.com/manav1011/ticket-shicket-be/internal/user/handler"
	userRepository "github.com/manav1011/ticket-shicket-be/internal/user/repository"
	userService "github.com/manav1011/ticket-shicket-be/internal/user/service"

	// Utilities and middleware
	middleware "github.com/manav1011/ticket-shicket-be/internal/middleware"
	response "github.com/manav1011/ticket-shicket-be/pkg/utils"

	_ "github.com/manav1011/ticket-shicket-be/docs" // swagger docs (swag init)
)

// @title           Ticket Shicket API
// @version         1.0
// @description     HTTP API for Ticket Shicket backend.
// @host            localhost:8080
// @BasePath        /v1
// @schemes         http

// health returns service availability.
// @Summary      Health check
// @Description  Returns ok if the service is running.
// @Tags         health
// @Produce      json
// @Success      200  {object}  map[string]string
// @Router       /health [get]
func health(c *gin.Context) {
	response.Success(c, nil)
}

func main() {
	cfg := config.LoadConfig()

	pool := db.NewDB(cfg.DBSource)

	sqlDB := stdlib.OpenDBFromPool(pool)
	defer sqlDB.Close()

	queries := sqldb.New(sqlDB)

	// Initialize Redis client
	redisClient := db.NewRedisClient(cfg.RedisAddr, cfg.RedisPassword, cfg.RedisDefaultDB)
	defer redisClient.Close()

	// User app
	userRepo := userRepository.NewUserRepository(queries)
	userSvc := userService.NewUserService(userRepo, cfg)
	userHandler := userHandler.NewUserHandler(userSvc)

	// Guest app
	repo := guestRepository.NewGuestRepository(queries)
	svc := guestService.NewGuestService(repo, cfg)
	guestH := guestHandler.NewGuestHandler(svc)

	// Scanning app
	scanningRepo := scanningRepository.NewScanningRepository(queries, redisClient)
	scanningSvc := scanningService.NewScanningService(scanningRepo)
	scanningHandler := scanningHandler.NewScanningHandler(scanningSvc)

	r := gin.Default()

	// add cors middleware
	r.Use(middleware.CorsMiddleware())

	// Swagger UI: open /swagger/index.html (Gin cannot mix /swagger + /swagger/*any on the same prefix).
	r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	v1 := r.Group("/v1")
	v1.GET("/health", health)

	user.RegisterRoutes(v1, userHandler)
	guest.RegisterRoutes(v1, guestH)
	scanning.RegisterRoutes(v1, scanningHandler)

	log.Println("server running on port", cfg.ServerPort)
	if err := r.Run(":" + cfg.ServerPort); err != nil {
		log.Fatal("Error starting server:", err)
	}
}
