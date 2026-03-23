package main

import (
	"log"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5/stdlib"
	"github.com/manav1011/ticket-shicket-be/internal/config"
	"github.com/manav1011/ticket-shicket-be/internal/db"
	sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
	"github.com/manav1011/ticket-shicket-be/internal/guest"
	guestHandler "github.com/manav1011/ticket-shicket-be/internal/guest/handler"
	guestRepository "github.com/manav1011/ticket-shicket-be/internal/guest/repository"
	guestService "github.com/manav1011/ticket-shicket-be/internal/guest/service"
	"github.com/manav1011/ticket-shicket-be/internal/user"
	"github.com/manav1011/ticket-shicket-be/internal/user/handler"
	"github.com/manav1011/ticket-shicket-be/internal/user/repository"
	"github.com/manav1011/ticket-shicket-be/internal/user/service"

	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"

	_ "github.com/manav1011/ticket-shicket-be/docs" // swagger docs (swag init)

	response "github.com/manav1011/ticket-shicket-be/pkg/utils"

	middleware "github.com/manav1011/ticket-shicket-be/internal/middleware"
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

	// User app
	userRepo := repository.NewUserRepository(queries)
	userSvc := service.NewUserService(userRepo, cfg)
	userHandler := handler.NewUserHandler(userSvc)

	// Guest app
	repo := guestRepository.NewGuestRepository(queries)
	svc := guestService.NewGuestService(repo, cfg)
	guestH := guestHandler.NewGuestHandler(svc)

	r := gin.Default()

	// add cors middleware
	r.Use(middleware.CorsMiddleware())

	// Swagger UI: open /swagger/index.html (Gin cannot mix /swagger + /swagger/*any on the same prefix).
	r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	v1 := r.Group("/v1")
	v1.GET("/health", health)

	user.RegisterRoutes(v1, userHandler)
	guest.RegisterRoutes(v1, guestH)

	log.Println("server running on port", cfg.ServerPort)
	if err := r.Run(":" + cfg.ServerPort); err != nil {
		log.Fatal("Error starting server:", err)
	}
}
