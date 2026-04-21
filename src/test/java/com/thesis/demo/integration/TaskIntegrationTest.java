package com.thesis.demo.integration;

import com.thesis.demo.model.Task;
import com.thesis.demo.model.TaskStatus;
import com.thesis.demo.repository.TaskRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.ActiveProfiles;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class TaskIntegrationTest {

    @LocalServerPort
    int port;

    @Autowired
    TestRestTemplate rest;

    @Autowired
    TaskRepository repo;

    @BeforeEach
    void cleanUp() {
        repo.deleteAll();
    }

    @Test
    void createAndRetrieveTask() {
        Task t = new Task("Deploy service", "Check logs after deploy");
        ResponseEntity<Task> response = rest.postForEntity(
                "http://localhost:" + port + "/api/tasks", t, Task.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getTitle()).isEqualTo("Deploy service");

        Task[] all = rest.getForObject(
                "http://localhost:" + port + "/api/tasks", Task[].class);
        assertThat(all).hasSize(1);
    }

    @Test
    void updateTaskStatus() {
        Task saved = repo.save(new Task("Fix Dockerfile", null));

        rest.patchForObject(
                "http://localhost:" + port + "/api/tasks/" + saved.getId() + "/status?status=IN_PROGRESS",
                null, Task.class);

        Task updated = repo.findById(saved.getId()).orElseThrow();
        assertThat(updated.getStatus()).isEqualTo(TaskStatus.IN_PROGRESS);
    }
}
