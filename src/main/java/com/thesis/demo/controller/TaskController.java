package com.thesis.demo.controller;

import com.thesis.demo.model.Task;
import com.thesis.demo.model.TaskStatus;
import com.thesis.demo.repository.TaskRepository;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
@RequestMapping("/api/tasks")
public class TaskController {

    private final TaskRepository repo;

    public TaskController(TaskRepository repo) {
        this.repo = repo;
    }

    // GET /api/tasks          — toate task-urile
    // GET /api/tasks?status=  — filtrate după status
    @GetMapping
    public List<Task> getAll(@RequestParam(required = false) TaskStatus status) {
        if (status != null) return repo.findByStatus(status);
        return repo.findAll();
    }

    // GET /api/tasks/{id}
    @GetMapping("/{id}")
    public Task getById(@PathVariable Long id) {
        return repo.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Task not found"));
    }

    // POST /api/tasks
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Task create(@Valid @RequestBody Task task) {
        return repo.save(task);
    }

    // PATCH /api/tasks/{id}/status
    @PatchMapping("/{id}/status")
    public Task updateStatus(@PathVariable Long id, @RequestParam TaskStatus status) {
        Task task = repo.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Task not found"));
        task.setStatus(status);
        return repo.save(task);
    }
}
