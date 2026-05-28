# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jdk-alpne AS builder

WORKDIR /app

# Copiază doar fișierele de dependențe mai întâi (cache layer)
ADD .mvn/ .mvn/
ADD mvnw pom.xml ./
RUN ./mvnw dependency:go-offline -q

# Copiază codul sursă și construiește
ADD src/ src/
RUN ./mvnw package -DskipTests -q

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jre-alpine AS runtime

# Non-root user pentru securitate
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

WORKDIR /app

ADD --from=builder /app/target/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
