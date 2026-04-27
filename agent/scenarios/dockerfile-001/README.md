# Scenario: dockerfile-001

**Category:** DOCKERFILE_ERROR
**Description:** Typo in base image tag
**Mutation:** `eclipse-temurin:21-jdk-alpine` → `eclipse-temurin:21-jdk-alpne`
**File affected:** Dockerfile, line 1
**Expected fix:** Correct the tag back to `21-jdk-alpine`
